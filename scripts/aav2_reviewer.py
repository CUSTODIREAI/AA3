#!/usr/bin/env python3
"""
AAv2 Reviewer Agent - Codex Diagnoses Failures

When verification fails, reviewer analyzes execution transcript
and verification report to diagnose issues and suggest fixes.

NOTE: This is simplified version. Full implementation would
call Codex API for actual reasoning and diagnosis.
"""
from __future__ import annotations
import sys, re, uuid
from pathlib import Path
from typing import List

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.aav2_artifacts import (
    VerificationReport, DiagnosisDocument, FailureDiagnosis,
    timestamp_now, save_artifact, load_artifact
)


def diagnose_failure(cmd_exec: dict, criteria_fail: dict, task_context: str = "") -> FailureDiagnosis:
    """
    Analyze failure and suggest fix.

    USES REAL CODEX/CLAUDE API for diagnosis!
    """
    from scripts.aav2_llm_integration import diagnose_with_llm

    cmd = cmd_exec.get("command", "")
    stderr = cmd_exec.get("stderr", "")
    stdout = cmd_exec.get("stdout", "")
    exit_code = cmd_exec.get("exit_code", 0)

    # Call REAL LLM for diagnosis
    try:
        result = diagnose_with_llm(
            failed_command=cmd,
            stderr=stderr,
            stdout=stdout,
            task_context=task_context,
            use_claude=False  # Use OpenAI Codex for diagnosis
        )

        if result.get("llm_used", False):
            # SUCCESS - LLM gave us real diagnosis
            return FailureDiagnosis(
                command=cmd,
                error_type=result["error_type"],
                root_cause=result["root_cause"],
                suggested_fix=result["suggested_fix"],
                confidence=float(result["confidence"])
            )
    except Exception as e:
        print(f"[WARN] LLM diagnosis failed: {e}, falling back to heuristics")

    # Fallback to heuristics if LLM unavailable
    error_type = "unknown"
    root_cause = "Command failed with unknown error"
    suggested_fix = "Retry command after investigating logs"
    confidence = 0.3

    # Permission denied
    if "permission denied" in stderr.lower() or exit_code == 126:
        error_type = "permission"
        root_cause = "Insufficient permissions to execute command"
        if "docker" in cmd:
            suggested_fix = "Ensure user is in docker group or use sudo"
        else:
            suggested_fix = "Use sudo or check file permissions"
        confidence = 0.85

    # File not found
    elif "no such file or directory" in stderr.lower() or exit_code == 127:
        error_type = "not_found"
        # Extract filename if possible
        match = re.search(r"(?:no such file or directory|cannot access|not found)[:\s]+([^\s\n]+)", stderr, re.I)
        filename = match.group(1) if match else "file/command"
        root_cause = f"{filename} not found"
        suggested_fix = f"Create missing file/directory or check path: {filename}"
        confidence = 0.9

    # Network errors
    elif any(x in stderr.lower() for x in ["connection refused", "connection timed out", "network", "could not resolve"]):
        error_type = "network"
        root_cause = "Network connectivity issue"
        suggested_fix = "Check network connection, firewall, or service availability"
        confidence = 0.8

    # Docker errors
    elif "docker" in cmd and "error" in stderr.lower():
        error_type = "docker"
        if "no such container" in stderr.lower():
            root_cause = "Docker container not found or not running"
            suggested_fix = "Start container or check container name"
            confidence = 0.9
        elif "image not found" in stderr.lower():
            root_cause = "Docker image not found"
            suggested_fix = "Build or pull the required image"
            confidence = 0.9
        else:
            root_cause = "Docker command failed"
            suggested_fix = "Check Docker daemon status and command syntax"
            confidence = 0.6

    # Syntax errors
    elif "syntax error" in stderr.lower() or exit_code == 2:
        error_type = "syntax"
        root_cause = "Command syntax error"
        suggested_fix = "Check command syntax and quote special characters"
        confidence = 0.85

    # Disk space
    elif any(x in stderr.lower() for x in ["no space left", "disk full", "quota exceeded"]):
        error_type = "disk_space"
        root_cause = "Insufficient disk space"
        suggested_fix = "Free up disk space or increase storage"
        confidence = 0.95

    return FailureDiagnosis(
        command=cmd,
        error_type=error_type,
        root_cause=root_cause,
        suggested_fix=suggested_fix,
        confidence=confidence
    )


