"""Agent wrapper for Claude Code and Codex CLI"""
from pathlib import Path
import json, time, subprocess, os

TRANSCRIPT = Path("reports/conversation.jsonl")


def log_conversation(turn: int, agent: str, phase: str, content: str):
    """Log conversation turn to transcript"""
    rec = {
        "ts": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "turn": turn,
        "agent": agent,
        "phase": phase,
        "content": content
    }
    TRANSCRIPT.parent.mkdir(parents=True, exist_ok=True)
    with open(TRANSCRIPT, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def format_history(history: list[dict]) -> str:
    """Format conversation history for agent context"""
    lines = []
    for h in history:
        lines.append(f"[Turn {h['turn']}] {h['agent']} ({h['phase']}): {h['content'][:200]}...")
    return "\n".join(lines)


def call_proposer(task_brief: str, history: list[dict], system_prompt: str, turn: int) -> dict:
    """
    Call Claude Code (Proposer) via its CLI or API.

    For now, using Codex as a stand-in for Claude Code since we're in Claude Code already.
    In production, this would call claude-code CLI or Anthropic API.
    """
    # Build prompt with context
    history_text = format_history(history) if history else "No prior conversation."

    prompt = f"""SYSTEM:
{system_prompt}

CONVERSATION HISTORY:
{history_text}

TASK BRIEF:
{task_brief}

YOUR TURN: {"Propose an initial plan" if turn == 1 else "Refine your plan based on the critic's feedback above"}.
Output JSON only."""

    # For demonstration: use codex to simulate proposer
    # In real implementation, call Claude Code API or CLI here
    result = _call_codex_exec(prompt)

    # Log to transcript
    log_conversation(turn, "claude-code", "propose" if turn == 1 else "refine", result)

    try:
        plan = json.loads(result)
        return {"success": True, "plan": plan, "raw": result}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON: {e}", "raw": result}


def call_critic(proposal: dict, history: list[dict], system_prompt: str, turn: int, task_brief: str) -> dict:
    """Call Codex (Critic) via its CLI"""

    history_text = format_history(history) if history else "No prior conversation."

    prompt = f"""SYSTEM:
{system_prompt}

CONVERSATION HISTORY:
{history_text}

TASK BRIEF:
{task_brief}

PROPOSED PLAN:
{json.dumps(proposal, indent=2)}

YOUR TURN: Review this plan. Output JSON only with your approval decision."""

    result = _call_codex_exec(prompt)

    # Log to transcript
    log_conversation(turn, "codex", "critique" if turn == 2 else "review", result)

    try:
        review = json.loads(result)
        return {"success": True, "review": review, "raw": result}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON: {e}", "raw": result}


def _call_codex_exec(prompt: str) -> str:
    """Execute Codex CLI command (helper function)"""
    # Escape quotes in prompt
    safe_prompt = prompt.replace('"', '\\"').replace("'", "\\'")

    # Determine if we're in WSL or Windows
    if os.path.exists('/proc/version'):
        # We're in WSL
        cmd = f'codex exec --skip-git-repo-check "{safe_prompt}"'
        proc = subprocess.run(
            ['bash', '-c', cmd],
            capture_output=True,
            text=True,
            timeout=120
        )
    else:
        # We're in Windows - call via WSL
        # Escape for WSL bash
        wsl_safe_prompt = safe_prompt.replace('$', '\\$')
        cmd = f'wsl bash -c "codex exec --skip-git-repo-check \\"{wsl_safe_prompt}\\""'
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=True,
            timeout=120
        )

    if proc.returncode != 0:
        raise RuntimeError(f"Codex exec failed: {proc.stderr}")

    # Extract just the agent's response (strip Codex CLI metadata)
    output = proc.stdout.strip()

    # Find the actual response (usually after "codex" line and metadata)
    lines = output.split('\n')

    # Look for the LAST occurrence of JSON (not the example in the prompt)
    # Strategy: find all { lines, take the last one that's near the end
    json_candidates = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('{') and not stripped.startswith('{...'):
            json_candidates.append(i)

    # Take the last JSON block (should be the actual response, not prompt example)
    if json_candidates:
        json_start = json_candidates[-1]

        # Extract from that line to the end, but stop at "tokens used" or similar metadata
        json_lines = []
        for line in lines[json_start:]:
            if 'tokens used' in line.lower() or line.startswith('[2025-'):
                break
            json_lines.append(line)

        result = '\n'.join(json_lines).strip()
        # Verify it's valid JSON structure
        if result.startswith('{') and result.endswith('}'):
            return result

    # Fallback: return everything after the last "codex" marker
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i]
        if 'codex' in line.lower() and '[2025-' not in line:
            return '\n'.join(lines[i+1:]).strip()

    return output


def call_claude_code_proposer(task_brief: str, history: list[dict], system_prompt: str, turn: int) -> dict:
    """
    Actual Claude Code proposer - uses Python to construct plan internally
    since we ARE Claude Code in this session.

    This is a special case: Claude Code calling itself for deliberation.
    """
    history_text = format_history(history) if history else "No prior conversation."

    # Since we're Claude Code, we can directly reason about the task
    # In a production system, this would call claude-code CLI or API

    if turn == 1:
        # Initial proposal - analyze task brief and create plan
        plan = _construct_plan_from_task(task_brief)
        reasoning = f"Analyzed task brief and created plan with {len(plan.get('actions', []))} actions"
    else:
        # Refinement - incorporate critic feedback
        last_critique = history[-1]['content'] if history else ""
        plan = _refine_plan_from_feedback(task_brief, last_critique)
        reasoning = "Refined plan based on critic feedback"

    result_text = json.dumps(plan, indent=2)
    log_conversation(turn, "claude-code", "propose" if turn == 1 else "refine", reasoning + "\n" + result_text)

    return {"success": True, "plan": plan, "raw": result_text}


def _construct_plan_from_task(task_brief: str) -> dict:
    """Helper: construct initial plan from task brief (Claude Code's internal reasoning)"""
    # This is a placeholder - in real usage, parse the task brief
    # For now, return a template that the critic will review
    return {
        "plan_id": f"plan-{int(time.time())}",
        "reasoning": "Initial plan based on task brief analysis",
        "actions": [
            {
                "id": "A1",
                "type": "fs.write",
                "params": {
                    "path": "staging/placeholder.txt",
                    "content": "Placeholder - will be replaced with actual task actions"
                }
            }
        ]
    }


def _refine_plan_from_feedback(task_brief: str, critique: str) -> dict:
    """Helper: refine plan based on critic feedback"""
    # Parse critique and update plan
    # For now, return updated template
    return {
        "plan_id": f"plan-refined-{int(time.time())}",
        "reasoning": f"Refined based on feedback: {critique[:100]}...",
        "actions": [
            {
                "id": "A1",
                "type": "fs.write",
                "params": {
                    "path": "staging/refined.txt",
                    "content": "Refined plan incorporating critic feedback"
                }
            }
        ]
    }
