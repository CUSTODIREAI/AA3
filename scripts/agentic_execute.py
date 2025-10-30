#!/usr/bin/env python3
"""
Agentic Execution: Agents observe intermediate results and adapt their plans.

Safety guarantees preserved:
- All actions go through gateway policy enforcement
- No new tools/capabilities added (no delete)
- Protected roots remain read-only
- All actions logged to ledger
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestrator.cycle import execute_action, log as ledger_log
from src.gateway.policy import Policy
from src.agents.agent_wrapper import call_codex_cli, extract_json_from_codex_output


def build_observation(action: dict, result: dict, action_idx: int) -> dict:
    """
    Build observation for agent to analyze execution results.

    Safety: Only shows data from writable roots (workspace/, staging/)
    """
    obs = {
        'action_index': action_idx,
        'action_type': action.get('type'),
        'action_id': action.get('id'),
        'success': result.get('ok', False),
    }

    # Type-specific observations
    if action['type'] == 'fs.write':
        path = Path(action['params']['path'])
        obs['path'] = str(path)
        if path.exists():
            obs['file_created'] = True
            obs['file_size_bytes'] = path.stat().st_size
            # For Python scripts, show relevant functions
            if path.suffix == '.py':
                try:
                    content = path.read_text(encoding='utf-8')
                    obs['file_type'] = 'python_script'
                    obs['total_lines'] = len(content.splitlines())
                    # Show key functions (not full content, too large)
                    obs['key_functions'] = []
                    for match in re.finditer(r'^def (\w+)', content, re.MULTILINE):
                        obs['key_functions'].append(match.group(1))
                except:
                    obs['content_preview'] = '<unreadable>'
            else:
                try:
                    content = path.read_text(encoding='utf-8')
                    obs['content_preview'] = content[:500]
                except:
                    obs['content_preview'] = '<binary or unreadable>'
        else:
            obs['file_created'] = False

    elif action['type'] == 'exec.container_cmd':
        obs['command'] = action['params'].get('cmd')
        obs['returncode'] = result.get('returncode')
        obs['stdout_preview'] = result.get('stdout', '')[:2000]
        obs['stderr_preview'] = result.get('stderr', '')[:2000]
        obs['stdout_lines'] = result.get('stdout_lines', 0)

        # Parse output files from stdout
        stdout_text = result.get('stdout', '')
        if 'Wrote:' in stdout_text or 'written' in stdout_text.lower():
            obs['output_files'] = {}
            # Extract file paths from stdout
            for line in stdout_text.split('\n')[:20]:
                for word in line.split():
                    if word.startswith('staging/') or word.startswith('workspace/'):
                        fpath = Path(word.rstrip(',.;:'))
                        if fpath.exists():
                            try:
                                # Read key metrics from output files
                                if fpath.suffix == '.json':
                                    data = json.loads(fpath.read_text(encoding='utf-8'))
                                    obs['output_files'][str(fpath)] = {
                                        'type': 'json',
                                        'keys': list(data.keys()) if isinstance(data, dict) else [],
                                        'sample': {k: data[k] for k in list(data.keys())[:5]} if isinstance(data, dict) else {}
                                    }
                                elif fpath.suffix == '.jsonl':
                                    lines = fpath.read_text(encoding='utf-8').splitlines()
                                    obs['output_files'][str(fpath)] = {
                                        'type': 'jsonl',
                                        'line_count': len(lines),
                                        'first_line_sample': json.loads(lines[0]) if lines else {}
                                    }
                            except:
                                obs['output_files'][str(fpath)] = {'type': 'file', 'exists': True}

    elif action['type'] == 'ingest.promote':
        obs['items_count'] = len(action.get('items', []))
        obs['results'] = result.get('results', [])

    # Add error info if failed
    if not result.get('ok', False):
        obs['error'] = result.get('error', 'unknown error')

    return obs


def check_output_quality(action: dict, result: dict, original_task: str) -> dict:
    """
    Use AI to check if execution results meet expectations.

    Returns: {'quality': 'good'|'suspicious'|'bad', 'issues': [...], 'suggestions': [...]}
    """
    # For exec.container_cmd that generates analysis reports
    if action['type'] == 'exec.container_cmd' and 'analyze' in action['params'].get('cmd', '').lower():
        stdout = result.get('stdout', '')

        # Check if output files were mentioned
        output_files = []
        for line in stdout.split('\n'):
            if 'staging/' in line:
                # Extract potential file paths
                for word in line.split():
                    if word.startswith('staging/') and ('json' in word or 'jsonl' in word or 'md' in word):
                        output_files.append(word.rstrip(',.;:'))

        # Check those files exist and have reasonable content
        issues = []
        for fpath in output_files:
            p = Path(fpath)
            if not p.exists():
                issues.append(f"Output file mentioned but not found: {fpath}")
            elif p.stat().st_size == 0:
                issues.append(f"Output file is empty: {fpath}")
            elif p.suffix == '.json':
                try:
                    data = json.loads(p.read_text(encoding='utf-8'))
                    # Check for suspicious patterns
                    if isinstance(data, dict):
                        # Check if report has 0 or null for critical counts
                        for key in ['suitable_real_count', 'total_real', 'selected']:
                            val = data.get(key)
                            if key in data and (val == 0 or val == [] or (isinstance(val, dict) and not val)):
                                # This might be suspicious depending on context
                                if 'total_videos' in data and data['total_videos'] > 1000:
                                    issues.append(f"Suspicious: {key}={val} despite {data['total_videos']} total videos scanned")
                except Exception as e:
                    issues.append(f"Could not parse JSON in {fpath}: {e}")

        if issues:
            return {
                'quality': 'suspicious',
                'issues': issues,
                'suggestions': [
                    "Check if data extraction logic is working correctly",
                    "Verify file parsing (e.g., .info.json vs .json naming)",
                    "Consider using additional metadata sources (ffprobe, mediainfo)"
                ]
            }
        else:
            return {'quality': 'good', 'issues': [], 'suggestions': []}

    # Default: assume ok if action succeeded
    if result.get('ok'):
        return {'quality': 'good', 'issues': [], 'suggestions': []}
    else:
        return {
            'quality': 'bad',
            'issues': [result.get('error', 'Action failed')],
            'suggestions': ['Check error message and retry with fixes']
        }


def call_agent_observe_and_adapt(
    original_plan: dict,
    action_index: int,
    current_action: dict,
    observation: dict,
    quality_check: dict,
    execution_history: list
) -> dict:
    """
    Call agent (via Codex) to observe execution and propose adaptation.

    Agent can only propose actions from the same allowlist - no new powers!
    """

    # Build context from recent execution history
    history_summary = []
    for i, entry in enumerate(execution_history[-5:]):  # Last 5 actions
        act = entry['action']
        res = entry['result']
        history_summary.append({
            'index': i,
            'action_id': act.get('id'),
            'action_type': act.get('type'),
            'success': res.get('ok', False),
            'summary': f"{act.get('type')} -> {'ok' if res.get('ok') else 'failed'}"
        })

    # CRITICAL: Give agent the actual code it needs to fix
    script_context = ""
    if current_action.get('type') == 'exec.container_cmd':
        cmd = current_action['params'].get('cmd', '')
        # If running a Python script, include relevant parts of that script
        if 'python' in cmd and 'workspace/' in cmd:
            script_path = None
            for word in cmd.split():
                if word.startswith('workspace/') and word.endswith('.py'):
                    script_path = Path(word)
                    break

            if script_path and script_path.exists():
                try:
                    full_script = script_path.read_text(encoding='utf-8')
                    # For very long scripts, show key functions mentioned in quality issues
                    if len(full_script) > 5000:
                        script_context = f"\nSCRIPT BEING EXECUTED ({script_path}):\n"
                        script_context += f"Total lines: {len(full_script.splitlines())}\n\n"

                        # Extract functions that might be relevant
                        for func_name in ['find_sidecar_json', 'parse_resolution', 'parse_duration', 'scan_datasets']:
                            match = re.search(rf'^def {func_name}\(.*?\):\n((?:    .*\n)*)', full_script, re.MULTILINE)
                            if match:
                                script_context += f"Function: {func_name}\n{match.group(0)[:500]}...\n\n"
                    else:
                        script_context = f"\nSCRIPT BEING EXECUTED ({script_path}):\n{full_script}\n"
                except:
                    script_context = "\n(Could not read script)\n"

    # Add filesystem investigation for quality issues
    investigation = ""
    if quality_check.get('quality') == 'suspicious':
        # If suspicious output, help agent investigate
        investigation = "\nFILESYSTEM INVESTIGATION:\n"

        # Check what metadata files exist in the datasets
        try:
            import subprocess
            sample_check = subprocess.run(
                ['bash', '-c', 'ls /mnt/x/dataset2/easylanguages/*.json 2>/dev/null | head -3'],
                capture_output=True, text=True, timeout=5
            )
            if sample_check.stdout:
                investigation += f"Sample metadata files found:\n{sample_check.stdout}\n"

                # Show a sample metadata file
                first_file = sample_check.stdout.splitlines()[0] if sample_check.stdout.splitlines() else None
                if first_file:
                    try:
                        sample_data = Path(first_file).read_text(encoding='utf-8')[:500]
                        investigation += f"\nSample metadata content ({Path(first_file).name}):\n{sample_data}\n"
                    except:
                        pass
        except:
            investigation += "(Could not investigate filesystem)\n"

    prompt = f"""You are an adaptive execution agent observing a plan in progress.

