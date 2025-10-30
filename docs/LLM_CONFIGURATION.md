# LLM Configuration Reference

**AAv3 REAL System - Complete LLM Hardcoding Audit**
**Date**: 2025-10-30
**Version**: v1.2.0+

---

## Executive Summary

This document provides a comprehensive inventory of all LLM-related hardcoded values and configurable parameters in the AAv3 REAL system. Use this as a reference to understand cost drivers, model dependencies, and customization options.

## Table of Contents

1. [Configuration Hierarchy](#configuration-hierarchy)
2. [Hardcoded LLM Values](#hardcoded-llm-values)
3. [Configurable Parameters](#configurable-parameters)
4. [Environment Variables](#environment-variables)
5. [Cost Control](#cost-control)
6. [Migration Guide](#migration-guide)

---

## Configuration Hierarchy

### Priority Order (Highest to Lowest)

1. **CLI Arguments** - Direct command-line parameters
2. **Environment Variables** - `OPENAI_MODEL`, `OPENAI_API_KEY`, etc.
3. **Hardcoded Defaults** - Built-in fallback values

---

## Hardcoded LLM Values

### 1. OpenAI Model - `scripts/aav2_llm_integration.py`

**HARDCODED: `model="gpt-4"`**

**Location**: `scripts/aav2_llm_integration.py:94, 101`

```python
# Line 94
response = client.chat.completions.create(
    model="gpt-4",  # ⚠️ HARDCODED
    messages=messages,
    max_tokens=max_tokens
)

# Line 101
return LLMResponse(
    content=response.choices[0].message.content,
    model="gpt-4",  # ⚠️ HARDCODED
    tokens_used=response.usage.total_tokens,
    success=True
)
```

**Impact**:
- **Cost**: GPT-4 is ~10-30x more expensive than GPT-3.5-turbo
- **Performance**: Slower response times than smaller models
- **Availability**: Requires GPT-4 API access

**Workaround** (Until Fixed):
```bash
# No workaround - must modify source code
# To change model, edit scripts/aav2_llm_integration.py line 94
```

**Recommended Fix** (Future v1.3.0):
```python
def call_openai(prompt: str, system_prompt: str = "", max_tokens: int = 4000,
                model: str = None) -> LLMResponse:
    """
    Call OpenAI API with configurable model.

    Args:
        model: Model name (default from OPENAI_MODEL env var, fallback to "gpt-4")
    """
    if model is None:
        model = os.environ.get("OPENAI_MODEL", "gpt-4")

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens
    )
```

### 2. Anthropic Models - `scripts/aav2_llm_integration.py`

**HARDCODED: `model="claude-sonnet-4-20250514"`**

**Location**: `scripts/aav2_llm_integration.py:47`

```python
# Line 47
response = client.messages.create(
    model="claude-sonnet-4-20250514",  # ⚠️ HARDCODED with specific date version
    max_tokens=max_tokens,
    messages=messages
)
```

**Impact**:
- **Versioning**: Tied to specific model snapshot (20250514)
- **Cost**: Claude Sonnet pricing (~$3/$15 per 1M tokens)
- **Availability**: Requires Anthropic API access

**Workaround**:
```bash
# No direct workaround - system chooses between Claude/OpenAI automatically
# Model selection logic is in call_llm() function
```

**Recommended Fix** (Future v1.3.0):
```python
def call_anthropic(prompt: str, system_prompt: str = "", max_tokens: int = 4000,
                   model: str = None) -> LLMResponse:
    """
    Call Anthropic API with configurable model.

    Args:
        model: Model name (default from ANTHROPIC_MODEL env var,
               fallback to "claude-sonnet-4-20250514")
    """
    if model is None:
        model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=messages
    )
```

### 3. Max Tokens - `scripts/aav2_llm_integration.py`

**NOT HARDCODED** ✅ - Passed as parameter with default 4000

```python
def call_llm(prompt: str, system_prompt: str = "", max_tokens: int = 4000) -> LLMResponse:
```

**Status**: **Configurable via function parameter** (Good)

---

## Configurable Parameters

### ✅ Already Configurable via CLI

| Parameter | CLI Flag | Default | Description | File Location |
|-----------|----------|---------|-------------|---------------|
| **Consensus Threshold** | `--consensus-threshold` | `0.67` | Agent approval threshold (v1.2.0+) | `aav3_orchestrator_real.py:666` |
| **Max Rounds** | `--max-rounds` | `50` | Maximum deliberation iterations | `aav3_orchestrator_real.py:36` |
| **Session ID** | `--session-id` | Auto-generated | Reproducible session identifier | `aav3_orchestrator_real.py:36` |

### ✅ Configurable via Environment Variables

| Variable | Default | Used By | Description |
|----------|---------|---------|-------------|
| `OPENAI_API_KEY` | *Required* | All OpenAI calls | API authentication |
| `ANTHROPIC_API_KEY` | Optional | Anthropic calls | API authentication (fallback to Claude) |
| `OPENAI_MODEL` | `gpt-4`* | README.md:172 | **Documented but not used in code** |

**⚠️ IMPORTANT**: `OPENAI_MODEL` is documented in README.md:172 but **NOT actually implemented** in the codebase. This is a documentation bug.

---

## Non-LLM Hardcoded Values (For Reference)

### Subprocess Timeouts

**File**: `scripts/aav3_orchestrator_real.py`

```python
# Line 508 - Python test timeout
timeout=30  # 30 seconds

# Line 549 - Docker build timeout
timeout=600  # 10 minutes
```

**Status**: **Acceptable** - Safety limits, rarely need tuning

---

## Cost Control

### Current Cost Per Session (Estimates)

Based on consensus threshold settings (v1.2.0+):

| Mode | Threshold | Rounds | Tokens | Cost (GPT-4) | Cost (GPT-3.5) |
|------|-----------|--------|--------|--------------|----------------|
| **Lenient** | 0.50 | ~2 | ~50K | $1.00 | $0.10 |
| **Balanced** | 0.67 | ~3 | ~75K | $1.50 | $0.15 |
| **Strict** | 0.90 | ~5 | ~125K | $2.50 | $0.25 |

**Note**: Costs assume GPT-4 at ~$30/1M input tokens, $60/1M output tokens. Using GPT-3.5-turbo would reduce costs by 90%.

### Cost Optimization Strategies

1. **Use Lenient Mode for Prototyping**:
   ```bash
   python scripts/aav3_orchestrator_real.py \
     --task tasks/my_task.md \
     --consensus-threshold 0.5 \
     --max-rounds 2
   ```
   **Savings**: ~40% compared to balanced mode

2. **Switch to GPT-3.5-turbo** (Requires code change):
   - Edit `scripts/aav2_llm_integration.py:94`
   - Change `model="gpt-4"` to `model="gpt-3.5-turbo"`
   - **Savings**: ~90% cost reduction
   - **Trade-off**: Lower quality reasoning

3. **Limit Max Rounds**:
   ```bash
   --max-rounds 2  # Force early termination
   ```

---

## Environment Variables

### Required

```bash
# OpenAI API
export OPENAI_API_KEY='sk-...'  # REQUIRED
```

### Optional

```bash
# LLM Selection
export OPENAI_MODEL='gpt-4'           # DEFAULT (documented but not implemented)
export ANTHROPIC_MODEL='claude-sonnet-4'  # Future use

# Logging
export LOG_LEVEL='INFO'               # DEBUG, INFO, WARNING, ERROR

# Cost Control
export MAX_ROUNDS='3'                 # Override default 50
```

### Usage Examples

```bash
# Budget-conscious run (lenient + limited rounds)
export OPENAI_API_KEY='sk-...'
python scripts/aav3_orchestrator_real.py \
  --task tasks/my_task.md \
  --consensus-threshold 0.5 \
  --max-rounds 2

# Production run (strict + extended rounds)
export OPENAI_API_KEY='sk-...'
python scripts/aav3_orchestrator_real.py \
  --task tasks/my_task.md \
  --consensus-threshold 0.90 \
  --max-rounds 10
```

---

## Migration Guide

### Recommended Improvements for v1.3.0

#### 1. Make Model Selection Configurable

**Current State**:
```python
model="gpt-4"  # Hardcoded at aav2_llm_integration.py:94
```

**Proposed Change**:
```python
model = os.environ.get("OPENAI_MODEL", "gpt-4")
```

**Implementation**:
```diff
  def call_openai(prompt: str, system_prompt: str = "", max_tokens: int = 4000) -> LLMResponse:
      try:
          client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
+         model = os.environ.get("OPENAI_MODEL", "gpt-4")

          messages = []
          if system_prompt:
              messages.append({"role": "system", "content": system_prompt})
          messages.append({"role": "user", "content": prompt})

          response = client.chat.completions.create(
-             model="gpt-4",
+             model=model,
              messages=messages,
              max_tokens=max_tokens
          )

          return LLMResponse(
              content=response.choices[0].message.content,
-             model="gpt-4",
+             model=model,
              tokens_used=response.usage.total_tokens,
              success=True
          )
```

**Benefit**:
- Users can switch models via environment variable
- No CLI changes needed
- 90% cost savings possible with GPT-3.5-turbo

#### 2. Add CLI Flag for Model Selection

**Proposed**:
```python
ap.add_argument("--model", default="gpt-4",
                help="LLM model (gpt-4, gpt-3.5-turbo, gpt-4-turbo)")
```

**Benefit**:
- Override environment variable per-run
- Easier A/B testing of models

#### 3. Add Temperature Control

**Current**: No temperature control (defaults to OpenAI's default 1.0)

**Proposed**:
```python
ap.add_argument("--temperature", type=float, default=0.7,
                help="LLM temperature (0.0=deterministic, 1.0=creative)")
```

**Benefit**:
- Control creativity vs consistency
- Lower temperature (0.3-0.5) for production
- Higher temperature (0.8-1.0) for brainstorming

---

## Summary Table

### Complete Hardcoding Audit

| Category | Item | Status | Location | Priority |
|----------|------|--------|----------|----------|
| **Model Name** | OpenAI `gpt-4` | ⚠️ HARDCODED | `aav2_llm_integration.py:94` | HIGH |
| **Model Name** | Anthropic `claude-sonnet-4-20250514` | ⚠️ HARDCODED | `aav2_llm_integration.py:47` | MEDIUM |
| **Max Tokens** | Default 4000 | ✅ Configurable | Function parameter | OK |
| **Consensus** | Threshold 0.67 | ✅ Configurable (v1.2.0+) | `--consensus-threshold` | FIXED |
| **Max Rounds** | Default 50 | ✅ Configurable | `--max-rounds` | OK |
| **Temperature** | Default 1.0 (OpenAI) | ⚠️ NOT EXPOSED | N/A | LOW |
| **API Keys** | Required from env | ✅ Environment variable | `OPENAI_API_KEY` | OK |
| **Timeouts** | 30s, 600s | ⚠️ HARDCODED | `aav3_orchestrator_real.py:508,549` | LOW |

---

## Quick Reference

### To Change LLM Model (Manual Edit Required)

1. **Open**: `scripts/aav2_llm_integration.py`
2. **Find**: Line 94 - `model="gpt-4"`
3. **Change to**: `model="gpt-3.5-turbo"` (for cost savings)
4. **Find**: Line 101 - `model="gpt-4"`
5. **Change to**: Same as step 3
6. **Save** and test

### To Reduce Costs Immediately

```bash
# Use lenient consensus + limit rounds
python scripts/aav3_orchestrator_real.py \
  --task tasks/my_task.md \
  --consensus-threshold 0.5 \
  --max-rounds 2
```

**Savings**: ~60% compared to default settings

---

## Version History

- **v1.2.0** (2025-10-30): Added configurable consensus threshold
- **v1.1.0** (2025-01-XX): Added environment capability detection
- **v1.0.0** (2025-01-XX): Initial release with hardcoded GPT-4

---

## Contributing

Found a hardcoded LLM value not listed here? Please submit an issue or pull request:

- **Issues**: https://github.com/CUSTODIREAI/AA3/issues
- **Pull Requests**: https://github.com/CUSTODIREAI/AA3/pulls

---

**Next Steps**: See [CONSENSUS_MODES.md](CONSENSUS_MODES.md) for cost/quality trade-off guidance.
