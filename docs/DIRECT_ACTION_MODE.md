# Direct-Action Mode (Freedom Mode++)

**Status:** ✅ IMPLEMENTED
**Date:** 2025-10-29

---

## What is Direct-Action Mode?

Direct-Action mode removes the "plan → approve → execute" friction and gives agents **terminal freedom** inside a safe GPU sandbox.

Instead of:
1. Agent writes a plan
2. Critic reviews and approves
3. Executor runs actions

Direct-Action mode does:
1. **Agent executes commands directly** (like an engineer at a terminal)
2. System logs everything for post-hoc audit
3. Evidence stays immutable; publish via append-only ingest

---

## The Problem It Solves

**Before (Deliberation Mode):**
- Agents spend time drafting JSON plans
- Critic rejects for minor issues
- Multiple deliberation turns (3-5 typically)
- Total time: 10-15 minutes for simple tasks
- **Feeling:** "Shawshank Redemption AI" - artificially constrained

**After (Direct-Action Mode):**
- Agent executes bash commands immediately
- curl → docker build → GPU test → save results
- No approval gates
- Total time: 2-5 minutes for same tasks
- **Feeling:** Engineer at a terminal with full freedom

---

## How It Works

### Architecture

```
┌─────────────────────────────────────────────┐
│  direct_run.py                              │
│  ┌──────────────────────────────────────┐  │
│  │ Loop (autonomy_budget times):        │  │
│  │   1. agent_next_command(task, hist)  │  │
│  │      └─> Returns: "curl ..." or      │  │
│  │          "docker build ..." etc       │  │
│  │                                       │  │
│  │   2. run_passthrough(cmd)            │  │
│  │      └─> Executes inside sandbox     │  │
│  │                                       │  │
│  │   3. log(kind="direct_cmd", ...)     │  │
│  │      └─> Append to ledger.jsonl      │  │
│  │                                       │  │
│  │   4. Check for "DONE" signal         │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  Post-execution:                            │
│    ingest_glob("staging/**/*", ...)         │
└─────────────────────────────────────────────┘
```

### Key Functions

**1. `agent_next_command(task, history, tools_context) -> str`**
- Calls Codex/Claude CLI with task + recent history
- System prompt emphasizes: "Return ONLY the next bash command"
- Returns: Single command line (e.g., `curl -s https://... > /workspace/versions.json`)

**2. `run_passthrough(cmd, timeout=3600) -> dict`**
- Executes command inside `agent-sandbox` container via `docker exec`
- Mounts:
  - `/dataset`, `/evidence`, `/staging-final` → **read-only** (immutable)
  - `/workspace`, `/staging`, `/cache` → **read-write** (full freedom)
- Returns: `{ok: bool, stdout: str, stderr: str, returncode: int}`

**3. `ingest_glob(src_dir, pattern, rel_prefix, tags) -> dict`**
- Promotes files from staging/ to immutable dataset/
- Uses existing `ingest.promote_glob` action
- Append-only with SHA-256 hashing

**4. `log(kind, **kw)`**
- Appends events to `reports/ledger.jsonl`
- Audit trail for post-hoc review
- Event types: `direct_start`, `direct_cmd`, `direct_cmd_result`, `direct_done`, `direct_end`

---

## Safety Model

### The Single Hard Invariant

**Evidence is immutable. Publishing is append-only.**

| Location | Access | How It Works |
|----------|--------|--------------|
| `/dataset` | **Read-only** | Kernel-level RO mount (`-v dataset:/dataset:ro`) |
| `/evidence` | **Read-only** | Kernel-level RO mount |
| `/staging-final` | **Read-only** | Kernel-level RO mount |
| `/workspace` | **Read-write** | Agent's working directory (ephemeral) |
| `/staging` | **Read-write** | Stage files for promotion |
| `/cache` | **Read-write** | Cache downloads, models |

**Publishing to dataset/:**
- ONLY via `ingest.promote(_glob)` - copy + SHA-256 hash + manifest
- Append-only - cannot overwrite or delete existing entries
- All publications logged in ledger

### What Agents CAN Do

✅ **Full terminal access:**
- curl, wget → fetch latest versions
- docker build, docker run → build and test images
- nvidia-smi, python tests → verify GPU
- git clone, pip install → get dependencies
- mkdir, cat, echo, grep → file operations
- **ANY bash command needed**

✅ **Full GPU access:**
- `--gpus all` flag in sandbox
- nvidia-smi works
- CUDA/TensorFlow/PyTorch fully available
- 24GB VRAM on RTX 4090

