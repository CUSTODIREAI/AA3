#!/usr/bin/env python3
"""
AAv2 Structured Artifacts - MetaGPT Pattern

Agents communicate via structured documents (not chat messages).
Eliminates "unproductive chatter" and enables verification.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

@dataclass
class CommandExecution:
    """Single command execution result"""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    timestamp: str
    duration_sec: float
    success: bool

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class ExecutionTranscript:
    """Executor Agent Output - Complete execution history"""
    task_file: str
    agent_id: str
    commands_executed: List[CommandExecution]
    total_commands: int
    successful_commands: int
    failed_commands: int
    total_duration_sec: float
    timestamp_start: str
    timestamp_end: str

    def to_dict(self) -> dict:
        return {
            "artifact_type": "execution_transcript",
            "task_file": self.task_file,
            "agent_id": self.agent_id,
            "commands_executed": [c.to_dict() for c in self.commands_executed],
            "total_commands": self.total_commands,
            "successful_commands": self.successful_commands,
            "failed_commands": self.failed_commands,
            "total_duration_sec": self.total_duration_sec,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

@dataclass
class CriteriaCheck:
    """Single success criteria verification"""
    criteria_type: str  # file, command, grep
    description: str
    passed: bool
    details: str

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class VerificationReport:
    """Verifier Agent Output - Quality gates"""
    transcript_id: str
    agent_id: str
    criteria_checked: List[CriteriaCheck]
    total_criteria: int
    passed_criteria: int
    failed_criteria: int
    overall_pass: bool
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "artifact_type": "verification_report",
            "transcript_id": self.transcript_id,
            "agent_id": self.agent_id,
            "criteria_checked": [c.to_dict() for c in self.criteria_checked],
            "total_criteria": self.total_criteria,
            "passed_criteria": self.passed_criteria,
            "failed_criteria": self.failed_criteria,
            "overall_pass": self.overall_pass,
            "timestamp": self.timestamp
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

@dataclass
class FailureDiagnosis:
    """Single failure analysis"""
    command: str
    error_type: str  # syntax, permission, not_found, network, etc.
    root_cause: str
    suggested_fix: str
    confidence: float  # 0.0-1.0

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class DiagnosisDocument:
    """Reviewer Agent Output - Error analysis & fixes"""
    verification_report_id: str
    agent_id: str
    failures_analyzed: List[FailureDiagnosis]
    total_failures: int
    fixable_failures: int
    unfixable_failures: int
    recommended_actions: List[str]
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "artifact_type": "diagnosis_document",
            "verification_report_id": self.verification_report_id,
            "agent_id": self.agent_id,
            "failures_analyzed": [f.to_dict() for f in self.failures_analyzed],
            "total_failures": self.total_failures,
            "fixable_failures": self.fixable_failures,
            "unfixable_failures": self.unfixable_failures,
            "recommended_actions": self.recommended_actions,
            "timestamp": self.timestamp
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

@dataclass
class ReflectionResult:
    """Self-critique before command execution"""
    command: str
    potential_issues: List[str]
    risk_level: str  # low, medium, high
    alternative_command: Optional[str]
    proceed: bool  # True if safe to proceed, False if alternative recommended
    reasoning: str

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class SynthesisReport:
    """Orchestrator Output - Final task summary"""
    task_file: str
    orchestrator_id: str
    agents_spawned: List[Dict[str, Any]]  # List of agent metadata
    execution_rounds: int
    final_status: str  # complete, incomplete, failed, needs_human
    artifacts_generated: List[str]  # Paths to all artifacts
    metrics: Dict[str, Any]
    timestamp_start: str
    timestamp_end: str
    total_duration_sec: float

    def to_dict(self) -> dict:
        return {
            "artifact_type": "synthesis_report",
            "task_file": self.task_file,
            "orchestrator_id": self.orchestrator_id,
            "agents_spawned": self.agents_spawned,
            "execution_rounds": self.execution_rounds,
            "final_status": self.final_status,
            "artifacts_generated": self.artifacts_generated,
            "metrics": self.metrics,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "total_duration_sec": self.total_duration_sec
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

# Helper functions

def save_artifact(artifact: Any, path: str) -> None:
    """Save structured artifact to disk"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(artifact.to_json())

def load_artifact(path: str) -> dict:
    """Load structured artifact from disk"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def timestamp_now() -> str:
    """Current timestamp in ISO format"""
    return datetime.now().isoformat()
