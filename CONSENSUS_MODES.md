# Configurable Consensus Threshold

## Overview

AAv3 REAL now supports configurable consensus thresholds via `--consensus-threshold` parameter, allowing you to balance between quality and efficiency.

## Usage

```bash
# Lenient mode (50% approval) - Faster, cheaper, more exploratory
python scripts/aav3_orchestrator_real.py \
  --task tasks/my_task.md \
  --consensus-threshold 0.50

# Balanced mode (67% approval) - DEFAULT
python scripts/aav3_orchestrator_real.py \
  --task tasks/my_task.md \
  --consensus-threshold 0.67

# Strict mode (90% approval) - High quality, more deliberation rounds
python scripts/aav3_orchestrator_real.py \
  --task tasks/my_task.md \
  --consensus-threshold 0.90
```

## Modes Explained

| Mode | Threshold | Use Case | Trade-offs |
|------|-----------|----------|------------|
| **Lenient** | 0.50-0.60 | Rapid prototyping, exploratory tasks | ⚡ Faster, 💰 Cheaper, ⚠️ Lower quality |
| **Balanced** | 0.67 (DEFAULT) | General tasks, production code | ⚖️ Good balance |
| **Strict** | 0.80-0.95 | Mission-critical, production deployments | ✅ Higher quality, ⏱️ Slower, 💸 More expensive |

## How It Works

During the consensus phase, all agents vote to approve or reject the implementation. The system now displays:

```
Consensus: 80% approval (4/5)
Required threshold: 67%
Result: APPROVED ✓
```

- **Below threshold**: Task goes through another refinement round
- **Above threshold**: Task is approved and completed
- **Lower threshold = fewer rounds = cheaper but riskier**
- **Higher threshold = more rounds = expensive but safer**

## Cost Impact

Assuming $0.10 per agent LLM call:

- **Lenient (0.50)**: ~$1.00 (avg 2 rounds)
- **Balanced (0.67)**: ~$1.50 (avg 3 rounds)  
- **Strict (0.90)**: ~$2.50 (avg 5 rounds)

## Environment Variable

```bash
export AAV3_CONSENSUS_THRESHOLD=0.75
```

(Note: CLI argument takes precedence)

## Examples

### Production Deployment
```bash
# Strict mode for deploying to production
python scripts/aav3_orchestrator_real.py \
  --task "Deploy authentication service" \
  --consensus-threshold 0.90 \
  --max-rounds 5
```

### Quick Experimentation
```bash
# Lenient mode for rapid prototyping
python scripts/aav3_orchestrator_real.py \
  --task "Prototype new API endpoint" \
  --consensus-threshold 0.55 \
  --max-rounds 2
```

## Version History

- **v1.2.0** (2025-01-XX): Added configurable consensus threshold parameter
