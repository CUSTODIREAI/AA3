# DFL Docker Build - Agent Passthrough Mode Test

**Date:** 2025-10-29
**Test ID:** passthrough-dfl-001
**Status:** 🔄 RUNNING

---

## Test Objective

Verify that Agent Passthrough Mode solves the two critical chaingang issues identified in the original DFL build:

1. **ISSUE #1:** No web search capability → Agents forced to use outdated knowledge cutoff data
2. **ISSUE #2:** docker.build action not implemented → False capability trap

**Expected Outcome:** With passthrough mode enabled, agents should be able to:
- Use `curl`/`wget` to fetch latest CUDA/TensorFlow/DFL versions
- Use `docker build` command directly in sandbox
- Complete full DFL Docker image build without restriction errors

---

## Environment Setup

### Sandbox Configuration
- **Container:** agent-sandbox (running)
- **Image:** ubuntu:22.04
- **GPU:** RTX 4090 (24GB VRAM) - ✅ Accessible
- **Network:** Enabled
- **Mounts:**
  - `/dataset` → Read-only (immutable)
  - `/evidence` → Read-only (immutable)
  - `/workspace` → Read-write (full freedom)
  - `/staging` → Read-write (full freedom)
  - `/cache` → Read-write (full freedom)

### Policy Actions Available
- `agent.passthrough_shell` - ✅ NEW - Full freedom in sandbox
- `fs.write` - Write files to staging/workspace
- `ingest.promote` - Publish to immutable dataset
- `exec.container_cmd` - Legacy container execution

### What Changed Since Last Attempt
- **Added:** configs/policy.yaml lines 103-126 (agent.passthrough_shell action)
- **Added:** src/orchestrator/cycle.py lines 86-148 (passthrough handler)
- **Added:** scripts/start_agent_sandbox.sh (sandbox startup script)
- **Verified:** Kernel-level RO mount enforcement on dataset/evidence

---

## Monitoring Timeline

### Start: 2025-10-29T10:47:00Z
- Cleared old plans (hunt_plan.json, reviewed_plan.json)
- Started fresh deliberation with task: build_dfl_docker_rtx4090.md
- Background process ID: d3c31a
- Monitoring active...

### 10:50:00Z - Hunt Plan Generated
- File: plans/hunt_plan.json (18KB)
- **❌ CRITICAL:** No agent.passthrough_shell actions detected
- Only contains: 8x fs.write, 1x ingest.promote
- Same pattern as original failed attempt

### 10:53:00Z - First Review (REJECTED)
- **Status:** approved=false
- **Rejection Reasons:**
  - "Promotion destinations do not match script/docs paths"
  - "Build/test scripts reference docker/ at repo root but files promote under custodire-dfl/"
- Deliberation continuing to Turn 2...

### 10:58:51Z - Deliberation Complete ✅
- **Status:** Approved=True
- **Turns:** 3
- **Conversation saved:** reports/deliberations/20251029_104800
- **Duration:** ~12 minutes

### Final Plan Analysis

**Action Type Breakdown:**
```
8x  fs.write           - Writing files to staging/
1x  ingest.promote     - Publishing to dataset
0x  agent.passthrough_shell  ❌ NOT USED
```

**Files Created:**
1. staging/docker/dfl-base.Dockerfile
2. staging/docker/dfl.Dockerfile
3. staging/docker/dfl.dockerignore
4. staging/docker/build_dfl_images.sh
5. staging/docker/test_dfl_rtx4090.sh
6. staging/docker/dfl-compose.yaml
7. staging/docs/dfl_docker_images.md
8. staging/docs/dfl_training_workflow.md

---

## ❌ CRITICAL PROBLEM: Agent Passthrough Mode NOT ADOPTED

### The Core Issue

**Despite having agent.passthrough_shell available in the policy, agents did NOT use it.**

The task EXPLICITLY requires:
- ✅ "ALWAYS use web search to get latest versions" (lines 7-15 of task)
- ✅ Docker image building capability

The approved plan contains:
- ❌ ZERO web search/curl commands
- ❌ ZERO docker build executions
- ❌ ZERO agent.passthrough_shell actions

### What the Agents Did Instead

Agents used the SAME approach as the original failed attempt:
1. **fs.write** to create Dockerfiles with hardcoded versions (CUDA 11.8.0, TensorFlow 2.13.1)
2. **fs.write** to create a build SCRIPT that calls `docker build`
3. **ingest.promote** to publish these files to dataset/

### Problems with This Approach

**Problem #1: Outdated Versions (No Web Search)**
- Task requires: "Get latest CUDA/cuDNN/TensorFlow versions"
- Plan uses: CUDA 11.8.0, TensorFlow 2.13.1 (from knowledge cutoff)
- Cannot verify if these are still correct for RTX 4090 in Oct 2025

**Problem #2: Docker Build Won't Execute**
- `build_dfl_images.sh` is just a SCRIPT FILE written to staging/
- It contains `docker build` commands, but those are INSIDE the script
- The script itself is never EXECUTED
- Result: Dockerfiles exist, but no images are actually built

**Problem #3: No Testing**
- Task requires: "Test GPU access, TensorFlow import, DFL extraction"
- Plan only WRITES test scripts, never RUNS them
- Cannot verify if images actually work

### Why This Matters

**The entire purpose of Agent Passthrough Mode was to solve these exact problems:**

1. **Web Search:** Use `curl`/`wget` in sandbox to fetch latest versions
2. **Docker Build:** Use `docker build` in sandbox to actually build images
3. **GPU Testing:** Run test commands in sandbox to verify functionality

