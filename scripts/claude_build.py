#!/usr/bin/env python3
"""
Claude Build - Deterministic Task Execution

Claude EXECUTES explicit commands.
Codex GUIDES on failures (optional).

Architecture:
- Parse EXECUTE: blocks (no interpretation)
- Run commands sequentially
- Verify SUCCESS_CRITERIA before claiming done
- Call Codex guide only when commands fail
"""
from __future__ import annotations
import sys, json, time, subprocess, re
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.execute_blocks import parse_task


def run_passthrough(cmd: str, timeout: int = 1800) -> dict:
    """
    Execute command inside agent-sandbox container.

    Returns: {ok: bool, stdout: str, stderr: str, returncode: int}
    """
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
            "returncode": 1
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
        "returncode": result.returncode
    }


def verify_criteria(criteria: list) -> tuple[bool, list]:
    """
    Verify SUCCESS_CRITERIA.

    Returns: (all_passed, [results])
    """
    results = []
    all_ok = True

    for c in criteria:
        if c["type"] == "file":
            # Check file exists (map /workspace to actual location if needed)
            path = c["path"]
            # For sandbox, check via docker exec
            res = run_passthrough(f"test -f {path} && echo OK || echo FAIL")
            ok = "OK" in res.get("stdout", "")
            results.append({
                "type": "file",
                "path": path,
                "ok": ok,
                "message": f"File {'exists' if ok else 'missing'}: {path}"
            })
            all_ok &= ok

        elif c["type"] == "command":
            # Run command, check exit code
            res = run_passthrough(c["cmd"])
            ok = res.get("ok", False)
            results.append({
                "type": "command",
                "cmd": c["cmd"],
                "ok": ok,
                "message": f"Command {'passed' if ok else 'failed'}: {c['cmd']}"
            })
            all_ok &= ok

        elif c["type"] == "grep":
            # Check if pattern appears in file
            pattern = c["pattern"]
            path = c["path"]
            # Read file via cat and grep
            res = run_passthrough(f"cat {path} 2>/dev/null | grep -q '{pattern}' && echo OK || echo FAIL")
            ok = "OK" in res.get("stdout", "")
            results.append({
                "type": "grep",
                "pattern": pattern,
                "path": path,
                "ok": ok,
                "message": f"Pattern {'found' if ok else 'not found'}: '{pattern}' in {path}"
            })
            all_ok &= ok

    return all_ok, results


def run_execblocks(task_file: str, budget: int = 20) -> dict:
    """
    Execute task using EXECUTE blocks (no LLM interpretation).

    Returns: {ok: bool, turns: int, criteria_passed: bool}
    """
    print("\n=== Claude Build: Deterministic Execution ===")
    print(f"Task: {task_file}")
    print(f"Budget: {budget} commands")
    print("")

    # Parse task file
    try:
        parsed = parse_task(task_file)
    except Exception as e:
        print(f"[ERROR] Failed to parse task: {e}")
        return {"ok": False, "turns": 0, "criteria_passed": False}

    cmds = parsed["commands"]
    criteria = parsed["criteria"]

    print(f"Commands to execute: {len(cmds)}")
    print(f"Success criteria: {len(criteria)}")
    print("")

    # Execute commands
    turns = 0
    failed = False

    for i, cmd in enumerate(cmds):
        if turns >= budget:
            print("[STOP] Budget exhausted before finishing commands.")
            break

        turns += 1
        print(f"\n--- Command {i+1}/{len(cmds)} ---")
        print(f"$ {cmd}")

        try:
            res = run_passthrough(cmd, timeout=1800)
        except subprocess.TimeoutExpired:
            print("[TIMEOUT] Command exceeded 30 minute limit")
            failed = True
            break
        except Exception as e:
            print(f"[ERROR] Execution failed: {e}")
            failed = True
            break

        # Show output
        output = (res.get("stdout", "") + res.get("stderr", "")).strip()
        if output:
            # Show last 500 chars to avoid flooding
            preview = output[-500:] if len(output) > 500 else output
            print(preview)

        ok_marker = "[OK]" if res.get("ok") else "[FAIL]"
        print(f"{ok_marker} Exit code: {res.get('returncode', 'unknown')}")

        if not res.get("ok"):
            print("\n[INFO] Command failed. Task incomplete.")
            failed = True
            break

    # Verify success criteria
    print("\n\n=== Success Criteria Verification ===")

    if failed:
        print("[SKIP] Commands failed, skipping criteria check")
        return {
            "ok": False,
            "turns": turns,
            "criteria_passed": False,
            "commands_completed": f"{i+1}/{len(cmds)}"
        }

    if not criteria:
        print("[INFO] No success criteria defined")
        return {
            "ok": True,
            "turns": turns,
            "criteria_passed": True,
            "commands_completed": f"{len(cmds)}/{len(cmds)}"
        }

    all_ok, results = verify_criteria(criteria)

    for r in results:
        status = "[OK]" if r["ok"] else "[FAIL]"
        print(f"{status} {r['message']}")

    # Final verdict
    print("\n\n=== Session Complete ===")
    print(f"Commands executed: {turns}/{len(cmds)}")
    print(f"Criteria passed: {sum(1 for r in results if r['ok'])}/{len(results)}")
    print(f"Task completed: {'Yes' if all_ok else 'No'}")

    return {
        "ok": all_ok,
        "turns": turns,
        "criteria_passed": all_ok,
        "commands_completed": f"{len(cmds)}/{len(cmds)}",
        "criteria_results": results
    }


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Claude Build: Deterministic task execution")
    ap.add_argument("task", help="Path to task file with EXECUTE: block")
    ap.add_argument("--budget", type=int, default=20, help="Max commands to execute")
    args = ap.parse_args()

    if not Path(args.task).exists():
        print(f"ERROR: Task file not found: {args.task}")
        sys.exit(1)

    result = run_execblocks(args.task, budget=args.budget)

    print("\n" + json.dumps(result, indent=2))

    sys.exit(0 if result["ok"] else 1)
