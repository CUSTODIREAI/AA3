# Multi-Agent System Failure Analysis - Need Diagnostic Opinion

## Context
We built 3 generations of multi-agent autonomous systems:
- AAv1: Simple deterministic executor (100% success)
- AAv2/2.5: Multi-agent error recovery with LLM diagnosis
- AAv3: Deliberative multi-agent with consensus (prototype)

## Current Failure: agentic_execute.py

### System Architecture
```python
# agentic_execute.py - Adaptive execution with quality feedback loop
def agentic_execute(plan):
    for action in plan.actions:
        result = execute_action(action)
        observation = build_observation(action, result)
        quality_check = check_output_quality(action, result)

        if not result.ok or quality_check.quality in ['suspicious', 'bad']:
            # Ask agent to decide what to do
            decision = call_agent_observe_and_adapt(...)

            # Problem: decision object missing 'decision' field!
            if 'decision' not in decision:
                return {'ok': False, 'reason': 'Invalid agent response - missing decision field'}
```

### Expected Agent Response Format
```json
{
  "decision": "continue" | "fix_and_retry" | "skip" | "abort",
  "reason": "...",
  "fix_actions": [...]  // if decision="fix_and_retry"
}
```

### What Actually Happens
1. ✅ Action A1 (fs.write) - Creates analyze_datasets.py - SUCCESS
2. ✅ Action A2 (exec.container_cmd) - Runs script, generates 4 output files - SUCCESS
3. ⚠️ Quality check flags: "Unusually short output from script execution"
4. 🤖 Calls call_agent_observe_and_adapt() via Codex
5. ❌ Agent response doesn't contain 'decision' field
6. 💥 System aborts with: "Invalid agent response - missing decision field"

### The Prompt Sent to Agent
```
You are an adaptive execution agent observing a plan in progress.

CURRENT ACTION: {action details}
OBSERVATION: {execution results}
QUALITY CHECK: suspicious - ['Unusually short output from script execution']

DECISION OPTIONS:
1. "continue": Action succeeded and quality is good
   {"decision": "continue", "reason": "..."}

2. "fix_and_retry": Quality suspicious, fix the issue
   {"decision": "fix_and_retry", "fix_actions": [...], "reason": "..."}

3. "skip": Action failed but is optional
   {"decision": "skip", "reason": "..."}

4. "abort": Fatal error
   {"decision": "abort", "reason": "..."}

OUTPUT FORMAT - CRITICAL:
You MUST return ONLY valid JSON, NO markdown blocks, NO explanations.
The JSON must be a single object with a "decision" field.

NOW OUTPUT YOUR DECISION AS JSON ONLY:
```

### Agent Response Received
The response goes through:
```python
output = call_codex_cli(prompt, timeout=120)
decision = extract_json_from_codex_output(output)
# decision object exists but missing 'decision' key!
```

### Execution Trace from Report
```json
{
  "ok": false,
  "reason": "Invalid agent response - missing decision field",
  "executed": [
    {"action_index": 0, "action": {"id": "A1", "type": "fs.write"}, "result": {"ok": true}},
    {"action_index": 1, "action": {"id": "A2", "type": "exec.container_cmd"}, "result": {"ok": true}},
    {"action_index": "1_fix_0", "action": {"type": "fs.write", "params": {"path": "workspace/script.py", "content": "fixed code"}}, "result": {"ok": true}},
    // Repeats the phantom fix 3 times...
  ]
}
```

**Phantom Fix Bug**: System kept applying fix "1_fix_0" with placeholder "fixed code" even though the original action succeeded!

---

## Second Failure: agentic_execute_orch.py

### Error
```
ModuleNotFoundError: No module named 'gateway.execution'
```

### Code
```python
from gateway.execution import execute_action  # Line 15
```

### Directory Structure
```
src/
  gateway/
    policy.py      ✓ exists
    gateway.py     ✓ exists
    execution.py   ✗ MISSING
  orchestrator/
    cycle.py       ✓ has execute_action()
```

**Problem**: Script imports from wrong module path. Should be:
```python
from src.orchestrator.cycle import execute_action
```

---

## Working System: deliberate.py

### Success Rate: 100% (3/3 runs)

```python
def run(task_file):
    # Simple consensus loop
    proposal = call_proposer(task_brief, history, tools_context)

    while turn <= max_turns:
        review = call_critic(proposal, history, tools_context, task_text)
        approved = review.get("approved", False)

        if approved:
            break

        # Refine and retry
        proposal = call_proposer(task_brief, history, tools_context)
        turn += 1

    return approved, final_plan
```

**Why It Works**:
- Simple boolean approval (no complex decision protocol)
- Direct attribute access with defaults: `review.get("approved", False)`
- No strict schema validation

---

## DIAGNOSTIC QUESTIONS FOR CODEX

### 1. JSON Extraction Issue
The `extract_json_from_codex_output()` function should extract JSON from your response. What format are you actually returning when given the agent decision prompt above?

Are you returning:
- A) Pure JSON: `{"decision": "continue", "reason": "..."}`
- B) Markdown wrapped: ```json {...} ```
- C) Text explanation + JSON
- D) Something else?

### 2. Schema Compliance
When prompted with explicit JSON schema requirements like "You MUST return ONLY valid JSON with a 'decision' field", what causes non-compliance? Is it:
- A) The prompt being too long/complex
- B) Instruct-tuning prioritizing helpfulness over strict format
- C) Temperature/sampling causing format drift
- D) Prompt injection from context data

### 3. Quality Check False Positive
The quality check flagged "Unusually short output" even though the script succeeded and created 4 output files correctly. How should we distinguish:
- Real quality issues (wrong output, missing data)
- False positives (warnings that don't matter)
- Acceptable edge cases (script succeeded, output valid but unexpected format)

Should we:
- A) Make quality checks more lenient (only flag real errors)
- B) Add "continue_with_warning" decision option
- C) Let agent see full quality check context and decide
- D) Skip quality checks for successful actions

### 4. Architecture Recommendation
Given these 3 systems:
1. **agentic_execute.py**: Complex decision protocol, fails on schema violations
2. **deliberate.py**: Simple approve/reject, 100% success rate
3. **AAv3 prototype**: Deliberative consensus, currently simulated

Which approach should we prioritize fixing/improving?
- A) Fix agentic_execute schema validation (make it robust)
- B) Extend deliberate.py with more capabilities
- C) Complete AAv3 integration (runs inside Claude Code with real tools)
- D) Hybrid: Simple protocol + AAv3 architecture

### 5. Phantom Fix Bug
Why did the system apply phantom fixes ("1_fix_0" with placeholder "fixed code") when:
- Original action A2 succeeded
- Quality check was only "suspicious" not "bad"
- Agent response should have said "continue" or provided real fixes

Is this:
- A) Agent returning malformed decision (missing fields)
- B) Error handling fallback creating default fix actions
- C) Loop retry logic bug
- D) Schema validation creating placeholder response

---

## REQUEST
Please analyze these 5 questions and provide:
1. Root cause diagnosis for each failure
2. Specific code fixes (show actual Python code changes)
3. Architectural recommendation (which system to prioritize)
4. JSON response format you actually use (so we can adapt extraction)

Be extremely technical and specific. Show actual code snippets for fixes.
