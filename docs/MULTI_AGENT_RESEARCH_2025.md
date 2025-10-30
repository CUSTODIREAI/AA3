# Multi-Agent LLM Systems Research - 2025 State-of-Art

**Date**: 2025-10-29
**Purpose**: Research findings on how multiple LLM agents collaborate to build systems and write code

---

## Executive Summary

Multi-agent LLM systems represent the current frontier in agentic AI (2025). Key breakthrough: **90.2% improvement** achieved by Anthropic using orchestrator-worker pattern with multiple Claude instances.

**Critical insight**: "Token usage by itself explains 80% of the variance" in performance. Distributing work across separate context windows is the architectural breakthrough.

---

## 1. Anthropic's Multi-Agent Research System

### Architecture: Orchestrator-Worker Pattern

```
Lead Agent (Claude Opus 4)
    ├─> Subagent 1 (Claude Sonnet 4) [Parallel]
    ├─> Subagent 2 (Claude Sonnet 4) [Parallel]
    └─> Subagent 3 (Claude Sonnet 4) [Parallel]
```

### How It Works

1. **Lead Agent**: Analyzes query, develops strategy, spawns subagents
2. **Subagents**: Execute specific tasks independently, return findings
3. **Synthesis**: Lead agent combines results, decides if more research needed
4. **Persistence**: Plans saved to external memory to maintain context

### Performance Results

- **90.2% improvement** over single-agent Claude Opus 4
- **90% time reduction** for complex queries via parallel execution
- Token efficiency: separate context windows prevent token bloat
- Cost: ~15x more tokens than single agent (justified for complex tasks)

### Communication Pattern

- **Synchronous execution**: Lead waits for subagents to complete
- **Detailed task descriptions**: Objectives, output formats, tool guidance, boundaries
- **Scaled effort**: Simple queries (1 agent), complex queries (10+ subagents)
- **Parallel tool calling**: 3-5 subagents spawned simultaneously

### Error Handling

- Resume from failure point (no full restarts)
- Model intelligence handles issues gracefully
- Tool failure notifications allow adaptation
- Rainbow deployments prevent disrupting running agents

### Key Lessons

1. **Prompt engineering is paramount**: Primary lever for behavior improvement
2. **Token efficiency matters most**: 80% of performance variance
3. **Tool design is critical**: Poor descriptions send agents down wrong paths
4. **Cost-benefit required**: 15x token cost requires high-value tasks
5. **Observability enables debugging**: Full tracing essential for non-deterministic agents
6. **Start evaluation early**: 20 queries often reveal impact clearly

---

## 2. MetaGPT: Multi-Agent Software Development

### Architecture: Assembly Line with SOPs

```
Product Manager → Architect → Project Manager → Engineer → QA Engineer
     ↓              ↓              ↓               ↓           ↓
Requirements   Design        Timeline         Code       Test Report
   Doc       Artifacts                      + Tests
```

### Core Philosophy

**Code = SOP(Team)**

Standardized Operating Procedures (SOPs) encoded into prompt sequences for streamlined workflows.

### Key Innovation: Structured Communication

**Problem**: Unproductive chatter between agents wastes tokens, introduces errors

**Solution**: Agents generate **structured outputs** (documents, diagrams) instead of chat messages

- Product Manager → Requirements document
- Architect → Design artifacts, flowcharts, interface specs
- Engineer → Code with tests
- QA Engineer → Test report with verification
- Reviewer → Feedback document

### Benefits

- Human-like domain expertise built into agent roles
- Intermediate results verified at each stage
- Code review built-in (missing in AutoGPT)
- Precompilation execution for early error detection
- Systematic decomposition of requirements

### vs AutoGPT

AutoGPT lacks systematic requirement decomposition. MetaGPT simplifies transforming abstract requirements into detailed designs through specialized division of labor.

---

## 3. Common Multi-Agent Patterns (2025)

### Pattern 1: Executor-Verifier-Reviewer

```
Planner → Analyzes task, creates execution plan
    ↓
Executor → Runs commands, builds artifacts
    ↓
Verifier → Tests outputs, validates against criteria
    ↓
Reviewer → Provides feedback, suggests fixes
    ↓
[Loop back to Executor if issues]
```

**Used by**: ACT (Agent-Coder-Tester), MANTRA, Audit-LLM

