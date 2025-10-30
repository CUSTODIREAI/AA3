# Agent Passthrough Mode - Full Freedom Architecture

**Status:** ✅ Implemented
**Date:** 2025-10-29

## Problem Solved

**Before:** Agents were trapped in a "chaingang" where:
- No web search capability (task requires it, policy doesn't allow it)
- docker.build action declared but not implemented (false capability trap)
- Agents forced to use outdated knowledge cutoff data
- Every new capability required implementing a new action handler
- System couldn't keep up with agent intelligence

**After:** Agents get **full freedom** inside a safe sandbox:
- Native web search, docker build, git, python, any tool they need
- Full GPU access with no artificial limits
- Network access to get latest versions
- Can use ALL their built-in capabilities
- **One hard constraint:** dataset/ and evidence/ are immutable

---

## Architecture

### The Core Insight

**Don't fight the tools agents already have - give them a safe place to use them.**

Instead of implementing hundreds of action handlers (web.search, docker.build, git.clone, npm.install, etc.), we provide ONE action that lets agents execute ANY command inside a persistent sandbox:

```yaml
- type: agent.passthrough_shell
  params: [cmd]
```

### The Hard Invariant

**Dataset & Evidence Are Immutable**

The ONLY way to publish results to the dataset is via the explicit, logged, append-only action:

```yaml
- type: ingest.promote
  params: [items]
```

This is enforced by:
1. **Read-only mounts** - /dataset and /evidence mounted with `:ro` flag
2. **Filesystem enforcement** - Linux kernel prevents writes to RO mounts
3. **Gateway logging** - All ingest.promote actions logged with SHA-256 hashes

---

## How It Works

### 1. Start the Persistent Sandbox

```bash
bash scripts/start_agent_sandbox.sh
```

This creates a long-running Docker container named `agent-sandbox` with:
- **Full GPU access** (`--gpus all`)
- **No resource limits** (no CPU/RAM caps)
- **Network enabled** (can fetch latest versions, clone repos, etc.)
- **Immutable dataset** (/dataset mounted read-only)
- **Immutable evidence** (/evidence mounted read-only)
- **Freedom zones** (/workspace, /staging, /cache mounted read-write)

### 2. Agents Execute Commands

When a plan includes:

```json
{
  "type": "agent.passthrough_shell",
  "params": {
    "cmd": "curl -s https://api.github.com/repos/iperov/DeepFaceLab/releases/latest | jq -r .tag_name > /workspace/dfl_latest_version.txt"
  }
}
```

The executor runs:
```bash
docker exec -w /workspace agent-sandbox bash -c "<cmd>"
```

Agents can:
- Search the web for latest versions
- Build Docker images
- Train ML models on GPU
- Run tests
- Clone repositories
- Install packages
- Compile code
- **Anything they need**

### 3. Publishing Results

After working in `/workspace` or `/staging`, agents use the explicit promotion action:

```json
{
  "type": "ingest.promote",
  "items": [
    {
      "src": "staging/docker/dfl-base.Dockerfile",
      "relative_dst": "docker/dfl-base.Dockerfile",
      "tags": {"component": "dfl", "gpu": "rtx4090"}
    }
  ]
}
```

This:
- Copies file to dataset with timestamp
- Computes SHA-256 hash
- Logs to manifest
- Makes it **immutable** (cannot be modified or deleted)

---

## Mounts & Permissions

### Read-Only (Immutable - Hard Constraint)

| Path | Purpose | Agents Can |
|------|---------|------------|
| `/dataset` | Immutable data store | Read only |
| `/evidence` | Immutable evidence store | Read only |
| `/staging-final` | Finalized staging | Read only |

**Enforced by:** Linux kernel RO mount + Docker mount mode

### Read-Write (Freedom Zones)

| Path | Purpose | Agents Can |
|------|---------|------------|
| `/workspace` | Primary work area | Full control |
| `/staging` | Pre-promotion staging | Full control |
| `/cache` | Build caches, downloads | Full control |

**Agents have FULL freedom** in these directories.

---

## Security Model

### What Agents CAN Do (Inside Sandbox)

✅ Use web search / fetch latest versions
✅ Build Docker images
✅ Run GPU workloads (training, inference)
✅ Install packages (pip, npm, apt if needed)
✅ Clone repositories
✅ Compile code
✅ Run tests
✅ Create files in /workspace, /staging, /cache
✅ Delete/modify files in /workspace, /staging, /cache
✅ Access network
✅ Use unlimited CPU/RAM

### What Agents CANNOT Do

❌ Write to /dataset (RO mount, kernel enforced)
❌ Write to /evidence (RO mount, kernel enforced)
❌ Delete from /dataset (RO mount)
❌ Modify files in /dataset (RO mount)
❌ Bypass ingest.promote (only way to publish)
❌ Escape sandbox (Docker isolation)

### Publishing (Controlled & Logged)

📝 Agents must explicitly call `ingest.promote`
📝 All promotions logged with SHA-256 hashes
📝 Append-only - no deletes or modifications
📝 Timestamped and tagged
📝 Fully auditable

---

## Benefits

### 1. Stop Fighting Agent Intelligence

**Before:**
- Agent knows how to use web search → policy doesn't allow it
- Agent knows how to build Docker → executor doesn't implement it
- Agent knows latest CUDA version → forced to use Jan 2025 data

**After:**
- Agent uses native capabilities inside sandbox
- No permission barriers for legitimate work
- Can adapt to current reality, not frozen knowledge cutoff

### 2. Competitive Speed

**Before:**
- Wait for humans to implement new action handlers
- Each capability requires code changes
- Weeks to add web search support

**After:**
- Agents use tools they already have
- Zero latency for new capabilities
- Instant access to full ecosystem

### 3. Safe by Default

**Before:**
- Granular permissions create complexity
- Easy to miss security holes
- Hard to audit all action types

**After:**
- ONE hard rule: dataset/evidence immutable
- Impossible to violate (kernel enforced)
- Simple to audit: check RO mounts + ingest logs

### 4. GPU Freedom

**Before:**
- CPU/RAM limits
- No CUDA base images
- No persistent GPU workloads

**After:**
- Full GPU access (`--gpus all`)
- No artificial limits
- Can train models, run inference, build with CUDA

---

## Usage Examples

### Example 1: Get Latest CUDA Version

```json
{
  "type": "agent.passthrough_shell",
  "params": {
    "cmd": "curl -s https://developer.nvidia.com/cuda-downloads | grep -oP 'CUDA \\K[0-9.]+' | head -1 > /workspace/cuda_latest.txt"
  }
}
```

### Example 2: Build Docker Image

```json
{
  "type": "agent.passthrough_shell",
  "params": {
    "cmd": "docker build -t custodire/dfl-base:rtx4090 -f /staging/docker/dfl-base.Dockerfile /staging",
    "timeout_sec": 7200
  }
}
```

### Example 3: Train ML Model

```json
{
  "type": "agent.passthrough_shell",
  "params": {
    "cmd": "python /workspace/train.py --gpu 0 --epochs 100 --output /workspace/models/",
    "timeout_sec": 86400
  }
}
```

### Example 4: Search Web & Build

```json
{
  "type": "agent.passthrough_shell",
  "params": {
    "cmd": "curl -s https://api.github.com/repos/iperov/DeepFaceLab/releases/latest > /workspace/dfl_release.json && python /workspace/build_from_latest.py"
  }
}
```

---

## Policy Configuration

In `configs/policy.yaml`:

```yaml
- type: agent.passthrough_shell
  params: [cmd]
  description: "Execute arbitrary commands inside agent sandbox with full capabilities"
  sandbox:
    container: "agent-sandbox"
    mount_allowlist:
      - prefix: dataset
        mode: ro
      - prefix: evidence
        mode: ro
      - prefix: staging-final
        mode: ro
      - prefix: workspace
        mode: rw
      - prefix: staging
        mode: rw
      - prefix: cache
        mode: rw
    gpu_access: true
    network_access: true
    no_resource_limits: true
  # Invariant: dataset/ and evidence/ are immutable (RO mounts)
  # Only way to publish: ingest.promote (append-only with hashes)
```

---

## Executor Implementation

In `src/orchestrator/cycle.py`:

```python
elif action_type == 'agent.passthrough_shell':
    cmd = params.get('cmd', '')

    # Check sandbox is running
    check_result = subprocess.run(
        ["docker", "ps", "--filter", "name=agent-sandbox", "--format", "{{.Names}}"],
        capture_output=True, text=True, timeout=10
    )

    if "agent-sandbox" not in check_result.stdout:
        return {"ok": False, "error": "agent-sandbox not running"}

    # Execute with full freedom
    result = subprocess.run(
        ["docker", "exec", "-w", "/workspace", "agent-sandbox", "bash", "-c", cmd],
        capture_output=True,
        text=True,
        timeout=params.get('timeout_sec', 3600)
    )

    return {
        "ok": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr
    }
```

---

## Comparison: Before vs After

### Before: Micro-Permissions (Chaingang)

```yaml
actions:
  - type: web.search
    params: [query]
    rate_limit: 10_per_minute

  - type: docker.build
    params: [dockerfile, context, tag]
    max_build_time: 7200

  - type: git.clone
    params: [repo, dst]

  - type: npm.install
    params: [package]

  # ... 50 more action types ...
```

**Problems:**
- Each capability requires implementation
- Easy to miss cases (web.search exists but docker.build doesn't)
- Agents trapped by missing handlers
- Maintenance nightmare

### After: Passthrough (Freedom)

```yaml
actions:
  - type: agent.passthrough_shell
    params: [cmd]
    # Full freedom inside sandbox

  - type: ingest.promote
    params: [items]
    # Only way to publish
```

**Benefits:**
- Agents use native capabilities
- No missing handler problems
- Simple to maintain
- One hard constraint (immutable dataset)

---

## Setup Instructions

### 1. Start Sandbox (First Time)

```bash
cd custodire-aa-system
bash scripts/start_agent_sandbox.sh
```

This creates and verifies the sandbox. Output:
```
[+] Creating new agent sandbox container: agent-sandbox
[✓] Agent sandbox created successfully
[✓] GPU accessible in sandbox
[✓] Dataset is properly read-only (immutable)
```

### 2. Verify Sandbox

```bash
docker exec agent-sandbox bash -c '
echo "=== Sandbox Check ==="
nvidia-smi --query-gpu=name --format=csv,noheader
echo "Dataset RO: $(ls -ld /dataset | grep dr-xr-xr-x && echo YES || echo NO)"
echo "Workspace RW: $(touch /workspace/.test && rm /workspace/.test && echo YES || echo NO)"
echo "Network: $(curl -s https://api.github.com > /dev/null && echo YES || echo NO)"
'
```

### 3. Use in Plans

Agents can now use passthrough_shell in their plans. Example:

```json
{
  "plan_id": "example-001",
  "actions": [
    {
      "id": "A1",
      "type": "agent.passthrough_shell",
      "params": {
        "cmd": "curl -s https://pypi.org/pypi/tensorflow/json | jq -r .info.version > /workspace/tf_latest.txt"
      }
    },
    {
      "id": "A2",
      "type": "fs.write",
      "params": {
        "path": "staging/versions.json",
        "content": "..."
      }
    },
    {
      "id": "A3",
      "type": "ingest.promote",
      "items": [
        {"src": "staging/versions.json", "relative_dst": "meta/versions.json"}
      ]
    }
  ]
}
```

---

## Troubleshooting

### "agent-sandbox container not running"

**Solution:** Start the sandbox:
```bash
bash scripts/start_agent_sandbox.sh
```

### "nvidia-smi not working"

**Check GPU access:**
```bash
docker exec agent-sandbox nvidia-smi
```

If fails, ensure:
- NVIDIA drivers installed (520+ for RTX 4090)
- nvidia-docker2 installed
- Docker daemon has nvidia runtime

### "Permission denied" writing to workspace

**Check mounts:**
```bash
docker exec agent-sandbox ls -la /workspace
```

Should show `drwxrwxrwx` (world-writable)

### Sandbox crashed/stopped

**Restart:**
```bash
docker start agent-sandbox
```

Or recreate:
```bash
docker rm agent-sandbox
bash scripts/start_agent_sandbox.sh
```

---

## Future Enhancements

### 1. Multiple Sandboxes

Run specialized sandboxes for different workloads:
- `agent-sandbox-gpu` - GPU workloads
- `agent-sandbox-build` - Docker builds
- `agent-sandbox-web` - Web scraping

### 2. MCP Integration

Connect agents' native tools (todo, search, memory) to the sandbox via Model Context Protocol for even tighter integration.

### 3. Persistent Agent Sessions

Keep Codex/Claude running in tmux inside sandbox:
```bash
docker exec -it agent-sandbox tmux attach
```

Agents maintain memory across tasks.

### 4. Kill Switch

Add `MAINTENANCE` file check:
```python
if Path("MAINTENANCE").exists():
    return {"ok": False, "error": "System in maintenance mode"}
```

### 5. Resource Quotas (Optional)

Add soft limits if needed (not enforced by default):
```yaml
resources:
  warn_cpu_percent: 80
  warn_mem_gb: 64
  alert_on_threshold: true
```

---

## Success Metrics

### Before Passthrough Mode

❌ Web search: Not available
❌ Docker build: Policy says yes, executor says no
❌ Latest versions: Forced to use Jan 2025 data
❌ GPU freedom: CPU/RAM limits, no CUDA bases
⏱️ Time to add capability: Days to weeks
🔒 Security model: Complex, many permission types

### After Passthrough Mode

✅ Web search: Native capability
✅ Docker build: Works out of box
✅ Latest versions: Can fetch current data
✅ GPU freedom: Full access, no limits
⏱️ Time to add capability: Zero (already have it)
🔒 Security model: Simple (one hard rule)

---

## Conclusion

**Agent Passthrough Mode solves the core tension:**

You want agents to have **maximum intelligence and capability** (that's why you chose Codex/Claude), but you need **one inviolable constraint** (immutable dataset/evidence for legal integrity).

Traditional micro-permissions create a "chaingang" - agents are smart but handcuffed. Passthrough mode gives them **full freedom** inside a sandbox while enforcing the **one rule that matters** via kernel-level RO mounts.

**Result:** Agents can compete at full speed while your truth store remains perfectly safe.

---

**Files:**
- Policy: `configs/policy.yaml` (agent.passthrough_shell action)
- Sandbox: `scripts/start_agent_sandbox.sh` (container setup)
- Executor: `src/orchestrator/cycle.py` (passthrough handler)
- Docs: `docs/agent_passthrough_mode.md` (this file)

**Quick Start:**
```bash
bash scripts/start_agent_sandbox.sh
# Agents now have full freedom - dataset remains immutable
```
