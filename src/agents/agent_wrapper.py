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
                    # Prioritize JSONs with required fields (plan, review, or decision structures)
                    has_key_field = 'plan_id' in parsed or 'approved' in parsed or 'decision' in parsed
                    # Give higher score to longer JSONs with key fields
                    score = len(json_text) + (1000 if has_key_field else 0)
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
    # Look for JSON with key fields (plan_id, approved, or decision)
    pattern = r'\{[^{}]*?"(?:plan_id|approved|decision)"[^{}]*?\}'
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

    # Final fallback: try to find ANY valid JSON object in the output
    # This catches cases where JSON is embedded in text
    for i in range(len(output)):
        if output[i] == '{':
            brace_count = 0
            for j in range(i, len(output)):
                if output[j] == '{':
                    brace_count += 1
                elif output[j] == '}':
                    brace_count -= 1
                if brace_count == 0:
                    try:
                        candidate = output[i:j+1]
                        parsed = json.loads(candidate)
                        # Accept any valid JSON object
                        if isinstance(parsed, dict) and len(parsed) > 0:
                            return parsed
                    except:
                        continue
                    break

    # Save full output for debugging
    debug_file = Path('debug_codex_output.txt')
    debug_file.write_text(output, encoding='utf-8')

    raise ValueError(f"Could not extract valid JSON from Codex output. Full output saved to {debug_file}\n\nFirst 1000 chars:\n{output[:1000]}...")


# ---- Codex CLI invocation ----
def call_codex_cli(prompt: str, timeout: int = 300) -> str:
    """Call Codex CLI and return raw output

    Uses stdin pipe for simplicity and reliability.
    """
    # Check if we're in WSL or Windows
    in_wsl = os.path.exists('/proc/version')

    if in_wsl:
        # Direct codex call in WSL with stdin
        cmd = ['codex', 'exec', '--skip-git-repo-check', '-']
        proc = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path.cwd()
        )
    else:
        # Call via WSL from Windows with stdin
        cmd = ['wsl', 'bash', '-c', 'cd /mnt/x/data_from_helper/custodire-aa-system && codex exec --skip-git-repo-check -']
        proc = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout
        )

    if proc.returncode != 0:
        raise RuntimeError(f"Codex CLI failed:\nSTDERR: {proc.stderr}\nSTDOUT: {proc.stdout}")

    return proc.stdout


# ---- Plan linter for passthrough adoption ----
def lint_plan_for_passthrough(plan: dict, task_text: str) -> tuple[bool, list[str]]:
    """
    Check if plan uses passthrough appropriately for task requirements.

    Returns:
        (is_valid, [rejection_reasons])
    """
    issues = []
    actions = plan.get('actions', [])
    action_types = [a.get('type') for a in actions]

    # Count action types
    fs_write_count = action_types.count('fs.write')
    passthrough_count = action_types.count('agent.passthrough_shell')

    text_lower = task_text.lower()

    # Check web/versions requirement
    if re.search(r'\b(web|latest|version|current|fetch)\b', text_lower):
        if passthrough_count == 0:
            issues.append("Task requires web lookups for latest versions, but plan has zero agent.passthrough_shell actions. Must use curl/wget to fetch current data.")

    # Check docker/build requirement
    if re.search(r'\b(docker|build|image)\b', text_lower):
        # Check if writing build scripts without executing
        build_scripts = [a for a in actions if a.get('type') == 'fs.write' and 'docker build' in str(a.get('params', {}).get('content', ''))]
        if build_scripts and passthrough_count == 0:
            issues.append("Task requires docker builds, but plan only writes build scripts without executing them. Must use agent.passthrough_shell to run docker build.")

    # Check GPU/test requirement
    if re.search(r'\b(gpu|cuda|test|verify)\b', text_lower):
        test_scripts = [a for a in actions if a.get('type') == 'fs.write' and any(kw in str(a.get('params', {})) for kw in ['nvidia-smi', 'GPU', 'cuda'])]
        if test_scripts and passthrough_count == 0:
            issues.append("Task requires GPU testing, but plan only writes test scripts without executing them. Must use agent.passthrough_shell to run tests.")

    return (len(issues) == 0, issues)


# ---- Agent implementations ----
def call_proposer(task_brief: str, history: list[dict], tools_context: str = None) -> dict:
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

    # Build system prompt - SIMPLIFIED to avoid timeout
    tools_section = tools_context if tools_context else "Tools: fs.write, agent.passthrough_shell, ingest.promote"

    prompt = f"""Create a plan (JSON only, no markdown).

Task: {task_brief[:300]}

History: {history_text[:200]}

Format:
{{"plan_id": "unique-id", "actions": [{{"id": "A1", "type": "...", "params": {{...}}}}]}}

Rules:
- Files in staging/ or workspace/ only
- Use agent.passthrough_shell for web/docker/GPU commands (execute, don't just write scripts)
- End with ingest.promote (include tags)

JSON:"""

    # Call Codex
    output = call_codex_cli(prompt)

    # Extract JSON
    plan = extract_json_from_codex_output(output)

    # Validate basic structure
    if 'actions' not in plan:
        raise ValueError(f"Invalid plan structure: missing 'actions' field. Plan: {plan}")

    return plan


def call_critic(proposal: dict, history: list[dict], tools_context: str = None, task_text: str = None) -> dict:
    """
    Critic agent: Reviews proposal and approves or requests changes.

    Uses Codex CLI with plan linter and enforcement rules.
    """
    # Apply linter BEFORE calling critic to catch write-only anti-patterns
    is_valid, lint_issues = lint_plan_for_passthrough(proposal, task_text or "")
    if not is_valid:
        # Auto-reject without calling critic
        return {
            "approved": False,
            "reasons": lint_issues,
            "plan": proposal
        }

    # Task context (limited to 200 chars to avoid bloat)
    task_context = task_text[:200] if task_text else ""

    # SIMPLIFIED prompt to avoid timeout
    prompt = f"""Review this plan (return JSON only).

Task: {task_context}

Plan:
{json.dumps(proposal, indent=2)[:1500]}

Check:
1. Files in staging/ or workspace/
2. Ends with ingest.promote (with tags)
3. If task needs web/docker/GPU: must use agent.passthrough_shell (not just write scripts)

Format:
{{"approved": true/false, "reasons": [...], "plan": <proposal>}}

JSON:"""

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
