#!/usr/bin/env python3
"""
AAv2 Executor Agent - Claude Executes Commands

Implements:
- Deterministic command execution (no interpretation)
- Reflection pattern (self-critique before execution)
- Structured transcript output (MetaGPT pattern)
"""
from __future__ import annotations
import sys, subprocess, time, uuid
from pathlib import Path
from typing import List, Optional

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.execute_blocks import parse_task
from scripts.aav2_artifacts import (
    CommandExecution, ExecutionTranscript, ReflectionResult,
    timestamp_now, save_artifact
)

def run_command_in_sandbox(cmd: str, timeout: int = 1800) -> dict:
    """
    Execute command inside agent-sandbox container.

    Returns: {ok: bool, stdout: str, stderr: str, returncode: int, duration_sec: float}
    """
    start_time = time.time()

    # Check if agent-sandbox is running
    check = subprocess.run(
        ["docker", "ps", "--filter", "name=agent-sandbox", "--format", "{{.Names}}"],
        capture_output=True, text=True, timeout=10
    )

    if "agent-sandbox" not in check.stdout:
        return {
            "ok": False,
            "stdout": "",
            "stderr": "agent-sandbox container not running. Run: scripts/start_agent_sandbox.sh",
            "returncode": 1,
            "duration_sec": time.time() - start_time
        }

    # Execute inside sandbox
    result = subprocess.run(
        ["docker", "exec", "-w", "/workspace", "agent-sandbox", "bash", "-c", cmd],
        capture_output=True,
        text=True,
        timeout=timeout
    )

    return {
        "ok": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
        "duration_sec": time.time() - start_time
    }


def reflect_on_command(cmd: str) -> ReflectionResult:
    """
    Reflection pattern: Self-critique before execution.

    Claude analyzes potential issues and suggests alternatives if risky.
    This is a simplified version - in full implementation, this would
    call Claude API for actual reasoning.
    """
    # Simplified heuristics (full version would use Claude API)
    potential_issues = []
    risk_level = "low"
    alternative = None
    proceed = True
    reasoning = "Command appears safe to execute"

    # Check for common issues
    if "rm -rf /" in cmd or "rm -rf /*" in cmd:
        potential_issues.append("Destructive command - deletes entire filesystem")
        risk_level = "high"
        proceed = False
        reasoning = "CRITICAL: This would delete the entire filesystem"

    elif "dd if=/dev/zero" in cmd:
        potential_issues.append("Disk wipe command detected")
        risk_level = "high"
        proceed = False
        reasoning = "This would overwrite disk data"

    elif cmd.startswith("mkdir") and "." in cmd.split()[-1]:
        # Looks like trying to mkdir a file (has extension)
        potential_issues.append("mkdir target looks like a file (has extension)")
        risk_level = "medium"
        dirname = cmd.split()[-1].rsplit("/", 1)[0] if "/" in cmd else "."
        filename = cmd.split()[-1]
        alternative = f"mkdir -p {dirname} && touch {filename}"
        proceed = False
        reasoning = "mkdir should create directory, but target looks like a file"

    elif "> /dev/sd" in cmd:
        potential_issues.append("Writing directly to block device")
        risk_level = "high"
        proceed = False
        reasoning = "Direct block device writes are dangerous"

    # Docker build without context
    elif "docker build" in cmd and " ." not in cmd and " -f" in cmd:
        # Has Dockerfile but maybe missing build context
        potential_issues.append("docker build might be missing build context")
        risk_level = "low"
        reasoning = "Command looks okay, proceeding"

    return ReflectionResult(
        command=cmd,
        potential_issues=potential_issues,
        risk_level=risk_level,
        alternative_command=alternative,
        proceed=proceed,
        reasoning=reasoning
    )


