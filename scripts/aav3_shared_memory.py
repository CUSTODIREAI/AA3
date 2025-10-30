#!/usr/bin/env python3
"""
AAv3 Shared Memory - Conversation Context for Multi-Agent Deliberation

All agents read/write to shared conversation memory.
This enables agent-to-agent communication and consensus building.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    """A message in the agent conversation."""
    from_agent: str
    role: str  # Agent's role (planner, coder, reviewer, etc.)
    content: str
    message_type: str  # proposal, question, answer, decision, artifact
    timestamp: str
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "from_agent": self.from_agent,
            "role": self.role,
            "content": self.content,
            "message_type": self.message_type,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


@dataclass
class Artifact:
    """An artifact created during deliberation (code, docs, etc.)."""
    name: str
    type: str  # dockerfile, python_module, markdown_doc, etc.
    content: str
    created_by: str
    version: int
    status: str  # draft, reviewed, approved, rejected
    timestamp: str

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": self.type,
            "content": self.content,
            "created_by": self.created_by,
            "version": self.version,
            "status": self.status,
            "timestamp": self.timestamp
        }


class SharedMemory:
    """
    Shared conversation memory for multi-agent deliberation.

    All agents can:
    - Read the full conversation history
    - Post new messages
    - Create/update artifacts
    - Vote on proposals
    - Check consensus status
    """

    def __init__(self, session_id: str, persistence_dir: str = "reports/aav3/sessions"):
        self.session_id = session_id
        self.persistence_dir = Path(persistence_dir)
        self.persistence_dir.mkdir(parents=True, exist_ok=True)

        self.messages: List[Message] = []
        self.artifacts: Dict[str, Artifact] = {}
        self.votes: Dict[str, Dict[str, str]] = {}  # {proposal_id: {agent: vote}}
        self.decisions: List[Dict] = []

        self.session_file = self.persistence_dir / f"{session_id}.json"

        # Load existing session if available
        if self.session_file.exists():
            self.load()

    def post_message(self, from_agent: str, role: str, content: str,
                     message_type: str = "message", metadata: Dict = None) -> Message:
        """Post a message to shared memory."""
        msg = Message(
            from_agent=from_agent,
            role=role,
            content=content,
            message_type=message_type,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        self.messages.append(msg)
        self.save()
        return msg

    def get_messages(self, from_role: str = None, message_type: str = None) -> List[Message]:
        """Get messages, optionally filtered by role or type."""
        messages = self.messages
        if from_role:
            messages = [m for m in messages if m.role == from_role]
        if message_type:
            messages = [m for m in messages if m.message_type == message_type]
        return messages

    def get_conversation_history(self, last_n: int = None) -> str:
        """Get formatted conversation history as string."""
        messages = self.messages[-last_n:] if last_n else self.messages

        lines = []
        for msg in messages:
            lines.append(f"[{msg.role}] {msg.from_agent}:")
            lines.append(f"  {msg.content}")
            lines.append("")

        return "\n".join(lines)

    def get_messages_as_dicts(self, last_n: int = None) -> List[Dict]:
        """Get conversation messages as list of dicts for agent processing."""
        messages = self.messages[-last_n:] if last_n else self.messages
        return [msg.to_dict() for msg in messages]

    def create_artifact(self, name: str, type: str, content: str,
                       created_by: str, status: str = "draft") -> Artifact:
        """Create or update an artifact."""
        if name in self.artifacts:
            # Update existing artifact (increment version)
            old = self.artifacts[name]
            artifact = Artifact(
                name=name,
                type=type,
                content=content,
                created_by=created_by,
                version=old.version + 1,
                status=status,
                timestamp=datetime.now().isoformat()
            )
        else:
            # Create new artifact
            artifact = Artifact(
                name=name,
                type=type,
                content=content,
                created_by=created_by,
                version=1,
                status=status,
                timestamp=datetime.now().isoformat()
            )

        self.artifacts[name] = artifact
        self.save()
        return artifact

    def get_artifact(self, name: str) -> Optional[Artifact]:
        """Get artifact by name."""
        return self.artifacts.get(name)

    def list_artifacts(self, type: str = None, status: str = None) -> List[Artifact]:
        """List artifacts, optionally filtered."""
        artifacts = list(self.artifacts.values())
        if type:
            artifacts = [a for a in artifacts if a.type == type]
        if status:
            artifacts = [a for a in artifacts if a.status == status]
        return artifacts

    def vote(self, proposal_id: str, agent: str, vote: str):
        """
        Cast a vote on a proposal.

        vote: "approve", "reject", "abstain"
        """
        if proposal_id not in self.votes:
            self.votes[proposal_id] = {}

        self.votes[proposal_id][agent] = vote
        self.save()

    def get_votes(self, proposal_id: str) -> Dict[str, str]:
        """Get all votes for a proposal."""
        return self.votes.get(proposal_id, {})

    def check_consensus(self, proposal_id: str, required_approval_ratio: float = 0.67) -> Dict:
        """
        Check if consensus reached on a proposal.

        Returns: {
            "consensus": bool,
            "approve": int,
            "reject": int,
            "abstain": int,
            "ratio": float
        }
        """
        votes = self.get_votes(proposal_id)

        approve = sum(1 for v in votes.values() if v == "approve")
        reject = sum(1 for v in votes.values() if v == "reject")
        abstain = sum(1 for v in votes.values() if v == "abstain")
        total = len(votes)

        if total == 0:
            return {"consensus": False, "approve": 0, "reject": 0, "abstain": 0, "ratio": 0.0}

        ratio = approve / total
        consensus = ratio >= required_approval_ratio

        return {
            "consensus": consensus,
            "approve": approve,
            "reject": reject,
            "abstain": abstain,
            "ratio": ratio
        }

    def record_decision(self, decision: str, rationale: str, agents_involved: List[str]):
        """Record a consensus decision."""
        self.decisions.append({
            "decision": decision,
            "rationale": rationale,
            "agents_involved": agents_involved,
            "timestamp": datetime.now().isoformat()
        })
        self.save()

    def save(self):
        """Persist memory to disk."""
        data = {
            "session_id": self.session_id,
            "messages": [m.to_dict() for m in self.messages],
            "artifacts": {name: a.to_dict() for name, a in self.artifacts.items()},
            "votes": self.votes,
            "decisions": self.decisions
        }

        with open(self.session_file, 'w') as f:
            json.dump(data, f, indent=2)

    def load(self):
        """Load memory from disk."""
        with open(self.session_file, 'r') as f:
            data = json.load(f)

        self.messages = [Message(**m) for m in data.get("messages", [])]
        self.artifacts = {
            name: Artifact(**a)
            for name, a in data.get("artifacts", {}).items()
        }
        self.votes = data.get("votes", {})
        self.decisions = data.get("decisions", [])

    def get_summary(self) -> str:
        """Get session summary."""
        return f"""
