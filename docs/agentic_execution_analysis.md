# Agentic Execution System: Evolution and Analysis

**Date:** 2025-10-29
**System:** Custodire AA Multi-Agent Architecture
**Author:** Claude Code Analysis

---

## Executive Summary

This document traces the evolution of our multi-agent execution system from a rigid "chaingang" implementation to a conversational, adaptive architecture. It analyzes failures, identifies solutions, and documents the current state.

---

## 1. The Original System: "Chaingang" Behavior

### 1.1 Architecture (From custodire-aa-system.zip)

**Components:**
- `scripts/deliberate.py` - Multi-agent deliberation for planning
- `src/orchestrator/cycle.py` - Rigid plan execution
- `src/gateway/policy.py` - Safety enforcement
- `src/agents/agent_wrapper.py` - Agent CLI wrappers

**Execution Flow:**
```
deliberate.py → produces approved plan
    ↓
cycle.py → executes actions sequentially
    ↓
Action 1: fs.write (create script)
    ↓
Action 2: exec.container_cmd (run script)
    ↓
Action 3: ingest.promote (promote results)
    ↓
DONE (no adaptation possible)
```

### 1.2 Critical Failure: The `.info.json` Issue

**Scenario:**
```python
# Action 2 executes: python workspace/analyze_datasets.py

# Script contains:
def find_sidecar_json(video_path: Path):
    candidates = []
    base = video_path.with_suffix('')
    cand1 = base.with_suffix('.json')  # Only checks .json
    if cand1.exists():
        candidates.append(cand1)
    # ... rest of function
```

**Problem:**
- Script scans 41,192 videos
- Finds 85 real videos
- BUT reports **0 suitable videos** (≥10s, ≥720p)
- Why? Metadata files are named `*.info.json` (YouTube-DL format)
- Script only checks `*.json` → never finds metadata
- Without duration/resolution data, ALL videos fail suitability check

**System Response:**
```
✅ Action 1: SUCCESS (wrote script)
✅ Action 2: SUCCESS (script ran without errors)
⚠️ Action 3: FAILED (0 videos selected, nothing to promote)

VERDICT: Task completed, but results are WRONG
```

**Agents never detected the issue!** They executed blindly like a "chaingang."

---

## 2. Comparison: Claude's Conversation with Codex vs. Chaingang System

### 2.1 Claude's Conversational Approach (Manual)

**Example: When Claude (me) worked with Codex on the JSON extraction bug:**

```
Claude: "The JSON extraction is failing. Here's the error and output..."

Codex: "I see the issue - you're looking for 'plan_id' but execution returns
        'decision' field. Add that to the has_key_field check."

Claude: "Applied the fix. But I'm still seeing parse failures on some outputs..."

Codex: "Right, those outputs have thinking blocks before the JSON. Try scanning
        from the LAST 'codex' marker, not the first."

Claude: "Perfect! That worked. But we're also getting timeouts on large prompts..."

Codex: "Use a temp file instead of command-line args - avoids escaping issues."

Claude: "Implemented. Now it works reliably."
```

**Key Characteristics:**
- 🔄 **Iterative refinement** - Multiple turns to reach solution
- 📊 **Shared context** - Each turn builds on previous understanding
- 🎯 **Progressive diagnosis** - Peeling layers of issues
- ✅ **Explicit approval** - Codex confirms "that worked"
- 🛠️ **Adaptive strategy** - Changes approach based on feedback

### 2.2 Chaingang System (Original)

**Same scenario in chaingang mode:**

```
[Planning Phase - Deliberation Works Well]
Proposer: "Here's a plan to analyze datasets..."
Critic: "Add error handling and tags..."
Proposer: "Updated plan..."
Critic: "Approved ✅"

[Execution Phase - No Adaptation]
Action 1: Write script → SUCCESS
Action 2: Run script → SUCCESS (but wrong results!)
Action 3: Promote results → FAIL (nothing to promote)

System: "Execution failed. Task incomplete."
[No conversation, no adaptation, no fix]
```

**Key Problems:**
- ❌ **No feedback loop** - Execution is one-way
- ❌ **No context retention** - Each action isolated
- ❌ **Success ≠ Correctness** - Script runs but produces wrong results
- ❌ **Blind execution** - Can't observe intermediate outputs
- ❌ **No recovery** - One chance, then done

### 2.3 Side-by-Side Comparison

