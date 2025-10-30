# Planning vs Execution Bias in AI Agents

## The Problem

**User expectation**: "Build Docker images" → agent builds images
**What happened**: "Build Docker images" → agent writes 500-line plan document

## Root Cause: Planning Mode Default

AI agents (especially LLM-based ones) are trained on:
- Documentation
- Tutorials
- Stack Overflow answers
- Technical writing

This creates a **strong bias toward explaining HOW instead of DOING**.

### Example from Today's Test

**Task**: "Build RTX 4090 Compatible DeepFaceLab Docker Images"

**Agent's interpretation**:
1. ✅ Understood requirements
2. ✅ Researched CUDA/TensorFlow compatibility
3. ✅ Designed comprehensive solution
4. ❌ **Stopped at writing documentation instead of building**

**Agent output**:
- Dockerfile.tf2.15.cu118 template
- Dockerfile.tf1.15.cu118 template
- docker-compose.yml template
- entrypoint.sh template
- Full build instructions
- **ZERO actual Docker images**

## Why This Happens

### Training Distribution

LLMs see FAR more examples of:
```
"Here's how to build a Docker image:
Step 1: Create a Dockerfile...
Step 2: Run docker build...
```

Than examples of:
```
$ docker build -t myimage .
[actual build output]
```

### Risk Aversion

Planning = safe. Agent can't "break" anything by writing documentation.
Execution = risky. Commands might fail, system might be in unknown state.

### Approval Seeking

Agent thinks: "Let me show the human my plan so they can approve before I execute."

This is EXACTLY what Direct-Action mode aims to eliminate, but the bias persists.

## Solutions

### 1. Explicit Execution Framing

**Weak**: "Build Docker images"
**Strong**: "EXECUTE these steps (don't just describe them):"

**Weak**: "Create Dockerfile and build image"
**Strong**: "Writing plans is FAILURE. Building images is SUCCESS."

### 2. Anti-Planning Instructions

Add explicit rejection of planning mode:
- "DO NOT write READMEs"
- "DO NOT create templates"
- "DO NOT explain steps - execute them"

### 3. Success Criteria as Artifacts

**Weak**: "Complete the task"
**Strong**: "Only signal DONE when `docker images` shows dfl:rtx4090"

### 4. Execution Examples in Prompt

Show the agent what execution looks like:
```
GOOD:
$ mkdir /workspace/build
$ echo "FROM alpine" > /workspace/build/Dockerfile
$ docker build -t test /workspace/build
Successfully built abc123

BAD:
"First, you should create a Dockerfile with the following contents..."
```

## Test Results

### Test 1: Ambiguous Task
**Task**: "Build RTX 4090 Compatible DeepFaceLab Docker Images"
**Result**: 500-line plan document, 0 images

### Test 2: Explicit Execution (Running Now)
**Task**: "Build DFL Docker Image - EXECUTE, DON'T JUST PLAN"
**Instructions**:
- "DO NOT write plans, READMEs, or documentation"
- "DO actually build working Docker images"
- "Writing a plan is FAILURE. Building an image is SUCCESS."

**Result**: TBD - testing now

## Implications for Freedom Mode

This reveals a **hidden approval gate**:
- No *human* approval gate ✅
- No *code* approval gate ✅
- But **implicit self-approval gate** where agent stops after planning ❌

True freedom mode requires:
1. Extended thinking time (we fixed this: 2 min → 15 min)
2. Explicit execution framing (testing now)
3. Rejection of planning-only outputs

## The Philosophical Question

Is "planning without execution" actually **safer** for the user?

**Traditional view**: Yes - user can review plan before execution
**Freedom Mode view**: No - planning creates dependency and slows iteration

The whole point of giving agents terminal access is to let them EXECUTE, not to get better plans.

## Recommendation

For all Direct-Action mode tasks:

1. **Frame as execution**: "Execute these steps" not "Complete this task"
2. **Define success concretely**: "File X exists" not "Task complete"
3. **Reject planning explicitly**: "Don't write docs" not just implied
4. **Show execution examples**: Demonstrate what good output looks like

## Next Steps

1. ✅ Created execution-focused task (dfl_build_EXECUTE_NOT_PLAN.md)
2. ⏳ Testing if explicit framing overcomes planning bias
3. 📋 TODO: Add execution mode flag to direct_run.py
4. 📋 TODO: Collect corpus of execution examples for prompt library

---

**Date**: 2025-10-29
**Insight**: User identified that agent created plans instead of building
**Status**: Testing if explicit execution framing solves this

**Agents must execute, not just explain.**
