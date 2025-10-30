"""Orchestrated Adaptive Execution

Integrates deliberation into execution loop for autonomous adaptation.
When quality issues detected, calls deliberate.py to create fix plans.
"""
from __future__ import annotations
import sys, json, subprocess, time
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.gateway.policy import Policy
from src.orchestrator.cycle import execute_action
from src.agents.agent_wrapper import append_transcript

def _ts():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def build_observation(action: dict, result: dict, obs_files: list[str] = None) -> dict:
    """Build rich observation including file contents and filesystem evidence.

    Args:
        action: The action that was executed
        result: Execution result with ok, stdout, stderr
        obs_files: Optional list of files to parse (from plan.meta observables)

    Returns:
        Observation dict with parsed data
    """
    obs = {
        "action_type": action.get("type"),
        "result_ok": result.get("ok", False),
        "stdout_preview": result.get("stdout", "")[:500],
        "stderr_preview": result.get("stderr", "")[:500],
    }

    # If action created output files, try to parse them
    if obs_files:
        obs["parsed_files"] = {}
        for fpath in obs_files:
            p = Path(fpath)
            if p.exists():
                try:
                    if p.suffix == ".json":
                        obs["parsed_files"][fpath] = json.loads(p.read_text(encoding="utf-8"))
                    else:
                        obs["parsed_files"][fpath] = p.read_text(encoding="utf-8")[:1000]
                except Exception as e:
                    obs["parsed_files"][fpath] = f"Error reading: {e}"

    # If script execution, include script code
    if action.get("type") == "exec.container_cmd":
        params = action.get("params", {})
        cmd = params.get("cmd", [])
        if len(cmd) >= 2 and cmd[0] == "python":
            script_path = Path(cmd[1])
            if script_path.exists():
                code = script_path.read_text(encoding="utf-8")
                obs["script_code"] = code[:3000]  # Truncate to avoid huge prompts

    return obs

def check_output_quality(action: dict, result: dict, obs: dict) -> dict:
    """Check output quality using heuristics.

    Returns:
        Quality assessment: {"quality": "good"|"suspicious"|"bad", "issues": [...]}
    """
    issues = []

    # Basic check: action failed
    if not result.get("ok"):
        return {
            "quality": "bad",
            "issues": [f"Action failed: {result.get('error', 'unknown error')}"]
        }

    # Check parsed files for suspicious patterns
    parsed = obs.get("parsed_files", {})

    # Pattern 1: Dataset analysis with 0 suitable videos despite real videos found
    for fpath, data in parsed.items():
        if isinstance(data, dict) and "report.json" in fpath:
            total_real = data.get("total_real", 0)
            suitable_real = data.get("suitable_real_count", -1)

            if total_real > 0 and suitable_real == 0:
                issues.append(
                    f"Found {total_real} real videos but 0 suitable (≥10s, ≥720p) "
                    f"- likely metadata parsing failure (.info.json vs .json)"
                )

    # Pattern 2: Empty output when expecting data
    stdout = result.get("stdout", "")
    if action.get("type") == "exec.container_cmd" and len(stdout) < 50:
        issues.append("Unusually short output from script execution")

    # Pattern 3: Error messages in stdout/stderr
    stderr = result.get("stderr", "")
    error_keywords = ["error:", "exception:", "traceback", "failed"]
    if any(kw in stderr.lower() for kw in error_keywords):
        issues.append(f"Error indicators in stderr: {stderr[:200]}")

    if issues:
        return {"quality": "suspicious", "issues": issues}

    return {"quality": "good", "issues": []}