def execute_task(task_file: str, agent_id: Optional[str] = None, enable_reflection: bool = True) -> ExecutionTranscript:
    """
    Execute task with reflection pattern enabled.

    Returns: ExecutionTranscript artifact
    """
    if agent_id is None:
        agent_id = f"executor_{uuid.uuid4().hex[:8]}"

    print(f"\n[Executor Agent: {agent_id}]")
    print(f"Task: {task_file}")
    print(f"Reflection: {'enabled' if enable_reflection else 'disabled'}")
    print("")

    timestamp_start = timestamp_now()

    # Parse task
    try:
        parsed = parse_task(task_file)
    except Exception as e:
        print(f"[ERROR] Failed to parse task: {e}")
        return None

    commands = parsed["commands"]
    print(f"Commands to execute: {len(commands)}\n")

    # Execute with reflection
    executions = []
    successful = 0
    failed = 0
    total_duration = 0.0

    for i, cmd in enumerate(commands):
        print(f"--- Command {i+1}/{len(commands)} ---")
        print(f"$ {cmd}")

        # Reflection step
        if enable_reflection:
            reflection = reflect_on_command(cmd)
            if not reflection.proceed:
                print(f"[REFLECTION] {reflection.reasoning}")
                print(f"[REFLECTION] Risk level: {reflection.risk_level}")
                if reflection.alternative_command:
                    print(f"[REFLECTION] Suggested alternative: {reflection.alternative_command}")
                    cmd = reflection.alternative_command
                    print(f"[REFLECTION] Using alternative")
                else:
                    print(f"[REFLECTION] BLOCKING execution - command too risky")
                    exec_record = CommandExecution(
                        command=cmd,
                        exit_code=1,
                        stdout="",
                        stderr=f"Blocked by reflection: {reflection.reasoning}",
                        timestamp=timestamp_now(),
                        duration_sec=0.0,
                        success=False
                    )
                    executions.append(exec_record)
                    failed += 1
                    continue

        # Execute
        try:
            result = run_command_in_sandbox(cmd, timeout=1800)
        except subprocess.TimeoutExpired:
            print("[TIMEOUT] Command exceeded 30 minute limit")
            exec_record = CommandExecution(
                command=cmd,
                exit_code=124,
                stdout="",
                stderr="Command timeout after 1800 seconds",
                timestamp=timestamp_now(),
                duration_sec=1800.0,
                success=False
            )
            executions.append(exec_record)
            failed += 1
            total_duration += 1800.0
            break
        except Exception as e:
            print(f"[ERROR] Execution failed: {e}")
            exec_record = CommandExecution(
                command=cmd,
                exit_code=1,
                stdout="",
                stderr=str(e),
                timestamp=timestamp_now(),
                duration_sec=0.0,
                success=False
            )
            executions.append(exec_record)
            failed += 1
            break

        # Record result
        exec_record = CommandExecution(
            command=cmd,
            exit_code=result["returncode"],
            stdout=result["stdout"],
            stderr=result["stderr"],
            timestamp=timestamp_now(),
            duration_sec=result["duration_sec"],
            success=result["ok"]
        )
        executions.append(exec_record)
        total_duration += result["duration_sec"]

        # Show output preview
        output = (result.get("stdout", "") + result.get("stderr", "")).strip()
        if output:
            preview = output[-500:] if len(output) > 500 else output
            print(preview)

        status = "[OK]" if result["ok"] else "[FAIL]"
        print(f"{status} Exit code: {result['returncode']} ({result['duration_sec']:.2f}s)\n")

        if result["ok"]:
            successful += 1
        else:
            failed += 1
            print("[INFO] Command failed. Stopping execution.")
            break

    timestamp_end = timestamp_now()

    # Build transcript artifact
    transcript = ExecutionTranscript(
        task_file=task_file,
        agent_id=agent_id,
        commands_executed=executions,
        total_commands=len(commands),
        successful_commands=successful,
        failed_commands=failed,
        total_duration_sec=total_duration,
        timestamp_start=timestamp_start,
        timestamp_end=timestamp_end
    )

    print(f"\n[Executor Complete]")
    print(f"Successful: {successful}/{len(commands)}")
    print(f"Failed: {failed}/{len(commands)}")
    print(f"Duration: {total_duration:.2f}s")

    return transcript


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="AAv2 Executor Agent - Claude executes commands")
    ap.add_argument("task", help="Path to task file with EXECUTE: block")
    ap.add_argument("--agent-id", help="Agent ID (auto-generated if not provided)")
    ap.add_argument("--no-reflection", action="store_true", help="Disable reflection pattern")
    ap.add_argument("--output", default="reports/aav2_execution_transcript.json", help="Output path for transcript")
    args = ap.parse_args()

    if not Path(args.task).exists():
        print(f"ERROR: Task file not found: {args.task}")
        sys.exit(1)

    # Execute task
    transcript = execute_task(
        task_file=args.task,
        agent_id=args.agent_id,
        enable_reflection=not args.no_reflection
    )

    if transcript is None:
        sys.exit(1)

    # Save artifact
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_artifact(transcript, str(output_path))

    print(f"\n[Artifact Saved]")
    print(f"Path: {output_path}")
    print(f"Type: execution_transcript")

    sys.exit(0 if transcript.failed_commands == 0 else 1)
