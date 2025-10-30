#!/usr/bin/env python3
"""
AAv2.5 Fixer Agent - Automatic Error Recovery

Takes diagnosis from reviewer and generates/executes fix commands.
This closes the loop: Executor → Verifier → Reviewer → Fixer → Retry

Uses REAL LLM to generate concrete fix commands from diagnosis.
"""
from __future__ import annotations
import sys, uuid, json
from pathlib import Path
from typing import List, Optional

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.aav2_artifacts import (
    DiagnosisDocument, ExecutionTranscript, FailureDiagnosis,
    timestamp_now, load_artifact, save_artifact
)
from scripts.aav2_llm_integration import call_claude_api, call_openai_api, LLMResponse


def generate_fix_commands(diagnosis: DiagnosisDocument, original_task: str, use_claude: bool = True) -> List[str]:
    """
    Use LLM to generate concrete fix commands from diagnosis.

    This is the breakthrough - LLM reasons about failures and generates fixes!
    """

    system_prompt = """You are an expert systems engineer fixing command failures.

Your task: Given a diagnosis of failures, generate concrete bash commands to fix them.

Output ONLY the commands, one per line, no explanations.
Commands must be:
- Concrete (not placeholders)
- Safe (no destructive operations)
- Testable (can verify they worked)
- Ordered (dependencies clear)

Example input:
- Error: "directory /workspace does not exist"
- Suggested fix: "Create directory: mkdir -p /workspace"

Example output:
mkdir -p /workspace
"""

    # Build diagnosis summary
    failures_summary = []
    for i, failure in enumerate(diagnosis.failures_analyzed, 1):
        failures_summary.append(f"""
Failure {i}:
  Command: {failure.command}
  Error Type: {failure.error_type}
  Root Cause: {failure.root_cause}
  Suggested Fix: {failure.suggested_fix}
  Confidence: {failure.confidence:.0%}
""")

    user_prompt = f"""Original task context:
{original_task[:500]}

Diagnosed failures:
{"".join(failures_summary)}

Generate bash commands to fix these failures (one per line, no explanations):"""

    # Call LLM
    if use_claude:
        response = call_claude_api(user_prompt, system_prompt, max_tokens=2048)
    else:
        response = call_openai_api(user_prompt, system_prompt, max_tokens=2048)

    if not response.success:
        # Fallback: extract suggested fixes from diagnosis
        print(f"[WARN] LLM fix generation failed: {response.error}")
        fix_commands = []
        for failure in diagnosis.failures_analyzed:
            # Try to extract command from suggested_fix
            suggested = failure.suggested_fix
            # Common patterns: "Run: cmd", "Use: cmd", "Execute: cmd"
            if ":" in suggested:
                cmd = suggested.split(":", 1)[1].strip()
                fix_commands.append(cmd)
            elif suggested.startswith("mkdir") or suggested.startswith("touch"):
                fix_commands.append(suggested)

        return fix_commands if fix_commands else ["echo '[ERROR] Could not generate fix commands'"]

    # Parse commands from LLM response
    commands = []
    for line in response.content.split('\n'):
        line = line.strip()
        # Skip empty lines, comments, explanations
        if not line or line.startswith('#') or line.startswith('//'):
            continue
        # Skip markdown code fences
        if line.startswith('```'):
            continue
        # Skip lines that look like explanations (contain ":")
        if ':' in line and not line.startswith('export'):
            # Unless it's a valid command like "echo 'foo: bar'"
            if not any(line.startswith(cmd) for cmd in ['echo', 'cat', 'docker', 'curl', 'wget']):
                continue

        commands.append(line)

    return commands if commands else ["echo '[WARN] No fix commands generated'"]


