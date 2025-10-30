#!/usr/bin/env python3
"""
Direct-Action Mode (Freedom Mode++)

Bypasses plan → approve → execute friction.
Agents execute commands directly in GPU sandbox, with post-hoc audit only.

Core principle: Agent has terminal freedom; system protects evidence.
"""
from __future__ import annotations
import json, time, uuid, subprocess, sys, re
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

LEDGER = Path("reports/ledger.jsonl")

def log(kind: str, **kw):
    """Append-only ledger for audit trail"""
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "kind": kind}
    rec.update(kw)
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def is_safe_command(cmd: str) -> tuple[bool, str]:
    """
    Check if command is safe to execute.

    Blocks:
    - rm commands (file deletion)
    - docker prune (cleanup)
    - docker rm (container removal)
    - docker run --rm (ephemeral containers)
    - destructive operations on immutable dirs

    Returns: (is_safe, rejection_reason)
    """
    cmd_lower = cmd.lower()

    # Block rm commands
    if re.match(r'\brm\b', cmd_lower):
        return (False, "BLOCKED: 'rm' command not allowed (use staging/ for temp files)")

    # Block docker prune
    if 'docker' in cmd_lower and 'prune' in cmd_lower:
        return (False, "BLOCKED: 'docker prune' not allowed (preserves all containers/images)")

    # Block docker rm
    if 'docker' in cmd_lower and re.search(r'\brm\b', cmd_lower):
        return (False, "BLOCKED: 'docker rm' not allowed (containers are persistent)")

    # Block docker run with --rm
    if 'docker' in cmd_lower and 'run' in cmd_lower and '--rm' in cmd:
        return (False, "BLOCKED: 'docker run --rm' not allowed (use persistent containers)")

    # Block operations on read-only dirs
    dangerous_patterns = [
        (r'>\s*/dataset/', "BLOCKED: Cannot write to /dataset (read-only)"),
        (r'>\s*/evidence/', "BLOCKED: Cannot write to /evidence (read-only)"),
        (r'>\s*/staging-final/', "BLOCKED: Cannot write to /staging-final (read-only)"),
    ]

    for pattern, msg in dangerous_patterns:
        if re.search(pattern, cmd):
            return (False, msg)

    return (True, "")


def run_passthrough(cmd: str, timeout: int = 3600) -> dict:
    """
    Execute command inside persistent GPU sandbox (agent-sandbox container).

    Mounts:
    - dataset/, evidence/, staging-final/ → read-only (immutable)
    - staging/, workspace/, cache/ → read-write (full freedom)

    Returns: {ok: bool, stdout: str, stderr: str, returncode: int}
    """
    # Safety check
    is_safe, reason = is_safe_command(cmd)
    if not is_safe:
        return {
            "ok": False,
            "stdout": "",
            "stderr": reason,
            "returncode": 1
        }

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


def ingest_glob(src_dir: str, pattern: str, rel_prefix: str, tags: dict) -> dict:
    """
    Promote files matching glob pattern to immutable dataset.

    Uses existing ingest.promote_glob action via cycle.py executor.
    """
    from src.orchestrator import cycle
    from gateway.policy import Policy

    # Build action for promote_glob
    action = {
        "type": "ingest.promote_glob",
        "id": f"ingest-{int(time.time())}",
        "params": {
            "src_dir": src_dir,
            "pattern": pattern,
            "relative_dst_prefix": rel_prefix,
            "tags": tags
        }
    }

    # Execute via orchestrator's execute_action
    policy = Policy()
    result = cycle.execute_action(action, policy, plan_id="direct-action")
    return result


def read_text(p: str|Path) -> str:
    """Read text file"""
    return Path(p).read_text(encoding="utf-8")


# System prompt for Direct-Action mode (SIMPLIFIED)
DIRECT_SYSTEM = """AI engineer in GPU sandbox. Full bash access.

Dirs:
- /workspace → your workspace (RW, save evidence here)
- /staging → stage for dataset promotion (RW)
- /dataset, /evidence → read-only

Commands available: curl, docker, nvidia-smi, git, pip, all bash tools

Return ONLY next bash command (one line). When done: echo "DONE: summary"
"""


