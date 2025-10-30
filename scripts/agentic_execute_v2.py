#!/usr/bin/env python3
"""
Agentic Execution v2: Three-stage collaborative workflow

STAGE 1: Codex analyzes and diagnoses issues
STAGE 2: Claude Code agent applies fixes
STAGE 3: Codex reviews and proposes polish
"""
from __future__ import annotations
import sys, json, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestrator.cycle import execute_action
from src.gateway.policy import Policy
from src.agents.agent_wrapper import call_codex_cli, extract_json_from_codex_output, append_transcript

def ledger_log(event_type: str, **kwargs):
    """Log to reports/ledger.jsonl"""
    import time
    rec = {
        'ts': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        'event': event_type,
        **kwargs
    }
    append_transcript('reports/ledger.jsonl', rec)


def build_observation(action: dict, result: dict, action_idx: int) -> dict:
    """Build rich observation from execution result"""
    obs = {
        'action_index': action_idx,
        'action_type': action.get('type'),
        'action_id': action.get('id'),
        'success': result.get('ok', False),
    }

    # Include relevant result fields
    if 'returncode' in result:
        obs['returncode'] = result['returncode']
    if 'stdout' in result:
        stdout_text = result['stdout'][:1000]  # First 1000 chars
        obs['stdout_preview'] = stdout_text

        # Parse output files if mentioned
        if 'Wrote:' in result['stdout'] or 'written' in result['stdout'].lower():
            obs['output_files'] = {}
            for line in result['stdout'].splitlines():
                for word in line.split():
                    if word.startswith('staging/') or word.startswith('workspace/'):
                        fpath = Path(word.rstrip(',.;:'))
                        if fpath.exists():
                            try:
                                if fpath.suffix == '.json':
                                    data = json.loads(fpath.read_text(encoding='utf-8'))
                                    obs['output_files'][str(fpath)] = {
                                        'type': 'json',
                                        'keys': list(data.keys()) if isinstance(data, dict) else [],
                                        'preview': str(data)[:300]
                                    }
                                elif fpath.suffix == '.jsonl':
                                    lines = fpath.read_text(encoding='utf-8').splitlines()
                                    obs['output_files'][str(fpath)] = {
                                        'type': 'jsonl',
                                        'line_count': len(lines),
                                        'first_line': lines[0] if lines else ''
                                    }
                            except:
                                pass

    if 'stderr' in result and result['stderr']:
        obs['stderr_preview'] = result['stderr'][:500]
    if 'error' in result:
        obs['error'] = result['error']

    return obs


def check_output_quality(action: dict, result: dict, task: str) -> dict:
    """Assess quality of execution output"""
    if not result.get('ok'):
        return {'quality': 'bad', 'issues': [result.get('error', 'Action failed')]}

    stdout = result.get('stdout', '')

    # Check for suspicious patterns
    issues = []
    if 'suitable_real_count: 0' in stdout or 'suitable_real_count": 0' in stdout:
        issues.append("Found 0 suitable videos - may indicate metadata parsing failure")
    if 'No suitable' in stdout:
        issues.append("No suitable items found - verify input data")
    if 'WARNING' in stdout or 'ERROR' in stdout:
        issues.append("Warnings or errors in output")

    # CRITICAL: Check output files for suspicious data
    # If script wrote report.json, examine its contents
    if 'staging/dataset_analysis/report.json' in stdout:
        report_path = Path('staging/dataset_analysis/report.json')
        if report_path.exists():
            try:
                report_data = json.loads(report_path.read_text(encoding='utf-8'))
                suitable_count = report_data.get('suitable_real_count', -1)
                total_real = report_data.get('total_real', 0)

                # If found real videos but 0 suitable, likely a parsing issue
                if total_real > 0 and suitable_count == 0:
                    issues.append(f"Found {total_real} real videos but 0 suitable (≥10s, ≥720p) - likely metadata parsing failure")
            except:
                pass

    if issues:
        return {'quality': 'suspicious', 'issues': issues}

    return {'quality': 'good', 'issues': []}