def apply_fix(
    diagnosis_path: str,
    original_task_path: str,
    agent_id: str = None,
    use_claude: bool = True
) -> ExecutionTranscript:
    """
    Apply fixes from diagnosis by executing generated commands.

    Returns new ExecutionTranscript with fix results.
    """
    if agent_id is None:
        agent_id = f"fixer_{uuid.uuid4().hex[:8]}"

    print(f"\n[Fixer Agent (Claude): {agent_id}]")
    print(f"Diagnosis: {diagnosis_path}")
    print(f"Original task: {original_task_path}")
    print(f"Using: Real LLM fix generation")
    print("")

    # Load artifacts
    try:
        diagnosis = load_artifact(diagnosis_path)
        with open(original_task_path, 'r') as f:
            original_task = f.read()
    except Exception as e:
        print(f"[ERROR] Failed to load artifacts: {e}")
        return None

    # Check if there are fixable failures
    if diagnosis['fixable_failures'] == 0:
        print("[INFO] No fixable failures - nothing to fix")
        return None

    print(f"[Generating Fix Commands with LLM]")
    print(f"Fixable failures: {diagnosis['fixable_failures']}")
    print("")

    # Generate fix commands
    fix_commands = generate_fix_commands(diagnosis, original_task, use_claude=use_claude)

    print(f"[Generated {len(fix_commands)} fix commands]")
    for i, cmd in enumerate(fix_commands, 1):
        print(f"{i}. {cmd}")
    print("")

    # Execute fix commands
    print("[Executing Fixes]")

    from scripts.aav2_executor import run_command_in_sandbox

    commands_executed = []
    successful = 0
    failed = 0

    for i, cmd in enumerate(fix_commands, 1):
        print(f"\n--- Fix Command {i}/{len(fix_commands)} ---")
        print(f"$ {cmd}")

        result = run_command_in_sandbox(cmd, timeout=300)

        success = result.get('ok', False)
        if success:
            successful += 1
            print(f"[SUCCESS] Exit code: {result.get('exit_code', 0)}")
        else:
            failed += 1
            print(f"[FAILED] Exit code: {result.get('exit_code', 1)}")
            if result.get('stderr'):
                print(f"Error: {result['stderr'][:200]}")

        commands_executed.append({
            "command": cmd,
            "success": success,
            "exit_code": result.get('exit_code', 0),
            "stdout": result.get('stdout', ''),
            "stderr": result.get('stderr', ''),
            "timestamp": timestamp_now()
        })

    # Build transcript
    transcript = ExecutionTranscript(
        task_file=f"FIX:{original_task_path}",
        agent_id=agent_id,
        commands_executed=commands_executed,
        total_commands=len(commands_executed),
        successful_commands=successful,
        failed_commands=failed,
        timestamp=timestamp_now()
    )

    print(f"\n[Fixer Complete]")
    print(f"Total commands: {len(commands_executed)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    return transcript


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="AAv2.5 Fixer Agent - Apply fixes from diagnosis")
    ap.add_argument("diagnosis", help="Path to diagnosis document JSON")
    ap.add_argument("task", help="Path to original task file")
    ap.add_argument("--agent-id", help="Agent ID (auto-generated if not provided)")
    ap.add_argument("--output", default="reports/aav2_fix_transcript.json",
                    help="Output path for fix transcript")
    ap.add_argument("--use-codex", action="store_true",
                    help="Use OpenAI Codex instead of Claude")
    args = ap.parse_args()

    if not Path(args.diagnosis).exists():
        print(f"ERROR: Diagnosis not found: {args.diagnosis}")
        sys.exit(1)

    if not Path(args.task).exists():
        print(f"ERROR: Task file not found: {args.task}")
        sys.exit(1)

    # Apply fixes
    transcript = apply_fix(
        diagnosis_path=args.diagnosis,
        original_task_path=args.task,
        agent_id=args.agent_id,
        use_claude=not args.use_codex
    )

    if transcript is None:
        sys.exit(1)

    # Save artifact
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_artifact(transcript, str(output_path))

    print(f"\n[Artifact Saved]")
    print(f"Path: {output_path}")
    print(f"Type: execution_transcript (fix)")

    # Exit with success/failure based on results
    if transcript.failed_commands > 0:
        print(f"\n[WARNING] {transcript.failed_commands} fix commands failed")
        sys.exit(1)
    else:
        print(f"\n[SUCCESS] All {transcript.successful_commands} fix commands succeeded")
        sys.exit(0)