def agent_next_command(task: str, history: list[str], tools_context: str = "") -> str:
    """
    Ask agent for next command to execute.

    Returns: Single bash command line (no prose)
    """
    from src.agents.agent_wrapper import call_codex_cli

    # Build context from recent history (last 500 chars to keep it concise)
    hist_text = "\n".join(history[-5:])[-500:] if history else "Starting fresh."

    # Check if we've done enough work to allow completion
    allow_done = len(history) >= 3
    done_instruction = '\nWhen task is complete, return: echo "DONE: summary"' if allow_done else ""

    # For long tasks, provide more context (up to 1000 chars)
    task_desc = task[:1000] if len(task) > 1000 else task

    # Directive prompt - command-only with examples
    prompt = f"""Execute task in /workspace using bash commands.

TASK: {task_desc}

HISTORY: {hist_text}

Rules:
- Output ONE bash command (no explanation, no thinking)
- Must START with a command verb: cat, echo, mkdir, docker, curl, wget, etc.
- Paths alone are NOT commands: /workspace/file.txt is INVALID
- Valid examples: cat > file.txt, mkdir -p /workspace/dir, docker build -t name .
- Invalid examples: /workspace/file, file.txt, "First we should..."{done_instruction}

COMMAND:"""

    # Call Codex for next command (15 min timeout - Codex is a CS professor, let it think)
    # "Trust the agent. Only catch true hangs (network failures, crashes), not deep thinking."
    timeout = 900
    output = call_codex_cli(prompt, timeout=timeout)

    # Extract command - find actual bash commands in codex output
    lines = output.split('\n')

    # Common command list used for validation
    common_cmds = ['ls', 'cd', 'pwd', 'cat', 'echo', 'date', 'curl', 'wget', 'docker', 'git',
                   'mkdir', 'touch', 'cp', 'mv', 'grep', 'find', 'python', 'bash',
                   'nvidia-smi', 'uname', 'apt', 'pip', 'chmod', 'chown', 'tar', 'gzip', 'printf']

    # First try: look for commands in backticks or after "command is"

    # Pattern 1: Look for bash command in backticks
    backtick_match = re.search(r'`([^`]+)`', output)
    if backtick_match:
        potential_cmd = backtick_match.group(1).strip()
        # Reject standalone paths (paths without command verbs)
        is_standalone_path = potential_cmd.startswith('/') and not any(potential_cmd.startswith(f'{c} ') or potential_cmd.startswith(f'{c}\t') for c in common_cmds)
        if not is_standalone_path and len(potential_cmd) > 3 and not potential_cmd.startswith('$'):
            return potential_cmd

    # Pattern 2: Look for "command is: ..." or "proposed command is..."
    command_match = re.search(r'(?:proposed |my )?command (?:is|would be):?\s*(.+?)(?:\n|$|\.|;$)', output, re.IGNORECASE)
    if command_match:
        potential_cmd = command_match.group(1).strip('` "\'').strip()
        # Strip leading shell prompts and bullet points from examples
        potential_cmd = re.sub(r'^[$#>]\s*', '', potential_cmd)  # Remove $ # > prompts
        potential_cmd = re.sub(r'^[-*]\s+', '', potential_cmd)   # Remove bullet points
        # Reject standalone paths (paths without command verbs)
        is_standalone_path = potential_cmd.startswith('/') and not any(potential_cmd.startswith(f'{c} ') or potential_cmd.startswith(f'{c}\t') for c in common_cmds)
        if not is_standalone_path and len(potential_cmd) > 3:
            return potential_cmd

    # Pattern 3: Scan lines for bash commands
    for line in lines:
        stripped = line.strip()

        # Skip empty, timestamps, metadata, separators
        if not stripped: continue
        if stripped.startswith('[2025-'): continue
        if 'tokens used' in stripped.lower(): continue
        if stripped == 'codex': continue
        if all(c in '-_=*#' for c in stripped): continue

        # Skip prose sentences (capital letters, periods, long words)
        if len(stripped) > 10:
            # Check if it's a sentence (starts with capital, contains common words)
            if stripped[0].isupper() and any(word in stripped for word in [' the ', ' is ', ' are ', ' was ', ' can ', ' will ', ' should ', 'that ', 'this ', 'with ']):
                continue

        # Skip lines with multiple capital words (prose)
        capital_words = sum(1 for word in stripped.split() if word and word[0].isupper())
        if capital_words >= 3:
            continue

        # Skip prose indicators
        if any(phrase in stripped for phrase in ["I'm", "I am", "The user", "Let me", "Here is", "This is", "We need", "You should"]):
            continue

        # Skip metadata "key: value" style
        if ':' in stripped[:30] and not any(stripped.startswith(cmd) for cmd in ['echo', 'cat', 'docker', 'python']):
            continue

        # Skip bash help output
        if stripped.startswith('Usage:') or 'GNU long option' in stripped or '[option]' in stripped:
            continue

        # Clean up
        cmd = stripped.strip('`').strip('"').strip("'").strip()
        # Strip leading prompts and bullets from examples
        cmd = re.sub(r'^[$#>]\s*', '', cmd)  # Remove $ # > prompts
        cmd = re.sub(r'^[-*]\s+', '', cmd)   # Remove bullet points

        # Skip if too short or looks weird
        if len(cmd) < 3 or cmd.startswith('--') or cmd.startswith('['):
            continue

        # Check if looks like bash command
        first_word = cmd.split()[0] if cmd.split() else ""

        # REJECT pure paths (starts with / but no command)
        if cmd.startswith('/') and not any(cmd.startswith(f'{c} ') or cmd == c for c in common_cmds):
            continue

        # Reject if first word ends with / (directory path, not command)
        if first_word.endswith('/'):
            continue

        # Reject paths with file extensions (not commands)
        if '/' in first_word and any(first_word.endswith(ext) for ext in ['.py', '.sh', '.txt', '.md', '.json', '.yml', '.yaml', '.Dockerfile']):
            continue

        # Accept if starts with known command OR has command-like operators
        if first_word in common_cmds or '|' in cmd or '&&' in cmd or '>' in cmd or '<<' in cmd:
            # Final validation: not a fragment
            if len(cmd) > 3 and not cmd.endswith('...'):
                return cmd

    # Fallback: check workspace status
    return "ls -la /workspace/"