ORIGINAL PLAN:
Plan ID: {original_plan.get('plan_id')}
Total actions: {len(original_plan.get('actions', []))}

CURRENT ACTION (index {action_index}):
{json.dumps(current_action, indent=2)}

OBSERVATION (execution result):
{json.dumps(observation, indent=2)}

QUALITY CHECK:
Quality: {quality_check.get('quality')}
Issues: {quality_check.get('issues', [])}
Suggestions: {quality_check.get('suggestions', [])}

RECENT EXECUTION HISTORY:
{json.dumps(history_summary, indent=2)}
{script_context}
{investigation}

ANALYSIS REQUIRED:
The action {'SUCCEEDED' if observation.get('success') else 'FAILED'}.
Quality assessment: {quality_check.get('quality')}

Based on ALL the information above (observation, quality check, script code, filesystem investigation), decide what to do next.

ALLOWED ADAPTATIONS (you can ONLY use existing action types from policy):
- fs.write (create/overwrite files in workspace/ or staging/)
- fs.append (append to files)
- fs.move (move files)
- exec.container_cmd (run commands: python, bash, ffmpeg, etc.)
- ingest.promote (promote files to dataset/ - append-only)

DECISION OPTIONS:

1. "continue": Action succeeded and quality is good, move to next action
   {{"decision": "continue", "reason": "..."}}