# ===== STAGE 1: Codex Diagnosis =====
def call_codex_diagnose(
    action_index: int,
    current_action: dict,
    observation: dict,
    quality_check: dict,
    execution_history: list
) -> dict:
    """
    STAGE 1: Codex analyzes the issue and provides diagnosis.

    Returns:
    - {'needs_fix': False, 'reason': '...'} - continue
    - {'needs_fix': True, 'diagnosis': '...', 'fix_instructions': '...'} - needs fixing
    - {'abort': True, 'reason': '...'} - fatal error
    """
    # Gather context
    history_summary = []
    for entry in execution_history[-5:]:
        act = entry['action']
        res = entry['result']
        history_summary.append({
            'action_id': act.get('id'),
            'type': act.get('type'),
            'success': res.get('ok', False)
        })

    # Get script code if executing Python (truncate if too large)
    script_context = ""
    if current_action.get('type') == 'exec.container_cmd':
        cmd = current_action['params'].get('cmd', '')
        if 'python' in cmd and 'workspace/' in cmd:
            for word in cmd.split():
                if word.startswith('workspace/') and word.endswith('.py'):
                    script_path = Path(word)
                    if script_path.exists():
                        try:
                            script_code = script_path.read_text(encoding='utf-8')
                            # Truncate if too large (keep first 3000 chars)
                            if len(script_code) > 3000:
                                script_context = f"\nSCRIPT CODE ({script_path}) - TRUNCATED:\n```python\n{script_code[:3000]}\n...\n[{len(script_code) - 3000} more chars]\n```\n"
                            else:
                                script_context = f"\nSCRIPT CODE ({script_path}):\n```python\n{script_code}\n```\n"
                        except:
                            pass
                    break

    # Filesystem investigation
    investigation = ""
    if quality_check.get('quality') == 'suspicious':
        investigation = "\nFILESYSTEM INVESTIGATION:\n"
        try:
            import subprocess
            check = subprocess.run(
                ['bash', '-c', 'ls /mnt/x/dataset2/easylanguages/*.json 2>/dev/null | head -3'],
                capture_output=True, text=True, timeout=5
            )
            if check.stdout:
                investigation += f"Metadata files found:\n{check.stdout}\n"
                first_file = check.stdout.splitlines()[0]
                if first_file:
                    try:
                        sample = Path(first_file).read_text(encoding='utf-8')[:400]
                        investigation += f"\nSample file content:\n{sample}\n"
                    except:
                        pass
        except:
            investigation += "(Investigation failed)\n"

    # Build concise action summary (avoid huge JSON dumps)
    action_summary = {
        'type': current_action.get('type'),
        'id': current_action.get('id')
    }
    if current_action.get('type') == 'exec.container_cmd':
        action_summary['command'] = current_action.get('params', {}).get('cmd', '')
    elif current_action.get('type') == 'fs.write':
        action_summary['path'] = current_action.get('params', {}).get('path', '')
        action_summary['content_size'] = len(current_action.get('params', {}).get('content', ''))

    prompt = f"""You are Codex, the diagnostic agent. Your job is to ANALYZE code issues, NOT to fix them.

CURRENT ACTION (index {action_index}):
{json.dumps(action_summary, indent=2)}

EXECUTION RESULT:
Success: {observation.get('success')}
Return Code: {observation.get('returncode', 'N/A')}
Output Preview: {observation.get('stdout_preview', '')[:500]}
Error: {observation.get('error', 'None')}

QUALITY ASSESSMENT:
Quality: {quality_check.get('quality')}
Issues: {quality_check.get('issues', [])}

RECENT HISTORY:
{json.dumps(history_summary, indent=2)}
{script_context}
{investigation}

YOUR TASK: Analyze whether this needs fixing.

If action succeeded and quality is good:
{{
  "needs_fix": false,
  "reason": "Output is acceptable, continue to next action"
}}

If there's an issue that can be fixed:
{{
  "needs_fix": true,
  "diagnosis": "Detailed analysis of what's wrong (e.g., 'Script only checks *.json but metadata files are named *.info.json')",
  "fix_instructions": "Clear instructions for Claude Code agent on what to change (e.g., 'In find_sidecar_json function, add check for .info.json extension after line 45')",
  "affected_files": ["workspace/analyze_datasets.py"]
}}

If fatal error:
{{
  "abort": true,
  "reason": "Why this cannot be recovered"
}}

CRITICAL: You are ONLY diagnosing. Do NOT write code. Just analyze and instruct.

Output JSON only:
"""

    try:
        # Increased timeout for diagnosis (large datasets take time to analyze)
        output = call_codex_cli(prompt, timeout=300)
        diagnosis = extract_json_from_codex_output(output)
        return diagnosis
    except Exception as e:
        ledger_log('codex_diagnosis_error', error=str(e))
        return {'needs_fix': False, 'reason': f'Diagnosis failed: {e}'}