**Roles**:
- **Executor**: Performs actions (fetch data, write code, build images)
- **Verifier/Tester**: Validates outputs, runs tests, checks criteria
- **Reviewer**: Evaluates quality, provides improvement feedback

### Pattern 2: Reflection (Self-Correction)

Agent evaluates its own work before finalizing:

```
1. Generate output
2. Self-critique: "What could be wrong?"
3. Identify errors, gaps, inefficiencies
4. Refine and improve
5. Repeat until quality threshold met
```

**Used by**: GitHub Copilot, AgentRefine

**Example**: Copilot generates code → runs in sandbox → identifies bugs → fixes → repeats

### Pattern 3: Plan-and-Execute

```
Planner Agent → Creates strategy
    ↓
Executor Agents → Carry out subtasks
    ↓
Synthesizer → Combines results
```

Subtasks not pre-defined but determined dynamically based on input.

### Pattern 4: Evaluator-Optimizer

```
Generator LLM → Produces initial output
    ↓
Reviewer LLM → Evaluates against criteria, provides feedback
    ↓
Generator LLM → Refines based on feedback
    ↓
[Iterate until quality threshold]
```

### Pattern 5: Evidence-Based Multi-Agent Debate (EMAD)

```
Executor 1 → Independent analysis
Executor 2 → Independent analysis
    ↓
Debate → Exchange reasoning, refine conclusions
    ↓
Consensus → Agreed solution
```

Reduces hallucinations through cross-validation (40% accuracy improvement).

---

## 4. Best Practices from Anthropic

### When to Use Multiple Agents vs Single Agent

**Start simple**: Optimize single LLM calls first

**Use multi-agent when**:
- Open-ended problems with unpredictable steps
- Fixed workflows cannot hardcode solution
- Flexibility and model-driven decisions essential
- Task complexity justifies 15x token cost

### Agent Collaboration Principles

1. **Orchestrator-workers**: Central LLM delegates unpredictable subtasks
2. **Evaluator-optimizer**: One generates, another provides iterative feedback
3. **Parallelization**: Multiple agents on sectioned subtasks simultaneously
4. **Dynamic task breakdown**: Orchestrator determines subtasks based on input

### Error Handling

- **Environmental feedback**: Agents gain "ground truth" at each step
- **Stopping conditions**: Maximum iteration limits maintain control
- **Human checkpoints**: Pause for feedback when encountering blockers
- **Sandboxed testing**: Extensive testing before production

### Verification and Quality Control

- **Tool documentation as defense**: Invest heavily in agent-computer interfaces (ACI)
- **Poka-yoke principles**: Design arguments to make errors harder
- **Measurement-driven iteration**: Add complexity only when it improves outcomes
- **Human oversight**: Maintain meaningful review for high-stakes decisions
- **Automated tests**: Verify functionality
- **Human review**: Ensure alignment with broader system requirements

### Production Considerations

- **Observability**: Full tracing for debugging non-deterministic agents
- **Resume capability**: Systems that resume from error points (not restart)
- **Rainbow deployments**: Gradual traffic shifting prevents disruption
- **Cost monitoring**: 15x token usage requires ROI justification

---

## 5. Framework Landscape (2025)

### LangGraph
Most sophisticated for building stateful, multi-agent applications

### AutoGen
Conversational multi-agent systems with natural language dialogue

### CrewAI
Creating "crews" of AI agents with defined roles

### Swarm
Minimalist approach with routine-based agent definitions

### MetaGPT
Software development with SOP-based workflows

---

## 6. Research Activity (2025)

- **AAAI 2025 Workshop**: Multi-agent collaboration (March 4, Philadelphia)
- **ArXiv papers**: 2501.06322 (collaboration mechanisms), 2505.23946 (lessons learned)
- **Applications**: 5G/6G networks, Industry 5.0, question answering, social/cultural settings
- **Benchmarks**: HumanEval, MBPP for code generation evaluation

---

## 7. Challenges and Limitations

### Technical Challenges
- **Resource intensive**: Astronomical compute requirements
- **Inference costs**: Balloon with concurrent requests
- **Coordination complexity**: Agent coordination, evaluation, reliability
- **Response latency**: Increases with agent communication
- **Cost scaling**: More LLMs = higher operational cost

### Addressed Through
- Load-balancing across multiple LLM providers
- Sophisticated orchestration logic
- Structured outputs (reduce chat overhead)
- Parallel execution (reduce wall-clock time)

---

## 8. Application to Custodire AA System

