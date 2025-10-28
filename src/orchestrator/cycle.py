from pathlib import Path, PurePosixPath
import json, time
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from gateway.gateway import ingest_promote
from gateway.policy import Policy

LEDGER = Path("reports/ledger.jsonl")

def log(kind, **kw):
    rec = {"ts": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), "kind": kind}
    rec.update(kw)
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")

def execute_action(action, policy, plan_id):
    """Execute a single action from the plan"""
    action_id = action.get('id', 'unknown')
    action_type = action['type']

    if action_type == 'fs.write':
        # Write file to staging or workspace
        params = action['params']
        path = Path(params['path'])
        content = params['content']

        # Create parent directory
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

        log("action_result", action_id=action_id, type=action_type, ok=True, path=str(path))
        return {"ok": True, "action_id": action_id, "path": str(path)}

    elif action_type == 'ingest.promote':
        # Promote files from staging to dataset
        items = action.get('items', [])
        results = ingest_promote(items, policy, plan_id=plan_id)

        all_ok = all(r.get('ok', False) for r in results)
        log("action_result", action_id=action_id, type=action_type, ok=all_ok, results=results)
        return {"ok": all_ok, "action_id": action_id, "results": results}

    else:
        log("action_result", action_id=action_id, type=action_type, ok=False, error=f"unknown action type: {action_type}")
        return {"ok": False, "action_id": action_id, "error": f"unknown action type"}

def run_cycle():
    # Minimal: create a scorecard placeholder if missing
    rep = Path("reports/diversity_report.json")
    if rep.exists():
        log("scorecard_generated", report=str(rep))
    else:
        log("report_missing")

    # If plans exist, execute them
    hp = Path("plans/hunt_plan.json")
    rp = Path("plans/reviewed_plan.json")

    if hp.exists() and rp.exists():
        log("plan_ready", hunt=str(hp), reviewed=str(rp))

        # Load reviewed plan
        with open(rp, 'r', encoding='utf-8') as f:
            reviewed = json.load(f)

        if not reviewed.get('approved', False):
            log("plan_rejected", reason="not approved")
            return

        plan = reviewed.get('plan', {})
        plan_id = plan.get('plan_id', 'unknown')
        actions = plan.get('actions', [])

        # Load policy
        policy = Policy()

        # Execute each action
        for action in actions:
            try:
                result = execute_action(action, policy, plan_id)
                if not result.get('ok', False):
                    log("plan_execution_failed", plan_id=plan_id, action_id=action.get('id'))
                    break
            except Exception as e:
                log("action_error", action_id=action.get('id'), error=str(e))
                break
        else:
            log("plan_execution_complete", plan_id=plan_id)
    else:
        log("plan_missing")