def review_failures(transcript_path: str, report_path: str, agent_id: str = None, task_context: str = "") -> DiagnosisDocument:
    """
    Review failed execution and verification, diagnose issues.

    NOW USES REAL CODEX for diagnosis!

    Returns: DiagnosisDocument artifact
    """
    if agent_id is None:
        agent_id = f"reviewer_{uuid.uuid4().hex[:8]}"

    print(f"\n[Reviewer Agent (Codex): {agent_id}]")
    print(f"Transcript: {transcript_path}")
    print(f"Verification: {report_path}")
    print(f"Using: Real LLM diagnosis (Codex/Claude)")
    print("")

    # Load artifacts
    try:
        transcript = load_artifact(transcript_path)
        report = load_artifact(report_path)
    except Exception as e:
        print(f"[ERROR] Failed to load artifacts: {e}")
        return None

    report_id = f"{report['agent_id']}_{report['timestamp']}"

    # Get task context from transcript
    if not task_context:
        task_context = f"Task: {transcript.get('task_file', 'unknown')}"

    # Analyze failures
    print(f"[Analyzing Failures with LLM]\n")

    diagnoses = []
    fixable = 0
    unfixable = 0

    # Failed commands
    failed_cmds = [c for c in transcript["commands_executed"] if not c["success"]]

    for cmd_exec in failed_cmds:
        print(f"--- Failed Command ---")
        print(f"$ {cmd_exec['command']}")
        print(f"Error: {cmd_exec['stderr'][:200]}")

        # Find matching failed criteria if any
        criteria_fail = None  # In full version, match with verification failures

        diagnosis = diagnose_failure(cmd_exec, criteria_fail, task_context)
        diagnoses.append(diagnosis)

        print(f"[Diagnosis]")
        print(f"Type: {diagnosis.error_type}")
        print(f"Root cause: {diagnosis.root_cause}")
        print(f"Suggested fix: {diagnosis.suggested_fix}")
        print(f"Confidence: {diagnosis.confidence:.2%}\n")

        if diagnosis.confidence >= 0.7:
            fixable += 1
        else:
            unfixable += 1

    # Failed criteria (that aren't from failed commands)
    failed_criteria = [c for c in report["criteria_checked"] if not c["passed"]]

    for criteria in failed_criteria:
        # Skip if we already diagnosed command failures
        if failed_cmds:
            continue

        print(f"--- Failed Criterion ---")
        print(f"{criteria['description']}")

        # Diagnose why criteria failed
        diagnosis = FailureDiagnosis(
            command="<criteria_check>",
            error_type="verification",
            root_cause=f"Criterion not met: {criteria['description']}",
            suggested_fix="Review execution output and ensure all steps completed successfully",
            confidence=0.5
        )
        diagnoses.append(diagnosis)
        unfixable += 1

        print(f"[Diagnosis]")
        print(f"Root cause: {diagnosis.root_cause}")
        print(f"Suggested fix: {diagnosis.suggested_fix}\n")

    # Build recommended actions
    actions = []
    if fixable > 0:
        actions.append(f"Apply suggested fixes for {fixable} diagnosable failures")
    if unfixable > 0:
        actions.append(f"Manual investigation needed for {unfixable} unclear failures")
    if not diagnoses:
        actions.append("No failures to diagnose - verification passed")

    # Build diagnosis document
    doc = DiagnosisDocument(
        verification_report_id=report_id,
        agent_id=agent_id,
        failures_analyzed=diagnoses,
        total_failures=len(diagnoses),
        fixable_failures=fixable,
        unfixable_failures=unfixable,
        recommended_actions=actions,
        timestamp=timestamp_now()
    )

    print(f"[Reviewer Complete]")
    print(f"Total failures: {len(diagnoses)}")
    print(f"Fixable: {fixable}")
    print(f"Needs investigation: {unfixable}")

    return doc


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="AAv2 Reviewer Agent - Codex diagnoses failures")
    ap.add_argument("transcript", help="Path to execution transcript JSON")
    ap.add_argument("report", help="Path to verification report JSON")
    ap.add_argument("--agent-id", help="Agent ID (auto-generated if not provided)")
    ap.add_argument("--output", default="reports/aav2_diagnosis.json", help="Output path for diagnosis")
    args = ap.parse_args()

    if not Path(args.transcript).exists():
        print(f"ERROR: Transcript not found: {args.transcript}")
        sys.exit(1)

    if not Path(args.report).exists():
        print(f"ERROR: Verification report not found: {args.report}")
        sys.exit(1)

    # Diagnose failures
    diagnosis = review_failures(
        transcript_path=args.transcript,
        report_path=args.report,
        agent_id=args.agent_id
    )

    if diagnosis is None:
        sys.exit(1)

    # Save artifact
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_artifact(diagnosis, str(output_path))

    print(f"\n[Artifact Saved]")
    print(f"Path: {output_path}")
    print(f"Type: diagnosis_document")

    sys.exit(0)