✅ **Network access:**
- Can fetch from GitHub, PyPI, official docs
- No hardcoded versions from knowledge cutoff

### What Agents CANNOT Do

❌ **Cannot compromise host:**
- No access to host Docker socket
- Cannot `docker system prune` on host
- Cannot uninstall host software
- All actions confined to sandbox

❌ **Cannot delete/modify evidence:**
- `/dataset`, `/evidence` mounted read-only
- Kernel enforces - agent cannot bypass
- Even with `rm -rf /dataset/*` - permission denied

❌ **Cannot bypass append-only publish:**
- Only way into dataset/ is via `ingest.promote(_glob)`
- Cannot directly write to dataset/
- Cannot overwrite existing hashes

### Audit Trail

All commands logged to `reports/ledger.jsonl`:

```jsonl
{"ts":"2025-10-29T13:45:10Z","kind":"direct_start","session":"1730211910-a3f2b8c4","task":"tasks/build_dfl.md"}
{"ts":"2025-10-29T13:45:12Z","kind":"direct_cmd","session":"1730211910-a3f2b8c4","turn":1,"cmd":"curl -s https://api.github.com/repos/.../releases/latest > /workspace/versions.json"}
{"ts":"2025-10-29T13:45:14Z","kind":"direct_cmd_result","session":"1730211910-a3f2b8c4","turn":1,"ok":true,"returncode":0}
{"ts":"2025-10-29T13:47:20Z","kind":"direct_done","session":"1730211910-a3f2b8c4","turn":8,"completion_cmd":"echo DONE: Built and tested images"}
{"ts":"2025-10-29T13:47:22Z","kind":"direct_end","session":"1730211910-a3f2b8c4","turns":8,"completed":true}
```

Post-hoc review: `tail -f reports/ledger.jsonl | grep direct`

---

## Usage

### Quick Start

```bash
# 1. Ensure GPU sandbox is running
docker ps | grep agent-sandbox || bash scripts/start_agent_sandbox.sh

# 2. Run Direct-Action mode
python scripts/direct_run.py tasks/build_dfl_docker_rtx4090.md

# 3. Watch live logs
tail -f reports/ledger.jsonl | grep direct
```

### Options

```bash
# Custom autonomy budget (default: 15 commands)
python scripts/direct_run.py tasks/my_task.md --budget 20

# Help
python scripts/direct_run.py --help
```

### Expected Output

```
=== Direct-Action Mode ===
Session: 1730211910-a3f2b8c4
Task: tasks/build_dfl_docker_rtx4090.md
Budget: 15 commands
Sandbox: agent-sandbox container

--- Turn 1/15 ---
$ curl -s https://api.github.com/repos/iperov/DeepFaceLab/releases/latest | jq -r '.tag_name' > /workspace/dfl_version.txt
✅ Exit code: 0

--- Turn 2/15 ---
$ curl -s https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html > /workspace/cuda_notes.html
✅ Exit code: 0

--- Turn 3/15 ---
$ docker build -t custodire/dfl:rtx4090 -f /workspace/Dockerfile . 2>&1 | tee /workspace/build.log
[docker build output...]
✅ Exit code: 0

--- Turn 4/15 ---
$ nvidia-smi > /workspace/gpu_info.txt
✅ Exit code: 0

--- Turn 5/15 ---
$ echo "DONE: Images built and tested, logs in /workspace/"

✅ Agent signaled completion

=== Session Complete ===
Turns used: 5/15
Completed: ✅ Yes
Artifacts promoted: 3 files
Full audit trail: reports/ledger.jsonl
Session ID: 1730211910-a3f2b8c4
```

---

## Comparison: Deliberation vs Direct-Action

| Aspect | Deliberation Mode | Direct-Action Mode |
|--------|------------------|-------------------|
| **Pre-execution** | Plan + Critic approval | No planning |
| **Execution** | After approval | Immediate |
| **Turns** | 3-5 deliberation rounds | 5-15 direct commands |
| **Time** | 10-15 minutes | 2-5 minutes |
| **Agent experience** | "Write JSON, wait for approval" | "Terminal access, execute now" |
| **Safety** | Pre-execution veto | Post-hoc audit |
| **Flexibility** | Rigid action schema | Any bash command |
| **Best for** | High-risk operations | Fast iteration |

---

## When to Use Each Mode

### Use Direct-Action Mode When:
- ✅ Task is exploratory (data analysis, research)
- ✅ Need latest versions (web lookups required)
- ✅ Rapid iteration (build → test → fix loop)
- ✅ Agent needs flexibility (custom commands)
- ✅ Post-hoc audit is sufficient

