# Deliberation Drop-In Patch

Adds:
- `configs/deliberation.yaml` (turns/roles/paths)
- `src/agents/agent_wrapper.py` (transcript + agent-call stubs)
- `scripts/deliberate.py` (conversation loop → writes plans/*.json)
- `tasks/sample_kpop_interviews.md` (example brief)

Usage:
1) Merge this patch into your repo root (folders align with existing structure).
2) Implement in `src/agents/agent_wrapper.py`:
   - `call_proposer(...)` → invoke Claude Code CLI/API, return plan dict
   - `call_critic(...)`   → invoke Codex CLI/API, return {approved,reasons,plan}
3) Run a deliberation:
   ```
   python scripts/deliberate.py --task tasks/sample_kpop_interviews.md
   ```
4) Execute the approved plan with your existing orchestrator (it already loads plans/reviewed_plan.json).