### Current State (AAv1)
```
Task file → Claude parses EXECUTE: → Runs commands → Done
```

**Strengths**:
- Deterministic execution (no LLM interpretation of commands)
- 100% success rate on DFL Docker build

**Missing**:
- Verification loops
- Reflection/self-correction
- Error recovery with diagnosis
- Parallel execution

### Proposed Architecture (AAv2): Orchestrator Pattern

```
┌─────────────────────────────────────────────────┐
│           Orchestrator (Claude)                 │
│  - Reads task                                   │
│  - Spawns specialized agents                    │
│  - Synthesizes results                          │
│  - Manages execution flow                       │
└────────┬────────────────────────────────────────┘
         │
         ├─────────────┬─────────────┬─────────────┐
         │             │             │             │
┌────────▼──────┐ ┌────▼──────┐ ┌───▼──────┐ ┌───▼──────┐
│   Executor    │ │ Verifier  │ │ Reviewer │ │ Fixer    │
│   (Claude)    │ │ (Claude)  │ │ (Codex)  │ │ (Claude) │
│               │ │           │ │          │ │          │
│ Runs commands │ │ Tests     │ │ Diagnoses│ │ Applies  │
│ Builds images │ │ Validates │ │ Suggests │ │ Fixes    │
│ Creates files │ │ Criteria  │ │ Improves │ │ Retries  │
└───────────────┘ └───────────┘ └──────────┘ └──────────┘
```

### Phase 1: Parallel Execution
- Spawn parallel Claude executors with separate context windows
- 80% token efficiency gain (Anthropic proven)
- Commands with no dependencies run simultaneously

### Phase 2: Verification Loop
- Structured execution transcript (artifact, not chat)
- Claude verifier checks SUCCESS_CRITERIA
- Verification report generated before DONE

### Phase 3: Diagnosis & Review
- If failures: Codex reviewer analyzes transcript
- Produces structured diagnosis document
- Suggests specific fixes with reasoning

### Phase 4: Self-Correction
- Claude executor applies fixes from diagnosis
- Reflection step before each command: "Could this fail?"
- Proposes alternatives if self-critique finds issues
- Verifies after fix application

### Phase 5: Synthesis
- Orchestrator collects all agent outputs
- Determines if task complete
- Decides if additional iterations needed
- Produces final summary report

---

## 9. Key Metrics to Track (AAv2)

### Performance
- Task completion rate (target: maintain 100%)
- Commands executed vs planned
- Parallel execution time savings
- Token usage vs AAv1

### Quality
- First-attempt success rate
- Fixes required per task
- Self-correction effectiveness
- Verification pass rate

### Reliability
- Error recovery success rate
- Manual intervention required (target: 0)
- Diagnosis accuracy
- Fix application success

---

## 10. Implementation Priorities

### Priority 1: Orchestrator Core
- Task decomposition
- Agent spawning
- Result synthesis

### Priority 2: Structured Artifacts
- Execution transcripts (JSON)
- Verification reports
- Diagnosis documents
- Fix proposals

### Priority 3: Parallel Execution
- Dependency analysis
- Concurrent executor spawning
- Result collection

### Priority 4: Verification Loop
- Criteria checking
- Artifact validation
- Quality gates

### Priority 5: Reflection Pattern
- Self-critique before commands
- Alternative proposal
- Pre-execution validation

---

## References

- Anthropic Engineering: Multi-Agent Research System (2025)
- Anthropic Research: Building Effective Agents (2025)
- MetaGPT: Meta Programming for Multi-Agent Framework (arXiv 2308.00352v6)
- Multi-Agent LLM Collaboration Survey (arXiv 2501.06322)
- Lessons Learned: Multi-Agent Code LLMs (arXiv 2505.23946)
- AAAI 2025 Workshop on Multi-Agent Collaboration
- Collabnix: Multi-Agent Architecture Guide 2025
- ACM TOSEM: LLM-Based Multi-Agent Systems for Software Engineering

---

**Conclusion**: The future of agentic AI is collaborative. Single-agent systems hit context limits and complexity ceilings. Multi-agent orchestrator patterns with structured communication, parallel execution, and verification loops represent the proven path forward.

**Evidence**: Anthropic achieved 90.2% improvement. MetaGPT produces higher-quality code than AutoGPT. Industry consensus: orchestrator-worker + structured artifacts + verification = production-ready agentic systems.

**Next Step**: Implement AAv2 with these patterns for Custodire system.