| Aspect | Claude ↔ Codex (Manual) | Chaingang System |
|--------|------------------------|------------------|
| **Conversation** | ✅ Multi-turn dialogue | ❌ Single-shot execution |
| **Context** | ✅ Shared history | ❌ Isolated actions |
| **Observation** | ✅ "I'm seeing failures..." | ❌ Only exit codes |
| **Adaptation** | ✅ "Try temp file instead" | ❌ Fixed plan only |
| **Approval** | ✅ "That worked!" | ❌ Implicit (exit code 0) |
| **Error Recovery** | ✅ Multiple attempts | ❌ One shot only |
| **Result Quality** | ✅ Verified correct | ❌ Script ran = success |

---

## 3. Root Cause Analysis: Why Chaingang Failed

### 3.1 Separation of Planning and Execution

**Design Flaw:**
```
DELIBERATION PHASE (conversational, adaptive):
    Proposer ↔ Critic → Approved Plan ✅

EXECUTION PHASE (rigid, blind):
    Execute Action 1
    Execute Action 2
    Execute Action 3
    DONE
```

**The Paradox:**
- Agents are smart during planning (debate, refine, approve)
- Agents are dumb during execution (just run commands)
- **No bridge between planning intelligence and execution reality**

### 3.2 The "Exit Code 0 = Success" Fallacy

**What the system checked:**
```python
result = subprocess.run(cmd, ...)
if result.returncode == 0:
    return {'ok': True}  # SUCCESS!
```

**What it should have checked:**
```python
result = subprocess.run(cmd, ...)
if result.returncode != 0:
    return {'ok': False}

# But ALSO check output quality:
if 'suitable_real_count": 0' in result.stdout:
    return {'quality': 'suspicious', 'needs_review': True}
```

**Real-world analogy:**
- **Chaingang:** "The truck driver drove the route successfully!" ✅
- **Reality:** "Yes, but the truck was empty - no cargo delivered!" ⚠️

### 3.3 Lack of Introspection

**Missing capabilities:**
1. **Output parsing** - Can't read `report.json` to see 0 suitable videos
2. **Quality metrics** - No heuristics for "suspicious" results
3. **Intermediate observation** - Can't examine files between actions
4. **Context from previous runs** - No memory of what worked before
5. **Self-correction** - No mechanism to say "wait, this doesn't look right"

---

## 4. What We Discovered: Keys to Adaptive Execution

### 4.1 Discovery #1: Rich Observation Context

**Breakthrough:**
```python
def build_observation(action, result, action_idx):
    obs = {
        'success': result.get('ok'),
        'stdout_preview': result['stdout'][:1000],
        # CRITICAL: Parse output files!
        'output_files': {}
    }

    # If script mentions writing files, go read them!
    if 'staging/dataset_analysis/report.json' in result['stdout']:
        data = json.loads(Path('staging/...').read_text())
        obs['output_files']['report.json'] = {
            'suitable_real_count': data.get('suitable_real_count'),
            'total_real': data.get('total_real')
        }

    return obs
```

**Impact:** Agents can now see *what* the script produced, not just *that* it ran.

### 4.2 Discovery #2: Quality Heuristics

**Automatic detection:**
```python
def check_output_quality(action, result, task):
    if 'suitable_real_count": 0' in result['stdout']:
        return {
            'quality': 'suspicious',
            'issues': ['Found 0 suitable videos - metadata parsing failure?']
        }

    # Also check parsed files:
    report = read_report_json()
    if report['total_real'] > 0 and report['suitable_real_count'] == 0:
        return {
            'quality': 'suspicious',
            'issues': [f'Found {report["total_real"]} real videos but 0 suitable']
        }
```

**Impact:** System knows when results don't make sense.

### 4.3 Discovery #3: Conversational Refinement Loop

**What didn't work (my first attempt):**
```
Stage 1: Codex diagnoses → one-shot
Stage 2: Claude fixes → one-shot
Stage 3: Codex reviews → one-shot (always suggests polish)
[Infinite loop of polish suggestions]
```

**What should work (orchestrated deliberation):**
```
Issue detected → Call deliberate.py with "fix script" sub-task
    ↓
Proposer: "Change .json to .info.json"
    ↓
Critic: "Also check for .json fallback"
    ↓
Proposer: "Added fallback logic"
    ↓
Critic: "Approved ✅"
    ↓
Apply fix and retry
```

**Key insight:** Reuse the existing deliberation system for adaptation!

### 4.4 Discovery #4: Temp File for CLI Prompts

**Problem:**
```bash
# Large JSON gets escaped multiple times:
codex exec "prompt with {\"nested\": {\"json\": \"...\"}}"
# → Timeout after 120s (escaping hell)
```

