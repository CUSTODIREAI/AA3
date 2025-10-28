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
    The response typically comes AFTER all the [2025-] timestamp lines and "codex" line.
    """
    lines = output.split('\n')

    # Find all "codex" lines (Codex outputs thinking summaries with codex markers)
    codex_markers = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == 'codex' or (stripped.startswith('codex') and '[2025-' not in line):
            codex_markers.append(i)

    # Start searching from after the LAST codex marker (the real response comes after all thinking)
    search_start = (codex_markers[-1] + 1) if codex_markers else 0

    # Find all potential JSON starts after the codex marker
    potential_starts = []
    for i in range(search_start, len(lines)):
        stripped = lines[i].strip()
        # Skip empty lines, timestamps, and metadata
        if not stripped or stripped.startswith('[2025-') or 'tokens used' in stripped.lower():
            continue
        if stripped.startswith('{'):
            potential_starts.append(i)

    # Try each potential start
    candidates = []
    for start_idx in potential_starts:
        brace_count = 0
        json_lines = []

        for i in range(start_idx, len(lines)):
            line = lines[i]

            # Stop at metadata/timestamp lines
            if ('tokens used' in line.lower() or line.startswith('[2025-')) and json_lines:
                break

            json_lines.append(line)
            brace_count += line.count('{') - line.count('}')

            # Found complete JSON
            if brace_count == 0 and len(json_lines) > 1:
                json_text = '\n'.join(json_lines)
                try:
                    parsed = json.loads(json_text)
                    # Prioritize JSONs with required fields
                    has_plan_id = 'plan_id' in parsed or 'approved' in parsed
                    score = len(json_text) + (1000 if has_plan_id else 0)
                    candidates.append((score, parsed, json_text))
                    break
                except json.JSONDecodeError:
                    continue

    # Return highest scoring candidate
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    # Last resort: try to extract any JSON-like structure
    import re
    # Look for JSON with "plan_id" or "approved" fields
    pattern = r'\{[^{}]*?"(?:plan_id|approved)"[^{}]*?\}'
    for match in re.finditer(pattern, output, re.DOTALL):
        # Try to expand to full object by counting braces
        start = match.start()
        brace_count = 0
        end = start
        for i in range(start, len(output)):
            if output[i] == '{':
                brace_count += 1
            elif output[i] == '}':
                brace_count -= 1
            if brace_count == 0:
                end = i + 1
                break

        try:
            json_text = output[start:end]
            return json.loads(json_text)
        except:
            continue

    # Save full output for debugging
    debug_file = Path('debug_codex_output.txt')
    debug_file.write_text(output, encoding='utf-8')

    raise ValueError(f"Could not extract valid JSON from Codex output. Full output saved to {debug_file}\n\nFirst 1000 chars:\n{output[:1000]}...")


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

    prompt = f"""You are a CRITIC reviewing a plan. DO NOT create a new plan - only review the existing one.

PLAN TO REVIEW:
{json.dumps(proposal, indent=2)}

REVIEW CRITERIA:
1. Files created in staging/ or workspace/
2. Plan ends with ingest.promote
3. Tags present in promotion items
4. No privileged docker
5. Actions will work correctly

YOUR OUTPUT MUST BE A REVIEW, NOT A PLAN.

Required JSON format (REVIEW structure, not plan structure):
{{
  "approved": true,
  "reasons": ["Meets all criteria", "Files in staging/", "Has ingest.promote with tags"],
  "plan": <copy the entire proposal here without changes if approved>
}}

OR if changes needed:
{{
  "approved": false,
  "reasons": ["Missing X", "Problem with Y"],
  "required_changes": ["Add X", "Fix Y"],
  "plan": <edited version of proposal>
}}

DO NOT return a plan with "plan_id" and "actions" - return a REVIEW with "approved" and "reasons".

Output review JSON now:"""

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
