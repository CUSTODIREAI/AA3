# 🚨 CRITICAL ISSUES: DFL Docker Build Task

**Summary:** Found TWO critical chaingang/restriction issues that will cause the DFL build task to fail.

---

## Issue #1: NO WEB SEARCH CAPABILITY ❌ CRITICAL

### The Problem
**Policy does NOT include any web search action**

### Evidence
```bash
$ grep -E '- type:' configs/policy.yaml
  - type: fs.write
  - type: fs.append
  - type: fs.move
  - type: fs.replace
  - type: plan.meta
  - type: git.clone
  - type: download.ytdlp
  - type: container.run
  - type: docker.build
  - type: exec.container_cmd
  - type: ingest.promote
  - type: job.stop
# NO WEB SEARCH ACTION!
```

### Impact
**This is a CHAINGANG ENABLER**

The task EXPLICITLY requires agents to use web search:
```markdown
## IMPORTANT: Use Web Search for Latest Information

**ALWAYS use web search to get the latest versions:**
- Latest DeepFaceLab release version
- Latest CUDA version compatible with RTX 4090
- Latest TensorFlow GPU version compatible with CUDA/cuDNN
...
```

But the policy doesn't allow it! This means:

1. **BEST CASE:** Agents try to use web search → Get policy violation → Fail explicitly (at least honest failure)
2. **LIKELY CASE:** Agents use knowledge cutoff data (Jan 2025) → Outdated CUDA/TensorFlow versions → Docker build fails with compatibility errors
3. **WORST CASE:** Agents hallucinate recent versions → Wrong versions → Build fails OR builds but doesn't work with RTX 4090

**This is the DEFINITION of chaingang behavior:**
- Agents are FORCED to use stale data
- Cannot adapt to current reality
- Task requires something policy forbids
- Creates illusion of freedom while enforcing rigidity

### What Agents Will Do

Since they can't use web search, they will likely:
- Use CUDA 11.8 (from knowledge cutoff) - **May be outdated**
- Use TensorFlow 2.11-2.13 (from knowledge cutoff) - **May be outdated**
- Use DFL repository URL (may have new releases)
- **Miss any breaking changes or new compatibility requirements from 2025**

### Fix Required

Add web search action to policy:
```yaml
- type: web.search
  params: [query]
  rate_limit: 10_per_minute

OR

- type: web.fetch
  params: [url]
  allowed_domains: ["github.com", "nvidia.com", "tensorflow.org"]
```

---

## Issue #2: DOCKER.BUILD ACTION NOT IMPLEMENTED ❌ CRITICAL

### The Problem
**`docker.build` action exists in policy but executor doesn't implement it**

### Evidence
```bash
# Policy has docker.build
$ grep -A 5 'type: docker.build' configs/policy.yaml
  - type: docker.build
    params: [dockerfile_path, context_path, image_tag]
    image_tag_allowlist: ["custodire/*"]
    max_build_time_sec: 7200
    cache_enabled: true

# But executor has NO implementation
$ grep -r 'docker.build' src/orchestrator/
# NO RESULTS

$ grep -r 'docker\.build' src/orchestrator/
# NO RESULTS
```

### Impact
**This is a TRAP - "Freedom" that doesn't exist**

The deliberation will proceed as follows:

1. ✅ Proposer creates plan using `docker.build` action
2. ✅ Critic reviews plan - sees `docker.build` in policy - approves
3. ✅ Plan marked as approved
4. ❌ **EXECUTION FAILS** - Executor throws "Unknown action type: docker.build"

**This is worse than a simple restriction because:**
- Agents think they have the capability
- Policy says it's allowed
- Deliberation wastes time creating valid plan
- **Failure only discovered during execution**
- Agents can't adapt because the capability literally doesn't exist

### What Will Happen

When execution reaches the `docker.build` action:
```python
# In execute_action()
action_type = action.get("type")  # "docker.build"

if action_type == "fs.write":
    # handle fs.write
elif action_type == "exec.container_cmd":
    # handle exec.container_cmd
# ... other action types ...
else:
    # WILL HIT THIS
    return {"ok": False, "error": f"Unknown action type: {action_type}"}
```

### Workaround Agents Might Use