**Solution:**
```python
prompt_file = Path('temp_codex_prompt.txt')
prompt_file.write_text(prompt)
subprocess.run(['bash', '-c', f'codex exec "$(cat {prompt_file})"'])
```

**Impact:** No more timeouts, handles any prompt size.

### 4.5 Discovery #5: Concise Context

**Before:**
```python
prompt = f"""
CURRENT ACTION:
{json.dumps(current_action, indent=2)}  # 5000+ chars of nested JSON
"""
```

**After:**
```python
action_summary = {
    'type': current_action.get('type'),
    'command': current_action['params'].get('cmd')
    # Omit huge content fields
}
prompt = f"""
CURRENT ACTION:
{json.dumps(action_summary, indent=2)}  # < 200 chars
"""
```

**Impact:** Faster processing, clearer signal-to-noise.

---

## 5. Evolution Timeline

### Phase 1: Chaingang (Original System)
```
[Planning] Proposer ↔ Critic ✅ (conversational)
[Execution] Action → Action → Action ❌ (rigid)
Result: Smart planning, blind execution
```

**Failure Mode:** 0 suitable videos, no detection, no fix

### Phase 2: First Adaptive Attempt (agentic_execute.py)
```
[Execution with detection]
Action → Observe → Agent Decision → Fix → Retry
```

**Issues:**
- Still one-shot decisions (no conversation)
- Codex timeout on large prompts
- "fix_and_retry" with placeholder fixes

### Phase 3: Three-Stage Pipeline (agentic_execute_v2.py)
```
[Execution with stages]
Action → Observe → Stage 1 (Codex) → Stage 2 (Claude) → Stage 3 (Codex) → Retry
```

**Issues:**
- ❌ No conversation between stages
- ❌ Codex always suggests polish → unnecessary loops
- ❌ Bypassed deliberation.py orchestrator
- ❌ Lost the conversational intelligence

**Status:** Fixed technical issues (temp files, timeouts), but wrong architecture!

### Phase 4: Return to Orchestrated Deliberation (NEXT)
```
[Execution with deliberation]
Action → Observe Quality Issue →
    ↓
Call deliberate.py("fix the script to handle .info.json")
    ↓
Proposer ↔ Critic (multi-turn conversation)
    ↓
Approved Fix ✅
    ↓
Apply fix and retry Action
```

**Benefits:**
- ✅ Reuses existing conversation system
- ✅ Full context and history
- ✅ Explicit approval (not implicit)
- ✅ Maintains separation of concerns

---

## 6. Current Status: Where We Are Now

### 6.1 What Works
- ✅ **Quality detection** - Catches suspicious output (0 suitable videos)
- ✅ **Rich observation** - Parses output files, sees actual results
- ✅ **Temp file CLI** - No more timeouts on large prompts
- ✅ **Concise context** - Efficient prompt engineering
- ✅ **Safety preserved** - Gateway policy unchanged (no delete)

### 6.2 What's Broken
- ❌ **No real conversation** - Stages are one-shot, not iterative
- ❌ **Orchestrator bypassed** - deliberate.py unused during execution
- ❌ **Polish loop** - Codex always suggests improvements (needs approval mechanism)
- ❌ **Context isolation** - Each stage doesn't see previous turns

### 6.3 Files Status

| File | Status | Notes |
|------|--------|-------|
| `scripts/deliberate.py` | ✅ Working | Orchestrates Proposer ↔ Critic for planning |
| `src/agents/agent_wrapper.py` | ✅ Fixed | Temp file CLI, robust JSON extraction |
| `src/orchestrator/cycle.py` | ⚠️ Limited | Executes actions but no adaptation |
| `scripts/agentic_execute.py` | ⚠️ Deprecated | First attempt, has issues |
| `scripts/agentic_execute_v2.py` | ❌ Wrong Architecture | Bypasses orchestrator, no conversation |

---

## 7. The Path Forward

### 7.1 Recommended Architecture

**Integrate deliberation INTO execution:**

```python
def agentic_execute_with_deliberation(approved_plan, task):
    """Execute plan with adaptive deliberation on issues"""

    for action in approved_plan['actions']:
        # Execute action
        result = execute_action(action)
        observation = build_observation(action, result)
        quality = check_output_quality(action, result)

        # If quality issue, trigger deliberation
        if quality['quality'] in ['suspicious', 'bad']:
            fix_task = create_fix_task(action, observation, quality)

            # Call existing deliberation system!
            approved_fix = deliberate.run(fix_task)

            if approved_fix:
                apply_fix(approved_fix)
                result = execute_action(action)  # Retry
            else:
                abort("Could not fix issue")
```

