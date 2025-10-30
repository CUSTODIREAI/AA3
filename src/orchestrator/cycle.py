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

    elif action_type == 'ingest.promote_glob':
        # Promote files matching glob pattern to dataset
        from gateway.gateway import ingest_promote_glob
        params = action.get('params', {})
        src_dir = params.get('src_dir', 'staging')
        pattern = params.get('pattern', '**/*')
        relative_dst_prefix = params.get('relative_dst_prefix', '')
        tags = params.get('tags', {})

        results = ingest_promote_glob(
            src_dir=src_dir,
            pattern=pattern,
            relative_dst_prefix=relative_dst_prefix,
            tags=tags,
            policy=policy,
            plan_id=plan_id,
            actor='direct-action'
        )

        all_ok = all(r.get('ok', False) for r in results)
        log("action_result", action_id=action_id, type=action_type, ok=all_ok,
            files_promoted=len([r for r in results if r.get('ok')]))
        return {"ok": all_ok, "action_id": action_id, "results": results}

    elif action_type == 'exec.container_cmd':
        # Execute a command (typically to run analysis scripts)
        import subprocess
        params = action.get('params', {})
        cmd = params.get('cmd', '')

        if not cmd:
            log("action_result", action_id=action_id, type=action_type, ok=False, error="no cmd specified")
            return {"ok": False, "action_id": action_id, "error": "no cmd specified"}

        try:
            # Execute command in the project directory
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout for analysis
                cwd=Path.cwd()
            )

            ok = result.returncode == 0
            log("action_result", action_id=action_id, type=action_type, ok=ok,
                returncode=result.returncode, stdout_lines=len(result.stdout.splitlines()))

            return {
                "ok": ok,
                "action_id": action_id,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except subprocess.TimeoutExpired:
            log("action_result", action_id=action_id, type=action_type, ok=False, error="timeout")
            return {"ok": False, "action_id": action_id, "error": "timeout"}
        except Exception as e:
            log("action_result", action_id=action_id, type=action_type, ok=False, error=str(e))
            return {"ok": False, "action_id": action_id, "error": str(e)}

    elif action_type == 'agent.passthrough_shell':
        # Execute command inside persistent agent sandbox
        # Gives agents full freedom (GPU, network, all tools) while keeping dataset/evidence immutable
        import subprocess
        params = action.get('params', {})
        cmd = params.get('cmd', '')

        if not cmd:
            log("action_result", action_id=action_id, type=action_type, ok=False, error="no cmd specified")
            return {"ok": False, "action_id": action_id, "error": "no cmd specified"}

        # Check if agent-sandbox container exists and is running
        try:
            check_result = subprocess.run(
                ["docker", "ps", "--filter", "name=agent-sandbox", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if "agent-sandbox" not in check_result.stdout:
                error_msg = "agent-sandbox container not running. Run: scripts/start_agent_sandbox.sh"
                log("action_result", action_id=action_id, type=action_type, ok=False, error=error_msg)
                return {"ok": False, "action_id": action_id, "error": error_msg}

        except Exception as e:
            log("action_result", action_id=action_id, type=action_type, ok=False, error=f"failed to check sandbox: {e}")
            return {"ok": False, "action_id": action_id, "error": f"failed to check sandbox: {e}"}

        try:
            # Execute command inside agent-sandbox with full freedom
            # No timeout (or very long timeout) - let agents work freely
            timeout_sec = params.get('timeout_sec', 3600)  # Default 1 hour

            result = subprocess.run(
                ["docker", "exec", "-w", "/workspace", "agent-sandbox", "bash", "-c", cmd],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                cwd=Path.cwd()
            )

            ok = result.returncode == 0
            log("action_result", action_id=action_id, type=action_type, ok=ok,
                returncode=result.returncode,
                stdout_lines=len(result.stdout.splitlines()),
                stderr_lines=len(result.stderr.splitlines()),
                cmd_preview=cmd[:100])

            return {
                "ok": ok,
                "action_id": action_id,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }

        except subprocess.TimeoutExpired:
            log("action_result", action_id=action_id, type=action_type, ok=False, error="timeout")
            return {"ok": False, "action_id": action_id, "error": f"timeout after {timeout_sec}s"}
        except Exception as e:
            log("action_result", action_id=action_id, type=action_type, ok=False, error=str(e))
            return {"ok": False, "action_id": action_id, "error": str(e)}

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

if __name__ == '__main__':
    run_cycle()
