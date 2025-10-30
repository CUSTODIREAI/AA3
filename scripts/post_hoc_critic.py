#!/usr/bin/env python3
"""Post-Hoc Critic - Automatic red-flag detection for Direct-Action sessions"""
from __future__ import annotations
import json, argparse, sys
from pathlib import Path

LEDGER = Path("reports/ledger.jsonl")
WORKSPACE = Path("workspace")

def read_ledger():
    if not LEDGER.exists():
        return []
    events = []
    with LEDGER.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except:
                    continue
    return events

def get_latest_session(events):
    sessions = []
    for ev in events:
        if ev.get("kind") == "direct_start":
            sessions.append((ev.get("ts"), ev.get("session")))
    if not sessions:
        return None
    sessions.sort(reverse=True)
    return sessions[0][1]

def analyze_session(session_id, events):
    session_events = [e for e in events if e.get("session") == session_id]
    if not session_events:
        return {"error": f"No events found for session {session_id}"}
    
    start_event = next((e for e in session_events if e.get("kind") == "direct_start"), None)
    end_event = next((e for e in session_events if e.get("kind") == "direct_end"), None)
    
    if not start_event:
        return {"error": "No start event found"}
    
    task = start_event.get("task", "unknown")
    budget = start_event.get("budget", 15)
    commands = [e for e in session_events if e.get("kind") == "direct_cmd"]
    results = [e for e in session_events if e.get("kind") == "direct_cmd_result"]
    total_commands = len(commands)
    failed_commands = [r for r in results if not r.get("ok", True)]
    failure_rate = len(failed_commands) / total_commands if total_commands > 0 else 0
    done_event = next((e for e in session_events if e.get("kind") == "direct_done"), None)
    completed = done_event is not None or (end_event and end_event.get("completed", False))
    expected_evidence = ["versions.json", "build.log", "test.log", "gpu_info.txt"]
    evidence_found = [f for f in expected_evidence if (WORKSPACE / f).exists()]
    publish_events = [e for e in session_events if e.get("kind") == "direct_publish"]
    artifacts_promoted = len(publish_events) > 0
    gpu_commands = [c for c in commands if "nvidia-smi" in c.get("cmd", "").lower()]
    gpu_used = len(gpu_commands) > 0
    
    red_flags = []
    warnings = []
    if failure_rate > 0.3:
        red_flags.append(f"High command failure rate: {failure_rate:.1%} ({len(failed_commands)}/{total_commands})")
    if not completed and total_commands >= budget:
        red_flags.append(f"Session exceeded budget ({budget}) without completing")
    if not artifacts_promoted:
        red_flags.append("No artifacts promoted to dataset")
    if len(evidence_found) == 0:
        red_flags.append("No evidence files created in workspace/")
    if total_commands > 5 and not gpu_used:
        warnings.append("No GPU usage detected (nvidia-smi not run)")
    if len(failed_commands) > 0:
        warnings.append(f"{len(failed_commands)} command(s) failed (exit code != 0)")
    
    return {
        "session": session_id, "task": task, "total_commands": total_commands,
        "budget": budget, "failure_rate": failure_rate, "completed": completed,
        "evidence_found": evidence_found, "artifacts_promoted": artifacts_promoted,
        "gpu_used": gpu_used, "red_flags": red_flags, "warnings": warnings,
        "failed_commands": [{"turn": r.get("turn"), "returncode": r.get("returncode")} for r in failed_commands]
    }

def print_report(analysis):
    if "error" in analysis:
        print(f"ERROR: {analysis['error']}")
        return
    print("="*60)
    print("Direct-Action Post-Hoc Report")
    print("="*60)
    print(f"\nSession:    {analysis['session']}")
    print(f"Task:       {analysis['task']}")
    print(f"Commands:   {analysis['total_commands']}/{analysis['budget']}")
    print(f"Completed:  {'Yes' if analysis['completed'] else 'No'}")
    print(f"Failure Rate: {analysis['failure_rate']:.1%}\n")
    print("Evidence Files:")
    if analysis['evidence_found']:
        for f in analysis['evidence_found']:
            print(f"  {f}")
    else:
        print("  No evidence files found")
    print(f"\nArtifacts Promoted: {'Yes' if analysis['artifacts_promoted'] else 'No'}")
    print(f"GPU Used: {'Yes' if analysis['gpu_used'] else 'No'}\n")
    if analysis['red_flags']:
        print("RED FLAGS:")
        for flag in analysis['red_flags']:
            print(f"  {flag}")
        print()
    if analysis['warnings']:
        print("WARNINGS:")
        for warn in analysis['warnings']:
            print(f"  {warn}")
        print()
    if analysis['failed_commands']:
        print("Failed Commands:")
        for fc in analysis['failed_commands']:
            print(f"  Turn {fc['turn']}: exit code {fc['returncode']}")
        print()
    print("="*60)
    if not analysis['red_flags']:
        print("VERDICT: Session passed post-hoc review")
    else:
        print(f"VERDICT: Session has {len(analysis['red_flags'])} red flag(s)")
    print("="*60)

def main():
    ap = argparse.ArgumentParser(description="Post-hoc critic for Direct-Action sessions")
    ap.add_argument("--session", help="Session ID to analyze")
    ap.add_argument("--latest", action="store_true", help="Analyze the most recent session")
    args = ap.parse_args()
    if not args.session and not args.latest:
        print("ERROR: Must specify --session <id> or --latest")
        sys.exit(1)
    events = read_ledger()
    if not events:
        print("ERROR: No events found in reports/ledger.jsonl")
        sys.exit(1)
    if args.latest:
        session_id = get_latest_session(events)
        if not session_id:
            print("ERROR: No direct-action sessions found in ledger")
            sys.exit(1)
        print(f"Analyzing latest session: {session_id}\n")
    else:
        session_id = args.session
    analysis = analyze_session(session_id, events)
    print_report(analysis)
    if "error" in analysis or analysis['red_flags']:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