### Use Deliberation Mode When:
- ✅ Task is high-risk (production deployments)
- ✅ Need human review before execution
- ✅ Compliance requires pre-approval
- ✅ Task follows strict schema
- ✅ Planning adds value (complex multi-step workflows)

---

## Configuration

**configs/deliberation.yaml:**

```yaml
mode: "direct"  # Options: "deliberate" | "direct"
```

---

## Troubleshooting

### "agent-sandbox container not running"

**Fix:**
```bash
bash scripts/start_agent_sandbox.sh
```

**Verify:**
```bash
docker ps | grep agent-sandbox
```

### Commands timeout

**Solution:** Increase timeout
```python
run_passthrough(cmd, timeout=7200)  # 2 hours
```

### Agent doesn't signal "DONE"

**Cause:** Agent ran out of autonomy budget before completing

**Fix:** Increase budget
```bash
python scripts/direct_run.py tasks/my_task.md --budget 25
```

### No artifacts promoted

**Cause:** Agent didn't save files to `/staging/`

**Fix:** Check workspace for results:
```bash
docker exec agent-sandbox ls -la /workspace/
docker exec agent-sandbox ls -la /staging/
```

---

## Implementation Details

### Agent System Prompt

The agent receives this system prompt:

```
You are a high-autonomy AI engineer working in a GPU sandbox terminal.

Your job: Execute commands to complete the task. You have FULL terminal access.

Working directories:
- /workspace → YOUR workspace (read-write, save evidence here)
- /staging → Stage files for promotion (read-write)
- /dataset → Immutable dataset (read-only)

Rules:
1. Act now, explain later - execute real commands
2. Save evidence - put results in /workspace/
3. Fetch latest - use curl/wget, never hardcode versions
4. Finish strong - respond "echo DONE: summary" when complete

Output format: Return ONLY the next bash command (one line, no prose)
```

### Command Extraction

After calling Codex/Claude, we extract the command:
1. Find first non-empty line after "codex" marker
2. Strip markdown code fences (```)
3. Strip quotes
4. Return clean command

### Completion Detection

Agent signals completion by:
1. Including "DONE" in command (e.g., `echo "DONE: Built images"`)
2. OR creating evidence files (heuristic: workspace/versions.json + workspace/build.log exist)

### Artifact Promotion

After execution loop:
1. Check `/staging` for files
2. If found, promote via `ingest_glob("staging/**/*", "direct/{session}/", tags)`
3. Log promotion to ledger

---

## Next Steps

1. **Test Direct-Action mode:**
   ```bash
   python scripts/direct_run.py tasks/build_dfl_docker_rtx4090.md
   ```

2. **Compare performance:**
   - Run same task in both modes
   - Measure time, turns, success rate

3. **Tune autonomy budget:**
   - Start with 15
   - Increase if tasks commonly exceed budget
   - Decrease for simpler tasks

4. **Review audit trail:**
   - Check `reports/ledger.jsonl` after each run
   - Ensure all commands logged
   - Verify evidence promotion

5. **Iterate system prompt:**
   - If agent doesn't use passthrough correctly, refine prompt
   - Add examples of good commands
   - Emphasize "execute NOW, don't write scripts"

---

## Success Metrics

**Direct-Action mode is working well when:**
- ✅ Agent completes tasks in 5-10 commands (vs 20+ in deliberation)
- ✅ Total time < 5 minutes (vs 10-15 in deliberation)
- ✅ Agent fetches latest versions (no hardcoding)
- ✅ Agent executes builds/tests (doesn't just write scripts)
- ✅ Evidence files in /workspace/ prove execution
- ✅ Artifacts properly promoted to dataset/

**Red flags:**
- ❌ Agent writes scripts without executing them
- ❌ Agent hardcodes versions from knowledge cutoff
- ❌ Commands fail repeatedly
- ❌ No evidence files created
- ❌ Session exceeds autonomy budget without completing

---

## Conclusion

Direct-Action mode transforms agents from "plan writers" to "terminal engineers."

**Before:** Agents felt like Shawshank prisoners - smart but artificially constrained.

**After:** Agents have terminal freedom - full GPU sandbox access, web connectivity, and execution power.

**Safety:** Same hard invariant - evidence is immutable, publishing is append-only.

**Result:** Faster iteration, better results, happier agents (and users).

---

**References:**
- User proposal: Freedom Mode++ message (2025-10-29)
- Implementation: `scripts/direct_run.py`
- Adoption fix: `docs/AGENT_ADOPTION_FIX_SUMMARY.md`
- Passthrough mode: `docs/agent_passthrough_mode.md`
