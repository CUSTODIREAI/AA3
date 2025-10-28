"""Agent wrapper for Claude Code and Codex CLI

Implements call_proposer and call_critic for multi-agent deliberation.
"""
from __future__ import annotations
from pathlib import Path
import json, time, subprocess, re, os

# ---- Transcript utilities ----
def _ts():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def append_transcript(path: str|Path, rec: dict):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# ---- File helpers ----
def read_text(path: str|Path) -> str:
    return Path(path).read_text(encoding="utf-8")

def save_json(path: str|Path, obj: dict):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


# ---- JSON extraction from Codex output ----
def extract_json_from_codex_output(output: str) -> dict:
    """
    Extract valid JSON from Codex CLI output.

    Codex outputs include metadata, thinking blocks, and the actual JSON response.
    We need to find the largest valid JSON object in the output.
    """
    # Strategy: find all potential JSON blocks and validate them
    lines = output.split('\n')

    # Find all lines that start with '{'
    potential_starts = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('{') and len(stripped) > 5:  # Not just "{"
            potential_starts.append(i)

    # Try each potential start, looking for complete JSON
    candidates = []
    for start_idx in potential_starts:
        # Try to find matching closing brace
        brace_count = 0
        json_lines = []

        for i in range(start_idx, len(lines)):
            line = lines[i]

            # Stop at metadata lines
            if 'tokens used' in line.lower() or line.startswith('[2025-'):
                break

            json_lines.append(line)

            # Count braces to find complete JSON
            brace_count += line.count('{') - line.count('}')

            if brace_count == 0 and len(json_lines) > 1:
                # Potentially complete JSON
                json_text = '\n'.join(json_lines)
                try:
                    parsed = json.loads(json_text)
                    candidates.append((len(json_text), parsed, json_text))
                    break  # Found valid JSON from this start point
                except json.JSONDecodeError:
                    continue

    # Return the largest valid JSON (most likely to be the actual response)
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]  # Return parsed dict

    # Fallback: try to find JSON by looking for specific patterns
    # Look for plan_id or reasoning fields
    json_pattern = r'\{[^{}]*"plan_id"[^{}]*\}'
    matches = re.finditer(json_pattern, output, re.DOTALL)
    for match in matches:
        try:
            # Try to expand to full JSON
            start = match.start()
            end = output.find('\n[2025-', start)  # Stop at timestamp
            if end == -1:
                end = output.find('\ntokens used', start)
            if end == -1:
                end = len(output)

            json_text = output[start:end].strip()
            return json.loads(json_text)
        except:
            continue

    raise ValueError(f"Could not extract valid JSON from Codex output. Output:\n{output[:500]}...")


# ---- Codex CLI invocation ----
def call_codex_cli(prompt: str, timeout: int = 180) -> str:
    """Call Codex CLI and return raw output"""

    # Check if we're in WSL or Windows
    in_wsl = os.path.exists('/proc/version')

    if in_wsl:
        # Direct codex call in WSL
        cmd = ['codex', 'exec', '--skip-git-repo-check', prompt]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
    else:
        # Call via WSL from Windows
        # Use a file to pass the prompt to avoid quoting issues
        prompt_file = Path('temp_prompt.txt')
        prompt_file.write_text(prompt, encoding='utf-8')

        cmd = f'wsl bash -c "cd /mnt/x/data_from_helper/custodire-aa-system && codex exec --skip-git-repo-check \\"$(cat temp_prompt.txt)\\""'
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=True,
            timeout=timeout
        )

        # Cleanup
        if prompt_file.exists():
            prompt_file.unlink()

    if proc.returncode != 0:
        raise RuntimeError(f"Codex CLI failed:\nSTDERR: {proc.stderr}\nSTDOUT: {proc.stdout}")

    return proc.stdout


# ---- Agent implementations ----
def call_proposer(task_brief: str, history: list[dict]) -> dict:
    """
    Proposer agent: Creates initial plan or refines based on critic feedback.

    For this implementation, we use Codex to simulate the proposer.
    In production, this would call Claude Code API/CLI.
    """
    # Build prompt based on history
    if not history or all(h.get('phase') != 'propose' for h in history):
        phase = "initial proposal"
        history_text = "This is your first turn."
    else:
        phase = "refinement"
        # Get last critique
        last_review = next((h for h in reversed(history) if h.get('phase') == 'critique'), None)
        if last_review:
            review_data = last_review.get('review', {})
            history_text = f"Previous critique:\nApproved: {review_data.get('approved')}\nReasons: {review_data.get('reasons')}\nRequired changes: {review_data.get('required_changes', [])}"
        else:
            history_text = "No critique found in history."

    prompt = f"""You are a Proposer agent creating a plan for dataset curation.

TASK:
{task_brief}

HISTORY:
{history_text}

PHASE: {phase}

OUTPUT REQUIREMENTS:
Return ONLY valid JSON (no markdown, no explanations) with this structure:
{{
  "plan_id": "unique-id-string",
  "reasoning": "Brief explanation of approach",
  "actions": [
    {{"id": "A1", "type": "fs.write", "params": {{"path": "...", "content": "..."}}}},
    {{"id": "A2", "type": "ingest.promote", "items": [{{"src": "...", "relative_dst": "...", "tags": {{...}}}}]}}
  ]
}}

Available tools: fs.write, fs.append, fs.move, git.clone, download.ytdlp, container.run, exec.container_cmd, ingest.promote

Rules:
- Files must be created in staging/ or workspace/ first
- Use ingest.promote to move to dataset/ (append-only)
- Include tags in promotion items
- plan_id must be unique

Output JSON now:"""

    # Call Codex
    output = call_codex_cli(prompt)

    # Extract JSON
    plan = extract_json_from_codex_output(output)

    # Validate basic structure
    if 'actions' not in plan:
        raise ValueError(f"Invalid plan structure: missing 'actions' field. Plan: {plan}")

    return plan


def call_critic(proposal: dict, history: list[dict]) -> dict:
    """
    Critic agent: Reviews proposal and approves or requests changes.

    Uses Codex CLI.
    """
    history_summary = f"This is critique turn {len([h for h in history if h.get('phase') == 'critique']) + 1}"

    prompt = f"""You are a Critic agent reviewing a dataset curation plan.

PROPOSAL:
{json.dumps(proposal, indent=2)}

HISTORY:
{history_summary}

YOUR TASK:
Review the proposal against these criteria:
1. Files are created in staging/ or workspace/ (writable roots)
2. Plan ends with ingest.promote action
3. Promotion items include tags
4. No privileged docker flags
5. Actions are valid and will work

OUTPUT REQUIREMENTS:
Return ONLY valid JSON (no markdown, no explanations):
{{
  "approved": true/false,
  "reasons": ["reason 1", "reason 2", ...],
  "required_changes": ["change 1", ...],  // only if not approved
  "plan": {{...}}  // final plan (same as proposal if approved, or edited version)
}}

If approved=true, plan will execute immediately.
If approved=false, proposer will refine.

Output JSON now:"""

    # Call Codex
    output = call_codex_cli(prompt)

    # Extract JSON
    review = extract_json_from_codex_output(output)

    # Validate structure
    if 'approved' not in review:
        raise ValueError(f"Invalid review structure: missing 'approved' field. Review: {review}")

    # Ensure plan is included
    if 'plan' not in review:
        review['plan'] = proposal  # Use original if not provided

    return review