# ===== STAGE 2: Claude Code Fixes =====
def call_claude_fix(diagnosis: dict, affected_files: list) -> dict:
    """
    STAGE 2: Claude Code agent applies fixes based on Codex's diagnosis.

    Returns:
    - {'applied': True, 'changes': [...]} - fixes applied
    - {'applied': False, 'reason': '...'} - could not fix
    """
    from src.agents.agent_wrapper import call_codex_cli, extract_json_from_codex_output

    fix_instructions = diagnosis.get('fix_instructions', '')
    files_to_fix = diagnosis.get('affected_files', affected_files)

    # Read affected files
    file_contents = {}
    for fpath in files_to_fix:
        p = Path(fpath)
        if p.exists():
            try:
                file_contents[fpath] = p.read_text(encoding='utf-8')
            except:
                pass

    if not file_contents:
        return {'applied': False, 'reason': 'No files to fix'}

    prompt = f"""You are Claude Code, the implementation agent. Apply fixes based on the diagnosis.

DIAGNOSIS FROM CODEX:
{diagnosis.get('diagnosis', 'No diagnosis')}

FIX INSTRUCTIONS:
{fix_instructions}

AFFECTED FILES:
{json.dumps({k: f"{len(v)} chars, {len(v.splitlines())} lines" for k, v in file_contents.items()}, indent=2)}

FILE CONTENTS:
"""
    for fpath, content in file_contents.items():
        prompt += f"\n{'='*60}\nFILE: {fpath}\n{'='*60}\n{content}\n"

    prompt += f"""
YOUR TASK: Apply the fixes as instructed. Return the COMPLETE fixed file contents.

Output format:
{{
  "fixes_applied": [
    {{
      "file": "workspace/analyze_datasets.py",
      "changes_description": "Added .info.json support in find_sidecar_json",
      "new_content": "<COMPLETE FILE CONTENT WITH FIXES>"
    }}
  ]
}}

CRITICAL:
- Provide COMPLETE file contents, not just the changed parts
- Make MINIMAL changes (only what's needed to fix the issue)
- Preserve all existing functionality

Output JSON only:
"""

    try:
        # Increased timeout for Claude Code fixes (may need to rewrite large files)
        output = call_codex_cli(prompt, timeout=300)
        fix_result = extract_json_from_codex_output(output)

        # Apply the fixes by writing files
        changes = []
        for fix in fix_result.get('fixes_applied', []):
            file_path = Path(fix['file'])
            new_content = fix['new_content']

            try:
                file_path.write_text(new_content, encoding='utf-8')
                changes.append({
                    'file': str(file_path),
                    'description': fix.get('changes_description', 'Applied fix')
                })
                ledger_log('claude_applied_fix', file=str(file_path), desc=fix.get('changes_description'))
            except Exception as e:
                ledger_log('claude_fix_failed', file=str(file_path), error=str(e))

        return {'applied': True, 'changes': changes}

    except Exception as e:
        ledger_log('claude_fix_error', error=str(e))
        return {'applied': False, 'reason': f'Fix application failed: {e}'}


# ===== STAGE 3: Codex Review =====
def call_codex_review(changes: list, affected_files: list) -> dict:
    """
    STAGE 3: Codex reviews Claude's changes and suggests polish (optional).

    Returns:
    - {'approved': True, 'notes': '...'} - changes look good
    - {'approved': True, 'polish_suggestions': '...', 'notes': '...'} - good but could be better
    - {'approved': False, 'issues': '...'} - changes have problems
    """
    # Read the changed files
    file_contents = {}
    for change in changes:
        fpath = Path(change['file'])
        if fpath.exists():
            try:
                file_contents[str(fpath)] = fpath.read_text(encoding='utf-8')
            except:
                pass

    prompt = f"""You are Codex, reviewing changes made by Claude Code.

CHANGES APPLIED:
{json.dumps(changes, indent=2)}

UPDATED FILE CONTENTS:
"""
    for fpath, content in file_contents.items():
        prompt += f"\n{'='*60}\nFILE: {fpath}\n{'='*60}\n{content[:2000]}\n...\n"

    prompt += """
YOUR TASK: Review the changes for correctness.

If changes look good:
{
  "approved": true,
  "notes": "Changes correctly address the issue"
}

If changes look good but could be improved:
{
  "approved": true,
  "notes": "Changes are correct",
  "polish_suggestions": "Optional: Could add error handling on line X, or optimize Y"
}

If changes have issues:
{
  "approved": false,
  "issues": "Detailed description of problems"
}

Output JSON only:
"""

    try:
        # Increased timeout for review
        output = call_codex_cli(prompt, timeout=180)
        review = extract_json_from_codex_output(output)
        return review
    except Exception as e:
        ledger_log('codex_review_error', error=str(e))
        return {'approved': True, 'notes': f'Review failed, assuming ok: {e}'}


