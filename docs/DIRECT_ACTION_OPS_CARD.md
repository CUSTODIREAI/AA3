# Direct-Action Mode — Ops Card

**What it is:** Agents act like terminal engineers inside a GPU sandbox. No plan/approval loops; post-hoc audit only. Evidence stays immutable; dataset changes only via `ingest.promote(_glob)` (append-only + SHA-256 manifest).

## Quick Start

```bash
# Ensure sandbox (with GPUs & RO/RW mounts)
bash scripts/start_agent_sandbox.sh

# Run a task directly (no planning gates)
python scripts/direct_run.py tasks/build_dfl_docker_rtx4090.md

# Watch audit trail
tail -f reports/ledger.jsonl | grep direct
```

**Expected turn pattern:** curl → docker build → nvidia-smi / framework checks → docker run tests → "DONE". Artifacts promoted from `/staging/…` to `dataset/YYYY/MM/DD/...` with a new manifest line.

## Guarantees (Safety Model)

* `dataset/`, `evidence/`, `staging-final/` = **read-only** mounts → agents cannot modify/delete.
* Dataset changes = **append-only** via `ingest.promote(_glob)` (copy + SHA-256 + manifest). No remove API.
* No host Docker socket in sandbox → agents can't prune/uninstall host.
* All commands logged to `reports/ledger.jsonl`.

## KPI Targets

* First run completes in **≤ 5–10 commands** and **≤ 5 minutes** (vs 10–15 min deliberation).
* Evidence files created: `/workspace/versions.json`, `/workspace/build.log`, `/workspace/gpu_info.txt`.
* At least one **artifact promoted** to dataset with manifest entry.

## Post-Hoc Review

```bash
# Check session results
python scripts/post_hoc_critic.py --session <session-id>

# Or review latest session
python scripts/post_hoc_critic.py --latest
```

**Flags:**
- ❌ Failed commands (exit code != 0)
- ❌ Missing evidence files
- ❌ No artifacts promoted
- ❌ Session exceeded budget without completion
- ⚠️  High command failure rate (>30%)
- ⚠️  No GPU usage detected

## If Something Misbehaves

* **Agent stalls** → bump `--budget` (turns), or refine the system prompt to "return one bash command only."
* **No outputs** → check `/workspace/` and `/staging/` via `docker exec agent-sandbox ls -la …`.
* **Access errors** → re-verify mounts (`touch /dataset/.t` must fail; `touch /workspace/.t` must succeed).
* **GPU fail** → `docker exec agent-sandbox nvidia-smi`. If not present, confirm NVIDIA toolkit/runtime on host.
* **Sandbox not running** → `bash scripts/start_agent_sandbox.sh`

## When to fall back to Deliberation

* Production-critical operations where pre-approval is mandatory.
* Tasks that materially benefit from a formal plan (multi-party coordination, compliance reviews).
* Otherwise, **Default to Direct-Action** for speed and freshness.

## Verification Checklist

```bash
# 1. Verify sandbox is running with correct mounts
bash scripts/verify_sandbox.sh

# 2. Test RO mounts (should fail)
docker exec agent-sandbox touch /dataset/.test
# Expected: touch: cannot touch '/dataset/.test': Read-only file system

# 3. Test RW mounts (should succeed)
docker exec agent-sandbox touch /workspace/.test && docker exec agent-sandbox rm /workspace/.test
# Expected: Success (no output)

# 4. Test GPU access
docker exec agent-sandbox nvidia-smi
# Expected: RTX 4090 detected

# 5. Run minimal test
python scripts/direct_run.py tasks/minimal_test.md --budget 5
# Expected: Completes in <2 minutes
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  User                                                   │
│    ↓                                                    │
│  python scripts/direct_run.py tasks/my_task.md         │
│    ↓                                                    │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Direct-Action Loop (autonomy_budget = 15)       │  │
│  │                                                  │  │
│  │  1. agent_next_command(task, history)           │  │
│  │     └─> Codex/Claude returns: "curl ..." or     │  │
│  │         "docker build ..." (single bash line)   │  │
│  │                                                  │  │
│  │  2. run_passthrough(cmd)                        │  │
│  │     └─> docker exec agent-sandbox bash -c cmd   │  │
│  │                                                  │  │
│  │  3. log(kind="direct_cmd", ...)                 │  │
│  │     └─> Append to reports/ledger.jsonl          │  │
│  │                                                  │  │
│  │  4. Check for "DONE" or evidence files          │  │
│  │                                                  │  │
│  │  Loop until done or budget exhausted            │  │
│  └──────────────────────────────────────────────────┘  │
│    ↓                                                    │
│  Post-execution: ingest_glob("staging/**/*")           │
│    ↓                                                    │
│  Artifacts → dataset/ (append-only + SHA-256)          │
└─────────────────────────────────────────────────────────┘
```

## Comparison: Deliberation vs Direct-Action

| Metric | Deliberation | Direct-Action |
|--------|--------------|---------------|
| **Time** | 10-15 min | 2-5 min |
| **Turns** | 3-5 planning | 5-10 commands |
| **Pre-approval** | Required | None |
| **Evidence** | Hypothetical plan | Real outputs |
| **Flexibility** | Action schema | Any bash command |
| **Safety** | Pre-veto | Post-audit |
| **Use Case** | High-risk prod | Dev/research |

## Files Reference

**Core:**
- `scripts/direct_run.py` - Main executor
- `scripts/start_agent_sandbox.sh` - Sandbox setup
- `scripts/post_hoc_critic.py` - Post-execution review
- `scripts/verify_sandbox.sh` - Verification helper

**Config:**
- `configs/deliberation.yaml` - Mode toggle (direct vs deliberate)

**Docs:**
- `docs/DIRECT_ACTION_MODE.md` - Full documentation
- `docs/AI2AI.md` - Lessons learned + GPU Wildbox vision
- `docs/AGENT_ADOPTION_FIX_SUMMARY.md` - Adoption fix KPIs

**Logs:**
- `reports/ledger.jsonl` - Audit trail (all commands + results)
- `workspace/` - Agent working directory (evidence files)
- `staging/` - Files ready for promotion

---

**Status:** ✅ Production-ready
**Last Updated:** 2025-10-29
**Maintainer:** Claude (Sonnet 4.5) + User
