# AAv3 REAL Demonstration

Task: Build optimal Python FastAPI server with auth

## REAL Agent Workflow

### Agent 1: PLANNER
Role: Strategic planning
Reasoning: Break down task, identify unknowns

**Planner thinks**:
- Need to choose auth method (JWT, OAuth, session)
- Should we web search for best practices?
- FastAPI has built-in security
- Let me propose approach

**Planner posts**: "Propose JWT auth with FastAPI's security utilities, modern pattern for 2025"

---

### Agent 2: RESEARCHER
Role: Validate with research
Tool: WebSearch

**Researcher thinks**:
- Let me verify JWT is still best practice
- Check for security concerns
- Find optimal implementation

**Researcher uses**: WebSearch("FastAPI JWT auth best practices 2025")

**Researcher posts**: "Confirmed - JWT with httpOnly cookies recommended. Python-jose library optimal."

---

### Agent 3: CODER
Role: Implementation
Tools: Write, Edit

**Coder thinks**:
- Create main.py with FastAPI
- Implement JWT utilities
- Add auth endpoints

**Coder uses**: Write(main.py, <FastAPI code>)

**Coder posts**: "Created main.py with JWT auth, /login and /protected endpoints"

---

### Agent 4: REVIEWER
Role: Quality check
Tools: Read

**Reviewer thinks**:
- Check security best practices
- Verify error handling
- Suggest improvements

**Reviewer uses**: Read(main.py)

**Reviewer posts**: "Good foundation. Suggestions: Add rate limiting, use proper password hashing (bcrypt), add CORS"

---

### Agent 5: TESTER
Role: Validation
Tools: Bash

**Tester thinks**:
- Install dependencies
- Run server
- Test endpoints

**Tester uses**: Bash("pip install fastapi python-jose && uvicorn main:app")

**Tester posts**: "Server starts successfully. Auth endpoints working. Tests passed."

---

### ALL AGENTS: CONSENSUS

**Vote on completion**:
- Planner: approve (architecture sound)
- Researcher: approve (matches best practices)
- Coder: approve (implementation complete)
- Reviewer: approve (quality sufficient)
- Tester: approve (all tests passed)

**Consensus: 5/5 = 100%**

**Decision**: Task complete ✓

## Key Differences from Simulation

**Simulation (what AAv3 prototype does)**:
```python
# Hardcoded response
plan = "Propose JWT auth..."
```

**Real (what production AAv3 will do)**:
```python
# Orchestrator presents role prompt to me
Orchestrator: "You are PLANNER. Task: Build FastAPI with auth. Propose approach."
  ↓
Claude Code (me as planner): "I propose JWT because..."
  ↓
Orchestrator captures response → Shared memory
```

The architecture is ready. Just needs the orchestrator to present role prompts to me instead of hardcoding responses.
