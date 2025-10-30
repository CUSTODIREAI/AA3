#!/usr/bin/env python3
"""
AAv2.5 LLM Integration - Real AI Reasoning

Provides unified interface to call LLMs (Claude, GPT, etc.)
for diagnosis, planning, and other reasoning tasks.

This is what enables TRUE multi-agent LLM collaboration.
"""
from __future__ import annotations
import os, json, subprocess
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

@dataclass
class LLMResponse:
    """Standardized LLM response"""
    content: str
    model: str
    tokens_used: int
    success: bool
    error: Optional[str] = None

def call_claude_api(prompt: str, system_prompt: str = "", max_tokens: int = 4096) -> LLMResponse:
    """
    Call Claude API for reasoning.

    Since we're IN Claude Code, we can use the subprocess approach
    to call ourselves in a fresh context.
    """
    # For now, we'll use a simulated call
    # In production, this would be: anthropic.Anthropic().messages.create(...)

    # Construct the prompt for diagnosis
    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

    # Simulate calling Claude (in production, use Anthropic SDK)
    # For this implementation, we'll use a subprocess call to python with anthropic

    try:
        # Try to use Anthropic API if available
        import anthropic

        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            system=system_prompt if system_prompt else "You are a helpful AI assistant analyzing errors and suggesting fixes.",
            messages=[{"role": "user", "content": prompt}]
        )

        return LLMResponse(
            content=message.content[0].text,
            model="claude-sonnet-4",
            tokens_used=message.usage.input_tokens + message.usage.output_tokens,
            success=True
        )

    except ImportError:
        # Anthropic SDK not installed - use fallback
        return LLMResponse(
            content="[LLM unavailable - using heuristic fallback]",
            model="fallback",
            tokens_used=0,
            success=False,
            error="Anthropic SDK not installed. Run: pip install anthropic"
        )
    except Exception as e:
        return LLMResponse(
            content="",
            model="error",
            tokens_used=0,
            success=False,
            error=str(e)
        )


def call_openai_api(prompt: str, system_prompt: str = "", max_tokens: int = 4096) -> LLMResponse:
    """
    Call OpenAI API (GPT-4/Codex) for reasoning.
    """
    try:
        import openai

        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=max_tokens
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            model="gpt-4",
            tokens_used=response.usage.total_tokens,
            success=True
        )

    except ImportError:
        return LLMResponse(
            content="",
            model="error",
            tokens_used=0,
            success=False,
            error="OpenAI SDK not installed. Run: pip install openai"
        )
    except Exception as e:
        return LLMResponse(
            content="",
            model="error",
            tokens_used=0,
            success=False,
            error=str(e)
        )


def diagnose_with_llm(
    failed_command: str,
    stderr: str,
    stdout: str,
    task_context: str = "",
    use_claude: bool = True
) -> Dict[str, Any]:
    """
    Use real LLM reasoning to diagnose a failure.

    This is the breakthrough - actual AI analysis instead of regex patterns!
    """

    system_prompt = """You are an expert systems debugger analyzing command failures.

Your task: Given a failed command and its error output, provide:
1. error_type (one word: permission, not_found, network, syntax, docker, etc.)
2. root_cause (one sentence explaining why it failed)
3. suggested_fix (concrete command or action to fix it)
4. confidence (0.0-1.0 how confident you are)

Respond in JSON format:
{
  "error_type": "...",
  "root_cause": "...",
  "suggested_fix": "...",
  "confidence": 0.0
}"""

    user_prompt = f"""Command that failed:
$ {failed_command}

Standard error:
{stderr[:1000]}

Standard output:
{stdout[:500]}

{f"Task context: {task_context}" if task_context else ""}

Analyze this failure and respond with diagnosis JSON."""

    # Call LLM
    if use_claude:
        response = call_claude_api(user_prompt, system_prompt, max_tokens=1024)
    else:
        response = call_openai_api(user_prompt, system_prompt, max_tokens=1024)

    if not response.success:
        # Fallback to heuristics
        return {
            "error_type": "unknown",
            "root_cause": f"LLM unavailable: {response.error}",
            "suggested_fix": "Review error logs manually",
            "confidence": 0.2,
            "llm_used": False
        }

    # Parse LLM response
    try:
        # Extract JSON from response (might have markdown fences)
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        diagnosis = json.loads(content.strip())
        diagnosis["llm_used"] = True
        diagnosis["llm_model"] = response.model
        diagnosis["llm_tokens"] = response.tokens_used

        return diagnosis

    except json.JSONDecodeError:
        # LLM didn't return valid JSON - parse as text
        return {
            "error_type": "parse_error",
            "root_cause": "LLM response not JSON",
            "suggested_fix": content[:200],  # Use first 200 chars as suggestion
            "confidence": 0.5,
            "llm_used": True,
            "llm_model": response.model
        }


def generate_plan_with_llm(task_description: str, use_claude: bool = True) -> List[str]:
    """
    Use LLM to generate an execution plan.
    """
    system_prompt = """You are a software task planner. Break tasks into concrete steps.

Output a numbered list of specific, executable steps. Each step should be:
- Concrete (not vague)
- Testable (can verify it worked)
- Ordered (dependencies clear)

Example:
1. Create directory structure
2. Write configuration file
3. Run build command
4. Execute tests
5. Verify output exists"""

    user_prompt = f"""Task: {task_description}

Generate a step-by-step execution plan:"""

    if use_claude:
        response = call_claude_api(user_prompt, system_prompt, max_tokens=2048)
    else:
        response = call_openai_api(user_prompt, system_prompt, max_tokens=2048)

    if not response.success:
        return ["[Plan generation failed - LLM unavailable]"]

    # Parse numbered list
    lines = response.content.split('\n')
    steps = []
    for line in lines:
        line = line.strip()
        if line and (line[0].isdigit() or line.startswith('-') or line.startswith('*')):
            # Remove number/bullet
            step = line.lstrip('0123456789.-*) ').strip()
            if step:
                steps.append(step)

    return steps if steps else [response.content]


def compress_context_with_llm(long_context: str, max_length: int = 2000, use_claude: bool = True) -> str:
    """
    Use LLM to compress/summarize long context (auto-compaction).
    """
    if len(long_context) <= max_length:
        return long_context

    system_prompt = """You are a context compressor. Summarize long text while preserving:
- Key decisions made
- Important errors encountered
- Current state/status
- Critical information needed for next steps

Be concise but complete."""

    user_prompt = f"""Compress this context to ~{max_length} chars while keeping all critical info:

{long_context}

Compressed version:"""

    if use_claude:
        response = call_claude_api(user_prompt, system_prompt, max_tokens=max_length//2)
    else:
        response = call_openai_api(user_prompt, system_prompt, max_tokens=max_length//2)

    if not response.success:
        # Fallback: truncate
        return long_context[:max_length] + "\n[...truncated...]"

    return response.content


if __name__ == "__main__":
    # Test LLM integration
    print("Testing LLM Integration...")

    # Test diagnosis
    result = diagnose_with_llm(
        failed_command="ls /nonexistent",
        stderr="ls: cannot access '/nonexistent': No such file or directory",
        stdout="",
        task_context="Building Docker image"
    )

    print("\nDiagnosis Result:")
    print(json.dumps(result, indent=2))

    # Test planning
    plan = generate_plan_with_llm("Build a Docker image for DeepFaceLab with RTX 4090 support")
    print("\nGenerated Plan:")
    for i, step in enumerate(plan, 1):
        print(f"{i}. {step}")