2. "fix_and_retry": Action succeeded but quality is suspicious/bad, fix the issue
   {{"decision": "fix_and_retry", "fix_actions": [{{"type": "fs.write", "params": {{...}}}}], "reason": "..."}}

   CRITICAL: fix_actions must contain REAL CODE FIXES, not placeholders!

   Example - If metadata parsing fails due to .info.json files:
   {{
     "decision": "fix_and_retry",
     "fix_actions": [{{
       "type": "fs.write",
       "params": {{
         "path": "workspace/analyze_datasets.py",
         "content": "<FULL FIXED SCRIPT with actual code changes - e.g., change glob pattern from '*.json' to '*.info.json' or update stem matching logic>"
       }}
     }}],
     "reason": "Script only checks .json but metadata files use .info.json naming (YouTube-DL format). Fixed glob pattern and stem matching."
   }}

   You MUST provide the COMPLETE fixed file content, not just "fixed code" placeholder!

3. "skip": Action failed but is optional/non-critical
   {{"decision": "skip", "reason": "..."}}

4. "abort": Fatal error, cannot recover
   {{"decision": "abort", "reason": "..."}}

IMPORTANT RULES:
- NO delete operations (not in policy)
- NO writes to dataset/ or evidence/ (use ingest.promote instead)
- fix_actions must use ONLY the allowed action types above
- Be concise: max 2-3 fix_actions

