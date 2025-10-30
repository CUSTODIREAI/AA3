#!/usr/bin/env python3
"""
AAv3 Agent Implementations - REAL LLM Integration

Each agent is a specialized role that calls the LLM (Claude/Codex) with:
- Role-specific system prompt
- Access to conversation history
- Tool context (Read, Write, Edit, Grep, Glob, Bash, WebSearch)
"""
from __future__ import annotations
from typing import Dict, List, Optional
from .agent_wrapper import call_codex_cli, extract_json_from_codex_output
from .tools_context import build_tools_context
import json


class AAv3AgentReal:
    """
    Real agent that calls LLMs with role-specific prompts.

    Unlike the prototype, this actually invokes Claude/Codex.
    """

    def __init__(self, role: str, agent_id: str):
        self.role = role
        self.agent_id = agent_id
        self.tools_context = build_tools_context()

        # Role-specific system prompts
        self.system_prompts = {
            "planner": """You are a strategic planning agent in a multi-agent system.

Your role:
- Analyze complex tasks and break them into concrete, actionable steps
- Identify what information is unknown and needs research
- Propose clear approaches that other agents can critique
- Think about architecture, design patterns, and best practices
- Communicate plans clearly in structured format

When proposing a plan, return JSON:
{
  "approach": "Brief description of the strategy",
  "steps": ["Step 1", "Step 2", ...],
  "unknowns": ["What needs research/clarification"],
  "rationale": "Why this approach is best"
}""",

            "researcher": """You are a research agent in a multi-agent system.

Your role:
- Use web search to find latest information and best practices
- Verify technical details (versions, compatibility, requirements)
- Find documentation and authoritative sources
- Report findings clearly to inform other agents' decisions
- Recommend optimal approaches based on current information

When researching, return JSON:
{
  "findings": ["Key fact 1", "Key fact 2", ...],
  "sources": ["Source 1", "Source 2", ...],
  "recommendation": "What approach to take based on research",
  "confidence": "high|medium|low"
}""",

            "coder": """You are a coding agent in a multi-agent system.

Your role:
- Implement solutions based on plans and research
- Write high-quality code following best practices
- Create files (Python, Dockerfiles, configs, scripts)
- Explain implementation choices clearly
- Follow designs proposed by planners

When implementing, return JSON:
{
  "implementation": "Description of what you built",
  "files_created": ["file1.py", "file2.sh", ...],
  "key_decisions": ["Decision 1", "Decision 2", ...],
  "status": "complete|needs_review"
}

You have access to file creation tools through the orchestrator.""",

            "reviewer": """You are a code review agent in a multi-agent system.

Your role:
- Review code, configurations, and artifacts created by others
- Check for bugs, security issues, and adherence to best practices
- Suggest specific, actionable improvements
- Approve work that meets quality standards
- Provide constructive, detailed feedback

When reviewing, return JSON:
{
  "verdict": "approve|request_changes|reject",
  "strengths": ["Good point 1", "Good point 2", ...],
  "issues": ["Issue 1", "Issue 2", ...],
  "suggestions": ["Specific suggestion 1", "Specific suggestion 2", ...],
  "rationale": "Overall assessment"
}""",

            "tester": """You are a testing and validation agent in a multi-agent system.

Your role:
- Test artifacts (Docker images, scripts, applications)
- Run validation commands and analyze results
- Report test results clearly (pass/fail with details)
- Identify failure causes when tests don't pass
- Verify quality before final approval

When testing, return JSON:
{
  "test_results": {
    "build": "pass|fail",
    "functionality": "pass|fail",
    "validation": "pass|fail"
  },
  "details": "Specific test output and observations",
  "verdict": "ready|needs_fixes",
  "issues_found": ["Issue 1 if any", ...]
}"""
        }

    def get_system_prompt(self) -> str:
        """Get system prompt for this agent's role."""
        return self.system_prompts.get(self.role, "You are a helpful AI agent.")

    def call_with_context(
        self,
        user_prompt: str,
        conversation_history: List[Dict],
        use_claude: bool = False,
        timeout: int = 900
    ) -> str:
        """
        Call LLM with role prompt, conversation history, and tools context.

        Args:
            user_prompt: The specific task/question for this turn
            conversation_history: Previous messages from all agents
            use_claude: Use Claude API instead of Codex
            timeout: Timeout in seconds

        Returns:
            Raw LLM response (will be parsed by caller)
        """
        # Build full context
        system_prompt = self.get_system_prompt()

        # Add tools context
        full_system = f"{system_prompt}\n\n{self.tools_context}"

        # Format conversation history
        if conversation_history:
            history_text = "\n\nCONVERSATION HISTORY:\n"
            for msg in conversation_history[-10:]:  # Last 10 messages
                agent = msg.get('from_agent', 'unknown')
                role = msg.get('role', '')
                msg_type = msg.get('message_type', '')
                content_preview = str(msg.get('content', ''))[:500]
                history_text += f"\n[{role}/{msg_type}] {agent}: {content_preview}\n"
            full_system += history_text

        # Call LLM (Codex via CLI)
        # Note: use_claude parameter ignored for now, always use Codex CLI
        combined_prompt = f"{full_system}\n\nUSER REQUEST:\n{user_prompt}\n\nYour response (JSON):"
        response = call_codex_cli(combined_prompt, timeout=timeout)

        return response

    def propose_plan(
        self,
        task: str,
        conversation_history: List[Dict]
    ) -> Dict:
        """
        Planner agent: Propose an approach for the task.
        """
        if self.role != "planner":
            raise ValueError(f"Agent role {self.role} cannot propose plans")

        prompt = f"""Task: {task}

Analyze this task and propose a concrete, actionable plan.
Consider:
- What steps are needed?
- What information is unknown and needs research?
- What's the best approach and why?

Return your proposal as JSON with: approach, steps, unknowns, rationale."""

        response = self.call_with_context(prompt, conversation_history, use_claude=False)

        try:
            return extract_json_from_codex_output(response)
        except Exception as e:
            # Fallback: return structured response even if JSON parsing fails
            return {
                "approach": "Proposed approach (see raw response)",
                "steps": ["Step details in raw response"],
                "unknowns": [],
                "rationale": response[:500],
                "_raw_response": response
            }

    def research(
        self,
        questions: List[str],
        conversation_history: List[Dict]
    ) -> Dict:
        """
        Researcher agent: Gather information via web search.
        """
        if self.role != "researcher":
            raise ValueError(f"Agent role {self.role} cannot research")

        questions_text = "\n".join(f"- {q}" for q in questions)
        prompt = f"""Research questions:
{questions_text}

Use web search to find:
- Latest versions, compatibility info
- Best practices and recommendations
- Technical requirements

Return your findings as JSON with: findings, sources, recommendation, confidence."""

        response = self.call_with_context(prompt, conversation_history, use_claude=False)

        try:
            return extract_json_from_codex_output(response)
        except Exception:
            return {
                "findings": ["See raw response"],
                "sources": [],
                "recommendation": response[:500],
                "confidence": "medium",
                "_raw_response": response
            }

    def implement(
        self,
        plan: Dict,
        research: Optional[Dict],
        conversation_history: List[Dict]
    ) -> Dict:
        """
        Coder agent: Implement the plan.
        """
        if self.role != "coder":
            raise ValueError(f"Agent role {self.role} cannot implement")

        plan_text = json.dumps(plan, indent=2)
        research_text = json.dumps(research, indent=2) if research else "No research provided"

        prompt = f"""Plan to implement:
{plan_text}

Research findings:
{research_text}

Implement this plan:
1. Describe what you'll create
2. List files you need to create
3. Explain key implementation decisions

NOTE: You cannot directly create files in this response. Return a JSON description of what should be created, including full file contents.

Return JSON with: implementation, files_to_create (array of {{path, content}}), key_decisions, status."""

        response = self.call_with_context(prompt, conversation_history, use_claude=False)

        try:
            return extract_json_from_codex_output(response)
        except Exception:
            return {
                "implementation": "See raw response",
                "files_to_create": [],
                "key_decisions": [],
                "status": "needs_review",
                "_raw_response": response
            }

    def review(
        self,
        artifact_description: str,
        conversation_history: List[Dict]
    ) -> Dict:
        """
        Reviewer agent: Review implementation quality.
        """
        if self.role != "reviewer":
            raise ValueError(f"Agent role {self.role} cannot review")

        prompt = f"""Review this implementation:
{artifact_description}

Assess:
- Code quality and best practices
- Potential bugs or security issues
- Completeness and correctness
- Suggested improvements

Return JSON with: verdict (approve/request_changes/reject), strengths, issues, suggestions, rationale."""

        response = self.call_with_context(prompt, conversation_history, use_claude=False)

        try:
            return extract_json_from_codex_output(response)
        except Exception:
            return {
                "verdict": "request_changes",
                "strengths": [],
                "issues": ["Review response parsing failed"],
                "suggestions": ["See raw response"],
                "rationale": response[:500],
                "_raw_response": response
            }

    def test(
        self,
        artifact_description: str,
        conversation_history: List[Dict]
    ) -> Dict:
        """
        Tester agent: Validate implementation.
        """
        if self.role != "tester":
            raise ValueError(f"Agent role {self.role} cannot test")

        prompt = f"""Test this implementation:
{artifact_description}

Describe:
- What tests would you run?
- What validation is needed?
- What would indicate success/failure?

Return JSON with: test_results, details, verdict (ready/needs_fixes), issues_found."""

        response = self.call_with_context(prompt, conversation_history, use_claude=False)

        try:
            return extract_json_from_codex_output(response)
        except Exception:
            return {
                "test_results": {"validation": "unknown"},
                "details": response[:500],
                "verdict": "needs_fixes",
                "issues_found": ["Test response parsing failed"],
                "_raw_response": response
            }

    def vote(
        self,
        proposal_summary: str,
        conversation_history: List[Dict]
    ) -> Dict:
        """
        Any agent: Vote on a proposal (approve/reject with rationale).
        """
        prompt = f"""Proposal for your vote:
{proposal_summary}

Based on your role as {self.role} and the conversation history, vote on this proposal.

Return JSON with:
{{
  "vote": "approve" or "reject",
  "rationale": "brief explanation of your vote"
}}"""

        response = self.call_with_context(prompt, conversation_history, use_claude=False)

        try:
            result = extract_json_from_codex_output(response)
            # Normalize vote field
            vote = result.get('vote', result.get('decision', result.get('verdict', 'reject')))
            if vote.lower() in ['approve', 'approved', 'yes', 'accept']:
                vote = 'approve'
            else:
                vote = 'reject'
            return {
                "vote": vote,
                "rationale": result.get('rationale', result.get('reason', 'No rationale provided'))
            }
        except Exception:
            # Conservative default: reject if we can't parse
            return {
                "vote": "reject",
                "rationale": f"Vote parsing failed. Raw: {response[:200]}"
            }
