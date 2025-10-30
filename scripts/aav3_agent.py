#!/usr/bin/env python3
"""
AAv3 Base Agent - Runs INSIDE Claude Code

KEY INSIGHT: This system runs INSIDE Claude Code.
Each agent is Claude Code reasoning with a specific role prompt.

NO external API calls - we USE the tools we already have:
- Read, Write, Edit (file operations)
- Grep, Glob (code search)
- Bash (execution)
- WebSearch (research)

This is the proper architecture: leverage the fact we're IN Claude Code.
"""
from __future__ import annotations
import uuid
from typing import Dict, List, Optional
from pathlib import Path

from scripts.aav3_shared_memory import SharedMemory


class AgentAction:
    """
    An action an agent can take.

    Since we're IN Claude Code, actions map to our tools:
    - read_file → Read tool
    - write_file → Write tool
    - edit_file → Edit tool
    - search_code → Grep tool
    - find_files → Glob tool
    - execute_command → Bash tool
    - web_search → WebSearch tool
    - create_artifact → SharedMemory.create_artifact
    - post_message → SharedMemory.post_message
    - vote → SharedMemory.vote
    """

    def __init__(self, action_type: str, parameters: Dict):
        self.action_type = action_type
        self.parameters = parameters
        self.result = None
        self.success = False
        self.error = None


class AAv3Agent:
    """
    Base agent that runs INSIDE Claude Code.

    This is NOT an external API call.
    This IS Claude Code reasoning with a role prompt.
    """

    def __init__(self, agent_id: str, role: str, shared_memory: SharedMemory):
        self.agent_id = agent_id
        self.role = role  # planner, researcher, coder, reviewer, tester
        self.shared_memory = shared_memory

        # Role-specific system prompts
        self.system_prompts = {
            "planner": """You are a strategic planner agent. Your role:
- Break down complex tasks into concrete steps
- Identify unknowns that need research
- Propose approaches for consensus
- Think about architecture and design
- Communicate plans clearly to other agents""",

            "researcher": """You are a research agent. Your role:
- Web search for latest information
- Find documentation and best practices
- Verify technical details
- Report findings to other agents
- Recommend optimal approaches based on research""",

            "coder": """You are a coding agent. Your role:
- Write high-quality code (Python, Dockerfiles, configs, etc.)
- Implement designs proposed by planners
- Follow best practices and patterns
- Create artifacts (files, modules, docs)
- Explain your implementation choices""",

            "reviewer": """You are a code reviewer agent. Your role:
- Review code/artifacts created by others
- Check for bugs, security issues, best practices
- Suggest improvements
- Approve or request changes
- Provide constructive feedback""",

            "tester": """You are a testing agent. Your role:
- Build and test artifacts (Docker images, code, etc.)
- Run validation commands
- Report test results
- Identify failures and their causes
- Verify quality before approval"""
        }

    def get_system_prompt(self) -> str:
        """Get system prompt for this agent's role."""
        return self.system_prompts.get(self.role, "You are a helpful AI agent.")

    def reason(self, context: str, question: str) -> str:
        """
        Agent reasons about a question given context.

        THIS IS THE KEY: We're IN Claude Code, so this is just
        me (Claude) reasoning with the role prompt.

        In practice, orchestrator calls this and I respond
        as if I'm this agent role.
        """
        system = self.get_system_prompt()

        # In a standalone implementation, this would be where
        # the agent "thinks" using LLM. But we're IN Claude Code,
        # so this is handled by the orchestrator showing the
        # role prompt and letting me respond.

        # For now, return a placeholder that orchestrator will fill
        return f"[{self.role} reasoning on: {question[:50]}...]"

    def propose(self, proposal: str) -> str:
        """Post a proposal to shared memory."""
        msg = self.shared_memory.post_message(
            from_agent=self.agent_id,
            role=self.role,
            content=proposal,
            message_type="proposal"
        )
        return f"proposal_{msg.timestamp}"

    def respond(self, content: str, message_type: str = "message"):
        """Post a response to shared memory."""
        self.shared_memory.post_message(
            from_agent=self.agent_id,
            role=self.role,
            content=content,
            message_type=message_type
        )

    def vote_on_proposal(self, proposal_id: str, vote: str):
        """Vote on a proposal."""
        self.shared_memory.vote(proposal_id, self.agent_id, vote)

    def create_artifact(self, name: str, type: str, content: str, status: str = "draft"):
        """Create an artifact."""
        return self.shared_memory.create_artifact(
            name=name,
            type=type,
            content=content,
            created_by=self.agent_id,
            status=status
        )

    def get_conversation_context(self, last_n: int = 10) -> str:
        """Get recent conversation for context."""
        return self.shared_memory.get_conversation_history(last_n=last_n)

    def get_artifacts(self) -> List:
        """Get all artifacts in shared memory."""
        return self.shared_memory.list_artifacts()

    # Tool wrappers (these would call Claude Code tools)
    # In practice, orchestrator coordinates these with real tool calls

    def read_file_action(self, file_path: str) -> AgentAction:
        """Request to read a file (orchestrator will use Read tool)."""
        return AgentAction("read_file", {"file_path": file_path})

    def write_file_action(self, file_path: str, content: str) -> AgentAction:
        """Request to write a file (orchestrator will use Write tool)."""
        return AgentAction("write_file", {"file_path": file_path, "content": content})

    def edit_file_action(self, file_path: str, old_string: str, new_string: str) -> AgentAction:
        """Request to edit a file (orchestrator will use Edit tool)."""
        return AgentAction("edit_file", {
            "file_path": file_path,
            "old_string": old_string,
            "new_string": new_string
        })

    def search_code_action(self, pattern: str, path: str = ".") -> AgentAction:
        """Request to search code (orchestrator will use Grep tool)."""
        return AgentAction("search_code", {"pattern": pattern, "path": path})

    def find_files_action(self, pattern: str) -> AgentAction:
        """Request to find files (orchestrator will use Glob tool)."""
        return AgentAction("find_files", {"pattern": pattern})

    def execute_command_action(self, command: str) -> AgentAction:
        """Request to execute command (orchestrator will use Bash tool)."""
        return AgentAction("execute_command", {"command": command})

    def web_search_action(self, query: str) -> AgentAction:
        """Request web search (orchestrator will use WebSearch tool)."""
        return AgentAction("web_search", {"query": query})


