#!/usr/bin/env python3
"""
AAv2 Verifier Agent - Claude Verifies Success Criteria

Implements quality gates before marking task complete.
Reads execution transcript, checks all SUCCESS_CRITERIA.
"""
from __future__ import annotations
import sys, subprocess, uuid
from pathlib import Path
from typing import List

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.execute_blocks import parse_task
from scripts.aav2_artifacts import (
    ExecutionTranscript, VerificationReport, CriteriaCheck,
    timestamp_now, save_artifact, load_artifact
)


def run_check_in_sandbox(cmd: str) -> dict:
    """Execute verification command in sandbox"""
    try:
        result = subprocess.run(
            ["docker", "exec", "-w", "/workspace", "agent-sandbox", "bash", "-c", cmd],
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e)}


def verify_criteria(task_file: str, transcript_path: str, agent_id: str = None) -> VerificationReport:
    """
    Verify all SUCCESS_CRITERIA from task.

    Returns: VerificationReport artifact
    """
    if agent_id is None:
        agent_id = f"verifier_{uuid.uuid4().hex[:8]}"

    print(f"\n[Verifier Agent: {agent_id}]")
    print(f"Task: {task_file}")
    print(f"Transcript: {transcript_path}")
    print("")

    # Load execution transcript
    try:
        transcript_data = load_artifact(transcript_path)
        transcript_id = f"{transcript_data['agent_id']}_{transcript_data['timestamp_end']}"
    except Exception as e:
        print(f"[ERROR] Failed to load transcript: {e}")
        return None

    # Parse task for criteria
    try:
        parsed = parse_task(task_file)
    except Exception as e:
        print(f"[ERROR] Failed to parse task: {e}")
        return None

    criteria = parsed["criteria"]
    print(f"Criteria to verify: {len(criteria)}\n")

    # Check each criterion
    checks = []
    passed_count = 0
    failed_count = 0

    for i, c in enumerate(criteria):
        print(f"--- Criterion {i+1}/{len(criteria)} ---")

        if c["type"] == "file":
            # Check file exists
            path = c["path"]
            print(f"File exists: {path}")
            res = run_check_in_sandbox(f"test -f {path} && echo OK || echo FAIL")
            ok = "OK" in res.get("stdout", "")

            check = CriteriaCheck(
                criteria_type="file",
                description=f"File exists: {path}",
                passed=ok,
                details=f"File {'exists' if ok else 'missing'}: {path}"
            )
            checks.append(check)

        elif c["type"] == "command":
            # Run command, check exit code
            cmd = c["cmd"]
            print(f"Command: {cmd}")
            res = run_check_in_sandbox(cmd)
            ok = res.get("ok", False)

            check = CriteriaCheck(
                criteria_type="command",
                description=f"Command: {cmd}",
                passed=ok,
                details=f"Command {'passed' if ok else 'failed'}: {cmd}"
            )
            checks.append(check)

        elif c["type"] == "grep":
            # Check if pattern appears in file
            pattern = c["pattern"]
            path = c["path"]
            print(f"Grep: '{pattern}' in {path}")
            res = run_check_in_sandbox(f"cat {path} 2>/dev/null | grep -q '{pattern}' && echo OK || echo FAIL")
            ok = "OK" in res.get("stdout", "")

            check = CriteriaCheck(
                criteria_type="grep",
                description=f"Pattern '{pattern}' in {path}",
                passed=ok,
                details=f"Pattern {'found' if ok else 'not found'}: '{pattern}' in {path}"
            )
            checks.append(check)

        else:
            print(f"[WARN] Unknown criteria type: {c['type']}")
            continue

        status = "[PASS]" if check.passed else "[FAIL]"
        print(f"{status} {check.details}\n")

        if check.passed:
            passed_count += 1
        else:
            failed_count += 1

    # Build report artifact
    overall_pass = failed_count == 0 and len(checks) > 0

    report = VerificationReport(
        transcript_id=transcript_id,
        agent_id=agent_id,
        criteria_checked=checks,
        total_criteria=len(criteria),
        passed_criteria=passed_count,
        failed_criteria=failed_count,
        overall_pass=overall_pass,
        timestamp=timestamp_now()
    )

    print(f"[Verifier Complete]")
    print(f"Passed: {passed_count}/{len(criteria)}")
    print(f"Failed: {failed_count}/{len(criteria)}")
    print(f"Overall: {'PASS' if overall_pass else 'FAIL'}")

    return report


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="AAv2 Verifier Agent - Claude checks success criteria")
    ap.add_argument("task", help="Path to task file with SUCCESS_CRITERIA")
    ap.add_argument("transcript", help="Path to execution transcript JSON")
    ap.add_argument("--agent-id", help="Agent ID (auto-generated if not provided)")
    ap.add_argument("--output", default="reports/aav2_verification_report.json", help="Output path for report")
    args = ap.parse_args()

    if not Path(args.task).exists():
        print(f"ERROR: Task file not found: {args.task}")
        sys.exit(1)

    if not Path(args.transcript).exists():
        print(f"ERROR: Transcript not found: {args.transcript}")
        sys.exit(1)

    # Verify criteria
    report = verify_criteria(
        task_file=args.task,
        transcript_path=args.transcript,
        agent_id=args.agent_id
    )

    if report is None:
        sys.exit(1)

    # Save artifact
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_artifact(report, str(output_path))

    print(f"\n[Artifact Saved]")
    print(f"Path: {output_path}")
    print(f"Type: verification_report")

    sys.exit(0 if report.overall_pass else 1)