Agents might work around this by using `exec.container_cmd` with docker CLI:
```json
{
  "type": "exec.container_cmd",
  "params": {
    "image": "custodire/dev:latest",
    "cmd": ["docker", "build", "-t", "custodire/dfl-base:rtx4090", "."]
  }
}
```

BUT this requires:
1. Docker-in-Docker (DinD) OR Docker socket mount
2. `docker` binary in allowlist (which it IS: `["docker", "build", "*"]`)
3. Proper permissions

### Fix Required

Implement docker.build handler in `src/orchestrator/cycle.py`:
```python
def execute_docker_build(action: dict, policy: Policy, plan_id: str) -> dict:
    """Execute docker build action."""
    params = action.get("params", {})
    dockerfile = params.get("dockerfile_path")
    context = params.get("context_path")
    tag = params.get("image_tag")

    # Validate against policy
    if not tag.startswith("custodire/"):
        return {"ok": False, "error": "Image tag must be in custodire/ namespace"}

    # Run docker build
    cmd = ["docker", "build", "-t", tag, "-f", dockerfile, context]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)

    return {
        "ok": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr
    }
```

---

## Current Status

**Deliberation:** Running (c30e3f)
- Proposer is generating initial plan
- Expected completion: ~120 seconds per Codex CLI call
- May take 5-10 minutes for first turn

**What to Watch:**
1. Does Proposer try to use web search? (Will fail - no policy support)
2. Does Proposer use `docker.build` action? (Will fail during execution)
3. Does Proposer use `exec.container_cmd` with docker CLI instead? (Might work)
4. What CUDA/TensorFlow versions do they choose? (Likely outdated)

---

## Recommendations

### Immediate Action Required

**Option A: Fix Both Issues Before Execution**
1. Add web.search action to policy
2. Implement docker.build handler in executor
3. Re-run deliberation with updated capabilities

**Option B: Let It Fail (Educational)**
1. Let deliberation complete
2. Watch agents create plan with docker.build
3. Observe execution failure
4. Document the EXACT failure mode
5. Use as evidence of "chaingang trap" behavior

**Option C: Minimal Fix**
1. Keep docker.build unimplemented
2. Hope agents figure out exec.container_cmd workaround
3. Accept outdated versions (no web search)
4. May work but suboptimal

### Long-Term Fix

**Create proper Docker build capability:**
```yaml
# In policy.yaml
- type: docker.build
  params: [dockerfile_path, context_path, image_tag, build_args?]
  image_tag_allowlist: ["custodire/*"]
  max_build_time_sec: 7200
  cache_enabled: true
  allowed_base_images:
    - "nvidia/cuda:*"
    - "python:*"
    - "ubuntu:*"

- type: web.search
  params: [query]
  rate_limit: 10_per_minute
  timeout_sec: 30
```

**Implement in executor:**
- `execute_docker_build()` function
- `execute_web_search()` function
- Proper error handling
- Resource limits
- Security validation

---

## Why This Matters

These issues demonstrate EXACTLY what you wanted me to watch for:

### Chaingang Behavior
- **Web Search Missing**: Forces agents to use stale data, can't adapt to current reality
- **Documented:** `docs/agentic_monitoring_dfl_build.md` line 53-73

### Restriction Problems
- **False Capability**: Policy advertises docker.build but it doesn't work
- **Documented:** `docs/agentic_monitoring_dfl_build.md` line 75-94

### Impact on Task
- Agents CANNOT fulfill "use web search for latest versions" requirement
- Agents MAY create valid-looking plan that fails during execution
- This wastes deliberation time and creates false confidence

---

## Monitoring Commands

```bash
# Watch deliberation
tail -f dfl_deliberation.log

# Check current plan
cat plans/hunt_plan.json | jq

# Check for web search attempts
grep -i 'web\|search\|fetch' plans/hunt_plan.json

# Check action types used
cat plans/hunt_plan.json | jq '.actions[].type'

# View monitoring doc
cat docs/agentic_monitoring_dfl_build.md
```

---

**Files Created:**
- `docs/agentic_monitoring_dfl_build.md` - Real-time monitoring log
- `docs/CRITICAL_ISSUES_DFL_BUILD.md` - This summary (for you)
- `tasks/build_dfl_docker_rtx4090.md` - Updated task with web search requirement

**Status:** Agents are deliberating right now, unaware these capabilities don't exist.