def direct_run(task_file: str, autonomy_budget: int = 15, tools_context: str = "") -> dict:
    """
    Direct-Action execution mode.

    Agent executes commands in sandbox until task is done or budget exhausted.
    No pre-approval, only post-hoc audit via ledger.

    Args:
        task_file: Path to task markdown file
        autonomy_budget: Max number of commands to execute
        tools_context: Optional tools awareness context

    Returns:
        {ok: bool, turns: int, artifacts: list, session: str}
    """
    session = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    task = read_text(task_file)

    log("direct_start", session=session, task=task_file, budget=autonomy_budget)
    print(f"=== Direct-Action Mode ===")
    print(f"Session: {session}")
    print(f"Task: {task_file}")
    print(f"Budget: {autonomy_budget} commands")
    print(f"Sandbox: agent-sandbox container")
    print(f"")

    history = []
    done = False

    for i in range(autonomy_budget):
        print(f"\n--- Turn {i+1}/{autonomy_budget} ---")

        # Get next command from agent
        try:
            cmd = agent_next_command(task, history, tools_context)
        except Exception as e:
            log("direct_error", session=session, turn=i+1, error=str(e))
            print(f"ERROR getting next command: {e}")
            break

        print(f"$ {cmd}")
        history.append(f"$ {cmd}")
        log("direct_cmd", session=session, turn=i+1, cmd=cmd)

        # Check for DONE sentinel (must be echo "DONE:..." not just any DONE substring)
        if "echo" in cmd.lower() and re.search(r'echo\s+["\']DONE', cmd, re.IGNORECASE):
            print(f"\n[DONE] Agent signaled completion: {cmd}")
            log("direct_done", session=session, turn=i+1, completion_cmd=cmd)
            done = True
            break

        # Execute command
        try:
            res = run_passthrough(cmd, timeout=1800)  # 30 min max per command
        except subprocess.TimeoutExpired:
            log("direct_timeout", session=session, turn=i+1, cmd=cmd)
            print(f"[TIMEOUT] Command exceeded 30 minute limit")
            history.append(f"[TIMEOUT after 30 minutes]")
            continue
        except Exception as e:
            log("direct_exec_error", session=session, turn=i+1, cmd=cmd, error=str(e))
            print(f"[ERROR] Execution failed: {e}")
            history.append(f"[ERROR: {e}]")
            continue

        # Show output
        output = (res.get("stdout", "") + res.get("stderr", "")).strip()
        output_preview = output[-1500:] if len(output) > 1500 else output  # Show last 1500 chars

        if output_preview:
            print(f"{output_preview}")

        ok_marker = "[OK]" if res.get("ok") else "[FAIL]"
        print(f"{ok_marker} Exit code: {res.get('returncode', 'unknown')}")

        # Add to history
        history.append(output[-1000:] if output else "[no output]")

        log("direct_cmd_result",
            session=session,
            turn=i+1,
            ok=res.get("ok", False),
            returncode=res.get("returncode"),
            output_len=len(output))

        # Simple heuristic: check for completion evidence
        workspace_has_evidence = any([
            Path("workspace/versions.json").exists(),
            Path("workspace/build.log").exists(),
            Path("workspace/test.log").exists(),
            Path("workspace/gpu_info.txt").exists()
        ])

        if workspace_has_evidence and i >= 3:  # At least 3 commands executed
            print(f"\n[INFO] Evidence files detected in workspace. Task may be complete.")

    # Post-execution: check for artifacts to promote
    print(f"\n\n=== Post-Execution Artifact Check ===")
    artifacts = []

    # Check staging directory for files to promote
    staging_path = Path("staging")
    if staging_path.exists():
        artifact_count = sum(1 for _ in staging_path.rglob("*") if _.is_file())
        print(f"Found {artifact_count} files in staging/")

        if artifact_count > 0:
            # Promote all staging files
            try:
                result = ingest_glob(
                    src_dir="staging",
                    pattern="**/*",
                    rel_prefix=f"direct/{session}/",
                    tags={"session": session, "mode": "direct", "task": task_file}
                )
                artifacts.append(result)
                log("direct_publish", session=session, result=result)
                print(f"[OK] Promoted {artifact_count} files to dataset/direct/{session}/")
            except Exception as e:
                log("direct_publish_error", session=session, error=str(e))
                print(f"[FAIL] Promotion error: {e}")

    # Final summary
    turns_used = min(i + 1, autonomy_budget)
    log("direct_end",
        session=session,
        turns=turns_used,
        completed=done,
        artifacts=len(artifacts))

    print(f"\n\n=== Session Complete ===")
    print(f"Turns used: {turns_used}/{autonomy_budget}")
    print(f"Completed: {'Yes' if done else 'Budget exhausted'}")
    print(f"Artifacts promoted: {len(artifacts)}")
    print(f"Full audit trail: {LEDGER}")
    print(f"Session ID: {session}")

    return {
        "ok": done or len(artifacts) > 0,
        "turns": turns_used,
        "artifacts": artifacts,
        "session": session,
        "completed": done
    }


if __name__ == "__main__":
    import argparse

    # Build tools context
    try:
        from src.agents.tools_context import build_tools_context
        tools_ctx = build_tools_context()
    except:
        tools_ctx = ""

    ap = argparse.ArgumentParser(description="Direct-Action Mode: Terminal freedom for agents")
    ap.add_argument("task", help="Path to task file (e.g., tasks/build_dfl_docker_rtx4090.md)")
    ap.add_argument("--budget", type=int, default=15, help="Max number of commands (default: 15)")
    args = ap.parse_args()

    if not Path(args.task).exists():
        print(f"ERROR: Task file not found: {args.task}")
        sys.exit(1)

    result = direct_run(args.task, autonomy_budget=args.budget, tools_context=tools_ctx)

    sys.exit(0 if result["ok"] else 1)