# ===== Main Execution Loop =====
def agentic_execute_v2(approved_plan: dict, original_task: str = '') -> dict:
    """
    Execute plan with three-stage collaborative adaptation:
    1. Codex diagnoses issues
    2. Claude Code applies fixes
    3. Codex reviews changes
    """
    policy = Policy()
    plan_id = approved_plan.get('plan_id', 'unknown')
    actions = approved_plan.get('actions', [])

    ledger_log('agentic_execution_v2_start', plan_id=plan_id, total_actions=len(actions))

    execution_history = []
    adaptation_count = 0
    max_adaptations = 3 * len(actions)

    action_idx = 0
    while action_idx < len(actions):
        current_action = actions[action_idx]
        action_id = current_action.get('id', f'A{action_idx}')

        ledger_log('action_start', action_index=action_idx, action_id=action_id)

        # Execute action through gateway
        result = execute_action(current_action, policy, plan_id)

        execution_history.append({
            'action_index': action_idx,
            'action': current_action,
            'result': result
        })

        # Build observation
        observation = build_observation(current_action, result, action_idx)
        quality_check = check_output_quality(current_action, result, original_task)

        # If action failed or quality suspicious, start three-stage collaboration
        if not result.get('ok') or quality_check.get('quality') in ['suspicious', 'bad']:
            ledger_log('quality_issue', action_id=action_id, quality=quality_check.get('quality'))

            # === STAGE 1: Codex Diagnosis ===
            ledger_log('stage_1_codex_diagnosis', action_id=action_id)
            diagnosis = call_codex_diagnose(action_idx, current_action, observation, quality_check, execution_history)

            if diagnosis.get('abort'):
                ledger_log('codex_abort', reason=diagnosis.get('reason'))
                return {
                    'ok': False,
                    'reason': f"Codex aborted: {diagnosis.get('reason')}",
                    'executed': execution_history,
                    'adaptations': adaptation_count
                }

            if not diagnosis.get('needs_fix'):
                ledger_log('codex_approve_continue', reason=diagnosis.get('reason'))
                action_idx += 1
                continue

            # === STAGE 2: Claude Code Applies Fixes ===
            ledger_log('stage_2_claude_fixing', diagnosis=diagnosis.get('diagnosis'))
            affected_files = diagnosis.get('affected_files', [])
            fix_result = call_claude_fix(diagnosis, affected_files)

            if not fix_result.get('applied'):
                ledger_log('claude_fix_failed', reason=fix_result.get('reason'))
                action_idx += 1
                continue

            changes = fix_result.get('changes', [])
            adaptation_count += 1

            # === STAGE 3: Codex Review ===
            ledger_log('stage_3_codex_review', changes=changes)
            review = call_codex_review(changes, affected_files)

            if not review.get('approved'):
                ledger_log('codex_rejected_changes', issues=review.get('issues'))
                return {
                    'ok': False,
                    'reason': f"Codex rejected changes: {review.get('issues')}",
                    'executed': execution_history,
                    'adaptations': adaptation_count
                }

            ledger_log('codex_approved_changes', notes=review.get('notes'),
                      polish=review.get('polish_suggestions', ''))

            # Check adaptation limit
            if adaptation_count >= max_adaptations:
                ledger_log('max_adaptations_reached', count=adaptation_count)
                return {
                    'ok': False,
                    'reason': 'Max adaptations reached',
                    'executed': execution_history,
                    'adaptations': adaptation_count
                }

            # Retry the action with fixes applied
            # (Don't increment action_idx - will retry same action)
            continue

        # Action succeeded with good quality
        action_idx += 1

    # All actions completed
    ledger_log('agentic_execution_v2_complete', adaptations=adaptation_count, total_actions=len(actions))

    return {
        'ok': True,
        'executed': execution_history,
        'adaptations': adaptation_count
    }


if __name__ == '__main__':
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', required=True, help='Path to reviewed_plan.json')
    ap.add_argument('--task', required=False, default='', help='Path to original task file')
    args = ap.parse_args()

    plan_data = json.loads(Path(args.plan).read_text(encoding='utf-8'))

    # Handle reviewed_plan structure (has 'plan' nested inside)
    if 'plan' in plan_data and 'approved' in plan_data:
        plan = plan_data['plan']
    else:
        plan = plan_data

    task_text = Path(args.task).read_text(encoding='utf-8') if args.task and Path(args.task).exists() else ''

    result = agentic_execute_v2(plan, task_text)

    # Save report
    report_path = Path('reports/agentic_execution_v2.json')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, indent=2), encoding='utf-8')

    print(f"Agentic execution v2 {'SUCCESS' if result['ok'] else 'FAILED'}")
    print(f"Adaptations: {result['adaptations']}")
    print(f"Report: {report_path}")

    sys.exit(0 if result['ok'] else 1)