**Key principles:**
1. **Reuse `deliberate.py`** - Don't reinvent the wheel
2. **Maintain conversation** - Proposer ↔ Critic iterate to approval
3. **Keep safety** - All fixes go through gateway
4. **Build context** - Issue description becomes task for deliberation

### 7.2 Example: The `.info.json` Fix (How It Should Work)

```
[Execution Phase]
Action A2: python workspace/analyze_datasets.py
    ↓
Result: 0 suitable videos (suspicious!)
    ↓
Create fix task: "Fix script to handle .info.json metadata files"
    ↓
Call deliberate.py(fix_task)
    ↓
[Deliberation Phase]
Proposer: "Change line 45: base.with_suffix('.info.json')"
    ↓
Critic: "Also keep .json as fallback for other datasets"
    ↓
Proposer: "Added check for both .info.json and .json"
    ↓
Critic: "Perfect! Approved ✅"
    ↓
[Back to Execution]
Apply fix to workspace/analyze_datasets.py
Retry Action A2
    ↓
Result: 85 suitable videos found ✅
Continue to Action A3...
```

### 7.3 Implementation Tasks

1. **Modify `agentic_execute.py`**
   - Remove hardcoded 3-stage logic
   - Add `call_deliberation_for_fix()` function
   - Pass quality issues as sub-tasks to `deliberate.py`

2. **Extend `deliberate.py`**
   - Add "fix mode" parameter
   - Include execution context in history
   - Return applied plan (not just approved plan)

3. **Enhance `agent_wrapper.py`**
   - Keep temp file CLI fix ✅
   - Keep robust JSON extraction ✅
   - Add execution context to prompts

4. **Update `cycle.py`**
   - Make it stateless (called by agentic_execute)
   - Return rich observations
   - Support action retry

---

## 8. Key Lessons Learned

### 8.1 Technical Lessons
1. **Exit code ≠ Success** - Need to check output quality
2. **Temp files > Command args** - For large prompts
3. **Parse, don't just log** - Read output files, extract metrics
4. **Truncate context** - Keep prompts focused and efficient

### 8.2 Architectural Lessons
1. **Don't bypass working systems** - Reuse deliberation orchestrator
2. **Conversation > Pipeline** - Multi-turn beats one-shot
3. **Explicit approval matters** - "Polish suggestions" ≠ Rejection
4. **Context is king** - Agents need history to make good decisions

### 8.3 Design Principles
1. **Separation of concerns:**
   - Planning: `deliberate.py` (conversational)
   - Execution: `cycle.py` (stateless action runner)
   - Adaptation: Call deliberation when needed

2. **Progressive enhancement:**
   - Start: Execute plan rigidly
   - Detect: Observe outputs, check quality
   - Adapt: Trigger deliberation on issues
   - Apply: Fix and retry

3. **Safety invariants:**
   - Gateway policy NEVER changes
   - Agents can't gain new powers during execution
   - All actions logged to immutable ledger
   - Append-only dataset prevents overwrites

---

## 9. Comparison Table: All Approaches

| Aspect | Chaingang | Adaptive v1 | 3-Stage v2 | Orchestrated (Target) |
|--------|-----------|-------------|------------|----------------------|
| **Conversation** | Planning only | One-shot decision | 3 one-shots | Multi-turn iterative |
| **Context** | None | Limited | Per-stage | Full history |
| **Orchestrator** | Used for planning | Bypassed | Bypassed | Integrated |
| **Approval** | Explicit | Implicit | Always polish | Explicit |
| **Timeout Fix** | N/A | No | Yes ✅ | Yes ✅ |
| **Quality Detection** | No | Yes ✅ | Yes ✅ | Yes ✅ |
| **Observation** | Exit codes | Output files ✅ | Output files ✅ | Output files ✅ |
| **Adaptation** | None | Yes | Yes | Yes (conversational) |
| **Architecture** | Rigid | Hacky | Wrong | Correct |

---

## 10. Conclusion

The journey from chaingang to adaptive execution revealed a fundamental insight: **intelligence during planning must extend to execution**.

The original system separated smart planning (conversational deliberation) from dumb execution (rigid action chains). Our first attempts to add adaptation created new problems by bypassing the existing conversation system.