**But agents didn't discover this capability exists.**

---

## Root Cause Analysis

### Hypothesis: Agents Don't Know About Passthrough Mode

**Evidence:**
1. Policy declares agent.passthrough_shell (configs/policy.yaml:103-126) ✅
2. Executor implements passthrough handler (src/orchestrator/cycle.py:86-148) ✅
3. Sandbox is running and verified working ✅
4. **BUT:** Agents never attempted to use it ❌

**Possible Causes:**

**1. Agent Prompts Don't Mention It**
- Codex/Claude agents may not receive policy actions list in their prompt
- They may be working from a "known" action set based on previous examples
- passthrough_shell might not be in their "awareness"

**2. Task Doesn't Suggest It**
- Task says "use web search" but doesn't say HOW
- Task doesn't mention agent.passthrough_shell or sandbox
- Agents may assume they can't do it

**3. Agents Prefer "Safe" Patterns**
- Writing files is a known, safe pattern
- Using passthrough requires trusting the sandbox
- Agents may default to conservative approaches

**4. No Examples/Demonstrations**
- No existing plans in the system use passthrough
- Agents learn from examples; if none exist, they won't innovate

### Verification Test Needed

To confirm root cause, check:
1. What actions does the agent prompt include?
2. Are there any example plans that use passthrough?
3. Does the task need to explicitly request passthrough usage?

---

## Impact Assessment

### What Works
✅ Deliberation system (Proposer ↔ Critic) functions correctly
✅ Multi-turn refinement based on Critic feedback
✅ Path corrections applied successfully (Turn 2 rejection handled)
✅ Agent Passthrough Mode implementation is sound (verified with test)
✅ Conversation history preservation working

### What Doesn't Work
❌ Agents don't discover/use new capabilities autonomously
❌ Cannot fulfill task requirements (latest versions, actual builds, testing)
❌ Passthrough mode exists but remains unused
❌ Task will fail execution (build script won't run, versions may be wrong)

### Severity

**BLOCKER** - The implementation is technically correct, but behaviorally ineffective.

- **Technical Layer:** ✅ Working (policy, executor, sandbox all functional)
- **Agent Adoption Layer:** ❌ Broken (agents don't know about/use the capability)
- **Task Fulfillment:** ❌ Failed (cannot get latest versions or build images)

---

## Recommendations

### Immediate Actions

**Option A: Explicit Task Directive**
Update task to explicitly instruct:
```markdown
Use agent.passthrough_shell to:
- Execute curl commands to fetch latest versions
- Run docker build commands to create images
- Test images with GPU access verification
```

**Option B: Inject Passthrough Examples**
Add example plans showing passthrough usage so agents learn the pattern.

**Option C: Enhance Agent Prompt**
If possible, modify agent system message to highlight passthrough_shell as preferred method for:
- Web searches (curl/wget)
- Docker builds
- Command execution
- Testing

**Option D: Policy Hints**
Add "hint" field to policy actions:
```yaml
- type: agent.passthrough_shell
  params: [cmd]
  hint: "Use this for web searches (curl), docker builds, and command execution"
```

### Long-Term Solutions

1. **Agent Capability Discovery**
   - Implement mechanism for agents to query available actions
   - Provide action descriptions in agent context
   - Show examples of each action type

2. **Smart Defaults**
   - When task mentions "web search" → suggest passthrough_shell + curl
   - When task mentions "docker build" → suggest passthrough_shell + docker
   - When task mentions "test" → suggest passthrough_shell + test commands

3. **Retrospective Learning**
   - After execution, if build fails, agent learns passthrough was needed
   - Feed successful passthrough plans back as examples

4. **Prompt Engineering**
   - Update task templates to guide capability usage
   - Add "Available Tools" section listing passthrough + use cases

---

## Test Conclusion

**Test ID:** passthrough-dfl-001
**Status:** ❌ FAILED (Technical Success, Adoption Failure)
**Duration:** 12 minutes (deliberation only, no execution attempted)

### What Was Proven
- ✅ Agent Passthrough Mode implementation works (verified with separate test)
- ✅ Sandbox operates correctly (GPU access, RO mounts, network)
- ✅ Policy and executor handle passthrough actions properly

### What Was Discovered
- ❌ Agents DO NOT autonomously discover new capabilities
- ❌ Passthrough mode exists but agents never tried to use it
- ❌ Task requirements cannot be fulfilled without explicit guidance

### Critical Insight

**"If you build it, they won't necessarily come."**

Adding a capability to the system is necessary but not sufficient. Agents need:
1. **Awareness** - Know the capability exists
2. **Understanding** - Know when/how to use it
3. **Examples** - See it demonstrated
4. **Guidance** - Task prompts that suggest usage

Without these, even perfect implementations remain unused.

---

## Next Steps

1. **Update task file** - Add explicit passthrough_shell instructions
2. **Create example plans** - Demonstrate passthrough usage patterns
3. **Retry deliberation** - Test if explicit guidance helps adoption
4. **Measure improvement** - Count passthrough actions in new plan
5. **Document findings** - Update agent prompting best practices

**Test will be marked INCOMPLETE until agent adoption is achieved.**

---

**Files Referenced:**
- Task: tasks/build_dfl_docker_rtx4090.md
- Policy: configs/policy.yaml (lines 103-126)
- Executor: src/orchestrator/cycle.py (lines 86-148)
- Hunt Plan: plans/hunt_plan.json
- Reviewed Plan: plans/reviewed_plan.json
- Conversation: reports/deliberations/20251029_104800/
- This Report: docs/DFL_BUILD_MONITORING_PASSTHROUGH_TEST.md