def call_deliberation_for_fix(action: dict, obs: dict, issues: list[str]) -> Optional[dict]:
    """Call deliberate.py to create a fix plan.

    Args:
        action: The failing action
        obs: Rich observation data
        issues: List of quality issues detected

    Returns:
        Approved fix plan dict, or None if deliberation failed
    """
    # Create a fix task description
    fix_task_brief = f"""Fix quality issues in action execution.

FAILING ACTION:
{json.dumps(action, indent=2)}

QUALITY ISSUES DETECTED:
{chr(10).join(f"- {issue}" for issue in issues)}

OBSERVATION:
{json.dumps(obs, indent=2, default=str)}

TASK:
Create a plan to fix the issues. The fix may involve:
- Correcting file paths or patterns (e.g., .info.json vs .json)
- Modifying scripts that process data
- Adjusting action parameters

Use fs.replace to modify scripts in workspace/ or staging/.
End with the corrected version of the failing action to retry.
"""

    # Write temporary task file
    task_file = Path("tasks/temp_fix_task.md")
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(fix_task_brief, encoding="utf-8")

    # Call deliberate.py
    try:
        result = subprocess.run(
            ["python", "scripts/deliberate.py", "--task", str(task_file)],
            capture_output=True,
            text=True,
            timeout=600,
            cwd=Path.cwd()
        )

        if result.returncode != 0:
            print(f"❌ Deliberation failed: {result.stderr}")
            return None

        # Parse final plan from transcript
        transcript_file = Path("reports/deliberation_transcript.jsonl")
        if not transcript_file.exists():
            print("❌ No deliberation transcript found")
            return None

        # Get last decision record
        records = transcript_file.read_text(encoding="utf-8").strip().split("\n")
        for line in reversed(records):
            rec = json.loads(line)
            if rec.get("phase") == "decision":
                if rec.get("approved"):
                    return rec.get("final_plan")

        print("❌ No approved plan in deliberation transcript")
        return None

    except subprocess.TimeoutExpired:
        print("❌ Deliberation timeout after 600s")
        return None
    except Exception as e:
        print(f"❌ Deliberation error: {e}")
        return None

def apply_fix_plan(fix_plan: dict, policy: Policy) -> bool:
    """Apply the fix plan actions.

    Args:
        fix_plan: Approved plan from deliberation
        policy: Policy instance for validation

    Returns:
        True if all actions succeeded, False otherwise
    """
    actions = fix_plan.get("actions", [])
    if not actions:
        print("⚠️  Fix plan has no actions")
        return False

    fix_plan_id = fix_plan.get("plan_id", "fix_unknown")
    print(f"📋 Applying {len(actions)} fix actions...")

    for idx, action in enumerate(actions, 1):
        action_type = action.get("type")
        print(f"  [{idx}/{len(actions)}] {action_type}")

        # Execute action
        result = execute_action(action, policy, fix_plan_id)

        if not result.get("ok"):
            print(f"  ❌ Fix action failed: {result.get('error')}")
            return False

        print(f"  ✅ Success")

    return True