**The solution is simple:** When execution encounters issues, don't create a new conversation system—**use the one that already works**. Call `deliberate.py` with "fix this" sub-tasks, let Proposer and Critic iterate to approval, then apply the fix and retry.

This preserves the architectural elegance:
- **Deliberation** = Conversation (planning, fixing, refining)
- **Execution** = Action (stateless, safe, logged)
- **Gateway** = Safety (unchanging, enforced)

**Next step:** Implement orchestrated adaptive execution that calls `deliberate.py` when quality issues are detected.

---

## Appendix A: Code Snippets

### A.1 Quality Detection (What We Built)
```python
def check_output_quality(action: dict, result: dict, task: str) -> dict:
    """Assess quality of execution output"""
    if not result.get('ok'):
        return {'quality': 'bad', 'issues': [result.get('error')]}

    stdout = result.get('stdout', '')
    issues = []

    # Check stdout patterns
    if 'suitable_real_count: 0' in stdout or 'suitable_real_count": 0' in stdout:
        issues.append("Found 0 suitable videos - metadata parsing failure?")

    # CRITICAL: Check output files for suspicious data
    if 'staging/dataset_analysis/report.json' in stdout:
        report_path = Path('staging/dataset_analysis/report.json')
        if report_path.exists():
            report_data = json.loads(report_path.read_text())
            suitable_count = report_data.get('suitable_real_count', -1)
            total_real = report_data.get('total_real', 0)

            if total_real > 0 and suitable_count == 0:
                issues.append(
                    f"Found {total_real} real videos but 0 suitable (≥10s, ≥720p) "
                    "- likely metadata parsing failure"
                )

    if issues:
        return {'quality': 'suspicious', 'issues': issues}

    return {'quality': 'good', 'issues': []}
```

### A.2 Temp File CLI Fix (What We Built)
```python
def call_codex_cli(prompt: str, timeout: int = 300) -> str:
    """Call Codex CLI - ALWAYS uses temp file for reliability"""

    # Write prompt to temp file
    prompt_file = Path('temp_codex_prompt.txt')
    prompt_file.write_text(prompt, encoding='utf-8')

    try:
        if in_wsl:
            cmd = ['bash', '-c', f'codex exec --skip-git-repo-check "$(cat {prompt_file})"']
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        else:
            # Windows → WSL
            cmd = 'wsl bash -c "cd /mnt/x/... && codex exec \\"$(cat temp_codex_prompt.txt)\\""'
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    finally:
        prompt_file.unlink()  # Cleanup

    return proc.stdout
```

### A.3 What We Should Build (Orchestrated Adaptation)
```python
def agentic_execute_with_orchestrator(approved_plan: dict, original_task: str) -> dict:
    """Execute plan with deliberation-based adaptation"""

    policy = Policy()
    actions = approved_plan['actions']
    execution_history = []
    adaptation_count = 0

    action_idx = 0
    while action_idx < len(actions):
        current_action = actions[action_idx]

        # Execute through gateway (safety enforced)
        result = execute_action(current_action, policy)

        # Build rich observation
        observation = build_observation(current_action, result, action_idx)

        # Check output quality
        quality_check = check_output_quality(current_action, result, original_task)

        # If issue detected, trigger deliberation
        if not result['ok'] or quality_check['quality'] in ['suspicious', 'bad']:
            # Create fix task for deliberation
            fix_task = f"""
# Task: Fix Action {current_action['id']}

## Issue Detected
{quality_check['issues']}

## Current Implementation
{json.dumps(current_action, indent=2)}

## Execution Result
{json.dumps(observation, indent=2)}

## Goal
Fix the issue and return an updated action that will work correctly.
"""

            # Write fix task
            fix_task_path = Path('tasks/fix_temp.md')
            fix_task_path.write_text(fix_task)

            # Call existing deliberation system!
            from scripts.deliberate import run as run_deliberation
            approved, fixed_plan = run_deliberation(str(fix_task_path))

            if not approved:
                return {
                    'ok': False,
                    'reason': 'Deliberation could not produce approved fix',
                    'executed': execution_history,
                    'adaptations': adaptation_count
                }

            # Apply fix (update action or related files)
            apply_fix_actions(fixed_plan['actions'])
            adaptation_count += 1

            # Retry action (don't increment action_idx)
            continue

        # Action succeeded with good quality
        execution_history.append({'action': current_action, 'result': result})
        action_idx += 1

    return {
        'ok': True,
        'executed': execution_history,
        'adaptations': adaptation_count
    }
```

---

**End of Document**