Session: {self.session_id}
Messages: {len(self.messages)}
Artifacts: {len(self.artifacts)}
Decisions: {len(self.decisions)}
Latest artifacts: {', '.join(a.name for a in list(self.artifacts.values())[-3:])}
"""


if __name__ == "__main__":
    # Test shared memory
    print("Testing AAv3 Shared Memory...")

    memory = SharedMemory("test_session")

    # Agent conversation
    memory.post_message("agent_1", "planner", "We should use CUDA 12.4 for RTX 4090", "proposal")
    memory.post_message("agent_2", "researcher", "Confirmed - CUDA 12.4 is optimal", "answer")
    memory.post_message("agent_3", "coder", "I'll write the Dockerfile", "decision")

    # Create artifact
    dockerfile = """FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04
RUN apt-get update && apt-get install -y python3-pip
"""
    memory.create_artifact(
        name="Dockerfile",
        type="dockerfile",
        content=dockerfile,
        created_by="agent_3"
    )

    # Voting
    memory.vote("dockerfile_v1", "agent_1", "approve")
    memory.vote("dockerfile_v1", "agent_2", "approve")
    memory.vote("dockerfile_v1", "agent_3", "approve")

    consensus = memory.check_consensus("dockerfile_v1")
    print(f"\nConsensus: {consensus}")

    print(f"\nConversation:\n{memory.get_conversation_history()}")
    print(f"\nSummary:\n{memory.get_summary()}")