def run_adaptive(approved_plan: dict, action_observables: dict = None) -> dict:
    """Run plan with adaptive fixing.

    Args:
        approved_plan: The approved plan to execute
        action_observables: Optional dict mapping action_id -> list of observable files

    Returns:
        Execution result: {"ok": bool, "executed": int, "reason": str}
    """
    policy = Policy()
    executed = []
    obs_map = action_observables or {}
    plan_id = approved_plan.get("plan_id", "unknown")

    actions = approved_plan.get("actions", [])
    print(f"\n🚀 Starting adaptive execution of {len(actions)} actions\n")

    for idx, action in enumerate(actions, 1):
        action_id = action.get("id", f"A{idx}")
        action_type = action.get("type")

        print(f"[{idx}/{len(actions)}] Executing {action_id} ({action_type})...")

        # Get observable files for this action
        obs_files = obs_map.get(action_id, [])

        # Execute once
        result = execute_action(action, policy, plan_id)
        obs = build_observation(action, result, obs_files)
        quality = check_output_quality(action, result, obs)

        # Log to transcript
        append_transcript("reports/execution_transcript.jsonl", {
            "timestamp": _ts(),
            "phase": "execute",
            "action_id": action_id,
            "action_type": action_type,
            "result_ok": result.get("ok", False),
            "quality": quality["quality"],
            "issues": quality.get("issues", [])
        })

        if quality["quality"] == "good":
            print(f"  ✅ Success (quality: good)")
            executed.append({"action": action, "result_ok": True})
            continue

        # Quality suspicious or bad - trigger deliberation
        print(f"  ⚠️  Quality {quality['quality']}: {quality['issues']}")
        print(f"  🤔 Calling deliberation for fix...")

        append_transcript("reports/execution_transcript.jsonl", {
            "timestamp": _ts(),
            "phase": "quality_issue",
            "action_id": action_id,
            "issues": quality["issues"],
            "triggering_deliberation": True
        })

        fix_plan = call_deliberation_for_fix(action, obs, quality["issues"])

        if not fix_plan:
            print(f"  ❌ Deliberation failed to produce fix")
            append_transcript("reports/execution_transcript.jsonl", {
                "timestamp": _ts(),
                "phase": "deliberation_failed",
                "action_id": action_id
            })
            return {
                "ok": False,
                "reason": f"deliberation_failed_for_{action_id}",
                "executed": len(executed)
            }

        print(f"  ✅ Fix plan approved, applying...")
        append_transcript("reports/execution_transcript.jsonl", {
            "timestamp": _ts(),
            "phase": "applying_fix",
            "action_id": action_id,
            "fix_plan_id": fix_plan.get("plan_id")
        })

        if not apply_fix_plan(fix_plan, policy):
            print(f"  ❌ Fix plan failed to apply")
            return {
                "ok": False,
                "reason": f"fix_plan_failed_for_{action_id}",
                "executed": len(executed)
            }

        # Retry the original action
        print(f"  🔄 Retrying original action...")
        result = execute_action(action, policy, plan_id)
        obs = build_observation(action, result, obs_files)
        quality = check_output_quality(action, result, obs)

        append_transcript("reports/execution_transcript.jsonl", {
            "timestamp": _ts(),
            "phase": "retry",
            "action_id": action_id,
            "result_ok": result.get("ok", False),
            "quality": quality["quality"]
        })

        if quality["quality"] in ("suspicious", "bad"):
            print(f"  ❌ Post-fix quality still {quality['quality']}")
            return {
                "ok": False,
                "reason": f"post_fix_still_poor_for_{action_id}",
                "executed": len(executed)
            }

        print(f"  ✅ Retry successful (quality: {quality['quality']})")
        executed.append({"action": action, "result_ok": True})

    print(f"\n✅ Adaptive execution complete: {len(executed)}/{len(actions)} actions succeeded\n")

    return {
        "ok": True,
        "executed": len(executed),
        "total": len(actions)
    }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Orchestrated adaptive execution")
    parser.add_argument("--plan", required=True, help="Path to approved plan JSON")
    parser.add_argument("--task", help="Path to original task (for context)")
    args = parser.parse_args()

    # Load plan
    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"❌ Plan not found: {plan_path}")
        sys.exit(1)

    plan_data = json.loads(plan_path.read_text(encoding="utf-8"))

    # Handle review-wrapped plans (from critic output)
    if "plan" in plan_data and "approved" in plan_data:
        print(f"📋 Unwrapping reviewed plan (approved: {plan_data['approved']})")
        plan = plan_data["plan"]
    else:
        plan = plan_data

    # Extract observable hints from plan.meta actions if present
    action_observables = {}
    for action in plan.get("actions", []):
        if action.get("type") == "plan.meta":
            obs = action.get("params", {}).get("observables", {})
            action_observables.update(obs)

    # Run adaptive execution
    result = run_adaptive(plan, action_observables)

    if result["ok"]:
        print(f"✅ Execution succeeded: {result['executed']}/{result['total']} actions")
        sys.exit(0)
    else:
        print(f"❌ Execution failed: {result.get('reason')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