# Specialized agent types

class PlannerAgent(AAv3Agent):
    """Strategic planning agent."""
    def __init__(self, shared_memory: SharedMemory):
        super().__init__(
            agent_id=f"planner_{uuid.uuid4().hex[:6]}",
            role="planner",
            shared_memory=shared_memory
        )


class ResearcherAgent(AAv3Agent):
    """Research and information gathering agent."""
    def __init__(self, shared_memory: SharedMemory):
        super().__init__(
            agent_id=f"researcher_{uuid.uuid4().hex[:6]}",
            role="researcher",
            shared_memory=shared_memory
        )


class CoderAgent(AAv3Agent):
    """Coding and implementation agent."""
    def __init__(self, shared_memory: SharedMemory):
        super().__init__(
            agent_id=f"coder_{uuid.uuid4().hex[:6]}",
            role="coder",
            shared_memory=shared_memory
        )


class ReviewerAgent(AAv3Agent):
    """Code review and quality assurance agent."""
    def __init__(self, shared_memory: SharedMemory):
        super().__init__(
            agent_id=f"reviewer_{uuid.uuid4().hex[:6]}",
            role="reviewer",
            shared_memory=shared_memory
        )


class TesterAgent(AAv3Agent):
    """Testing and validation agent."""
    def __init__(self, shared_memory: SharedMemory):
        super().__init__(
            agent_id=f"tester_{uuid.uuid4().hex[:6]}",
            role="tester",
            shared_memory=shared_memory
        )


if __name__ == "__main__":
    # Test agent creation
    print("Testing AAv3 Agents...")

    from scripts.aav3_shared_memory import SharedMemory

    memory = SharedMemory("test_agents")

    # Create agents
    planner = PlannerAgent(memory)
    researcher = ResearcherAgent(memory)
    coder = CoderAgent(memory)
    reviewer = ReviewerAgent(memory)
    tester = TesterAgent(memory)

    print(f"\nCreated agents:")
    print(f"  Planner: {planner.agent_id}")
    print(f"  Researcher: {researcher.agent_id}")
    print(f"  Coder: {coder.agent_id}")
    print(f"  Reviewer: {reviewer.agent_id}")
    print(f"  Tester: {tester.agent_id}")

    # Test conversation
    planner.respond("We should use CUDA 12.4 for RTX 4090", "proposal")
    researcher.respond("Confirmed - CUDA 12.4 is optimal based on research", "answer")
    coder.respond("I'll implement the Dockerfile", "decision")

    print(f"\nConversation:\n{memory.get_conversation_history()}")

    # Test artifact creation
    coder.create_artifact(
        name="Dockerfile",
        type="dockerfile",
        content="FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04",
        status="draft"
    )

    print(f"\nArtifacts: {len(memory.list_artifacts())}")