OUTPUT FORMAT - CRITICAL:
You MUST return ONLY valid JSON, NO markdown blocks, NO explanations, NO preamble.
The JSON must be a single object with a "decision" field.

Examples:
{{"decision": "continue", "reason": "Output is acceptable despite warning"}}

{{"decision": "fix_and_retry", "fix_actions": [{{"type": "fs.write", "params": {{"path": "workspace/script.py", "content": "fixed code"}}}}], "reason": "Found bug in JSON parsing"}}

{{"decision": "skip", "reason": "Optional action, can proceed"}}

{{"decision": "abort", "reason": "Fatal error, cannot recover"}}

NOW OUTPUT YOUR DECISION AS JSON ONLY:
"""

    try:
        output = call_codex_cli(prompt, timeout=120)
        decision = extract_json_from_codex_output(output)

        # Validate decision structure
        if 'decision' not in decision:
            return {'decision': 'abort', 'reason': 'Invalid agent response - missing decision field'}

        valid_decisions = ['continue', 'fix_and_retry', 'skip', 'abort']
        if decision['decision'] not in valid_decisions:
            return {'decision': 'abort', 'reason': f"Invalid decision: {decision['decision']}"}

        return decision

    except Exception as e:
        # If agent fails to respond, default to safe behavior
        ledger_log('agent_error', error=str(e), action_index=action_index)
        if observation.get('success'):
            return {'decision': 'continue', 'reason': 'Agent error but action succeeded'}
        else:
            return {'decision': 'abort', 'reason': f'Agent error and action failed: {e}'}


def agentic_execute(approved_plan: dict, original_task: str = '') -> dict:
    """
    Execute plan with adaptive feedback loop.

    Agents can observe results and adapt, but all safety constraints preserved:
    - Gateway enforces policy (no delete, no protected writes)
    - Same action allowlist as before
    - All actions logged

    Returns: {'ok': bool, 'executed': list, 'adaptations': int, ...}
    """
    policy = Policy()
    plan_id = approved_plan.get('plan_id', 'unknown')
    actions = approved_plan.get('actions', [])

    ledger_log('agentic_execution_start', plan_id=plan_id, total_actions=len(actions))

    execution_history = []
    adaptation_count = 0
    max_adaptations_per_action = 3

    action_idx = 0
    while action_idx < len(actions):
        current_action = actions[action_idx]
        action_id = current_action.get('id', f'A{action_idx}')

        ledger_log('action_start', action_index=action_idx, action_id=action_id,
                   action_type=current_action.get('type'))

        # Execute action through gateway (safety enforced)
        result = execute_action(current_action, policy, plan_id)

        execution_history.append({
            'action_index': action_idx,
            'action': current_action,
            'result': result
        })

        # Build observation
        observation = build_observation(current_action, result, action_idx)

        # Check output quality
        quality_check = check_output_quality(current_action, result, original_task)

        # If action failed OR quality is suspicious, ask agent to observe and adapt
        if not result.get('ok') or quality_check.get('quality') in ['suspicious', 'bad']:
            ledger_log('quality_issue', action_id=action_id, quality=quality_check.get('quality'),
                      issues=quality_check.get('issues'))

            # Call agent to decide what to do
            decision = call_agent_observe_and_adapt(
                original_plan=approved_plan,
                action_index=action_idx,
                current_action=current_action,
                observation=observation,
                quality_check=quality_check,
                execution_history=execution_history
            )

            ledger_log('agent_decision', action_id=action_id, decision=decision.get('decision'),
                      reason=decision.get('reason', ''))

            if decision['decision'] == 'continue':
                # Agent says it's ok despite issues, move on
                action_idx += 1

            elif decision['decision'] == 'fix_and_retry':
                # Agent proposes fixes
                fix_actions = decision.get('fix_actions', [])
                if not fix_actions:
                    ledger_log('adaptation_error', reason='fix_and_retry but no fix_actions provided')
                    action_idx += 1
                    continue

                if adaptation_count >= max_adaptations_per_action * len(actions):
                    ledger_log('max_adaptations_reached', adaptations=adaptation_count)
                    return {
                        'ok': False,
                        'reason': 'Max adaptations reached',
                        'executed': execution_history,
                        'adaptations': adaptation_count
                    }

                # Execute fix actions
                ledger_log('applying_fixes', fix_count=len(fix_actions))
                for fix_idx, fix_action in enumerate(fix_actions):
                    fix_result = execute_action(fix_action, policy, plan_id)
                    execution_history.append({
                        'action_index': f'{action_idx}_fix_{fix_idx}',
                        'action': fix_action,
                        'result': fix_result
                    })

                    if not fix_result.get('ok'):
                        ledger_log('fix_failed', fix_index=fix_idx)
                        return {
                            'ok': False,
                            'reason': f'Fix action {fix_idx} failed',
                            'executed': execution_history,
                            'adaptations': adaptation_count
                        }

                adaptation_count += 1
                # Retry current action (don't increment action_idx)
                ledger_log('retrying_action', action_id=action_id, attempt=adaptation_count)

            elif decision['decision'] == 'skip':
                # Agent says skip this action
                ledger_log('action_skipped', action_id=action_id, reason=decision.get('reason'))
                action_idx += 1

            elif decision['decision'] == 'abort':
                # Fatal error
                ledger_log('execution_aborted', action_id=action_id, reason=decision.get('reason'))
                return {
                    'ok': False,
                    'reason': decision.get('reason', 'Agent aborted execution'),
                    'executed': execution_history,
                    'adaptations': adaptation_count,
                    'aborted_at': action_idx
                }
        else:
            # Action succeeded and quality is good, move to next
            ledger_log('action_complete', action_id=action_id, quality='good')
            action_idx += 1

    # All actions completed
    ledger_log('agentic_execution_complete', plan_id=plan_id, total_adaptations=adaptation_count)

    return {
        'ok': True,
        'executed': execution_history,
        'adaptations': adaptation_count,
        'plan_id': plan_id
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Agentic execution with adaptation')
    parser.add_argument('--plan', default='plans/reviewed_plan.json', help='Path to approved plan')
    parser.add_argument('--task', default='', help='Original task file (for context)')
    args = parser.parse_args()

    # Load approved plan
    with open(args.plan, 'r', encoding='utf-8') as f:
        reviewed = json.load(f)

    if not reviewed.get('approved'):
        print('ERROR: Plan not approved')
        sys.exit(1)

    plan = reviewed.get('plan', {})

    # Load original task if provided
    task_text = ''
    if args.task and Path(args.task).exists():
        task_text = Path(args.task).read_text(encoding='utf-8')

    # Execute with adaptation
    result = agentic_execute(plan, original_task=task_text)

    # Save execution report
    report_path = Path('reports/agentic_execution.json')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f"\nAgentic execution {'SUCCEEDED' if result['ok'] else 'FAILED'}")
    print(f"Total actions: {len(result['executed'])}")
    print(f"Adaptations applied: {result['adaptations']}")
    print(f"Report: {report_path}")

    sys.exit(0 if result['ok'] else 1)
