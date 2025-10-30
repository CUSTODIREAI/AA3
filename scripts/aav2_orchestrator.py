#!/usr/bin/env python3
"""
AAv2 Orchestrator - Multi-Agent Coordination

Implements Anthropic's orchestrator-worker pattern:
- Spawns specialized agents (executor, verifier, reviewer)
- Coordinates via structured artifacts (MetaGPT pattern)
- Manages execution flow with retry loops
- Synthesizes final results
"""
from __future__ import annotations
import sys, time, uuid
from pathlib import Path
from typing import List, Dict, Any

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.aav2_executor import execute_task
from scripts.aav2_verifier import verify_criteria
from scripts.aav2_reviewer import review_failures
from scripts.aav2_artifacts import (
    SynthesisReport, timestamp_now, save_artifact
)


class AAv2Orchestrator:
    """
    Multi-agent orchestrator implementing Anthropic's pattern.

    Coordinates:
    - Executor agents (run commands)
    - Verifier agents (check criteria)
    - Reviewer agents (diagnose failures)
    - Fixer agents (apply fixes - uses executor)
    """

    def __init__(self, task_file: str, max_rounds: int = 3, artifacts_dir: str = "reports/aav2"):
        self.task_file = task_file
        self.max_rounds = max_rounds
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        self.orchestrator_id = f"orchestrator_{uuid.uuid4().hex[:8]}"
        self.agents_spawned = []
        self.artifacts_generated = []
        self.timestamp_start = timestamp_now()

    def log(self, message: str):
        """Log orchestrator messages"""
        print(f"[Orchestrator {self.orchestrator_id}] {message}")

    def spawn_executor(self, agent_id: str = None, enable_reflection: bool = True) -> tuple[bool, str]:
        """Spawn executor agent"""
        if agent_id is None:
            agent_id = f"executor_{uuid.uuid4().hex[:8]}"

        self.log(f"Spawning Executor Agent: {agent_id}")

        transcript_path = self.artifacts_dir / f"{agent_id}_transcript.json"

        self.agents_spawned.append({
            "type": "executor",
            "agent_id": agent_id,
            "timestamp": timestamp_now(),
            "reflection_enabled": enable_reflection
        })

        # Execute task
        transcript = execute_task(
            task_file=self.task_file,
            agent_id=agent_id,
            enable_reflection=enable_reflection
        )

        if transcript is None:
            return False, None

        # Save transcript artifact
        save_artifact(transcript, str(transcript_path))
        self.artifacts_generated.append(str(transcript_path))

        success = transcript.failed_commands == 0
        self.log(f"Executor {'completed successfully' if success else 'completed with failures'}")

        return success, str(transcript_path)

    def spawn_verifier(self, transcript_path: str, agent_id: str = None) -> tuple[bool, str]:
        """Spawn verifier agent"""
        if agent_id is None:
            agent_id = f"verifier_{uuid.uuid4().hex[:8]}"

        self.log(f"Spawning Verifier Agent: {agent_id}")

        report_path = self.artifacts_dir / f"{agent_id}_report.json"

        self.agents_spawned.append({
            "type": "verifier",
            "agent_id": agent_id,
            "timestamp": timestamp_now()
        })

        # Verify criteria
        report = verify_criteria(
            task_file=self.task_file,
            transcript_path=transcript_path,
            agent_id=agent_id
        )

        if report is None:
            return False, None

        # Save report artifact
        save_artifact(report, str(report_path))
        self.artifacts_generated.append(str(report_path))

        self.log(f"Verifier {'PASSED' if report.overall_pass else 'FAILED'}")

        return report.overall_pass, str(report_path)

    def spawn_reviewer(self, transcript_path: str, report_path: str, agent_id: str = None) -> tuple[bool, str]:
        """Spawn reviewer agent"""
        if agent_id is None:
            agent_id = f"reviewer_{uuid.uuid4().hex[:8]}"

        self.log(f"Spawning Reviewer Agent: {agent_id}")

        diagnosis_path = self.artifacts_dir / f"{agent_id}_diagnosis.json"

        self.agents_spawned.append({
            "type": "reviewer",
            "agent_id": agent_id,
            "timestamp": timestamp_now()
        })

        # Review failures
        diagnosis = review_failures(
            transcript_path=transcript_path,
            report_path=report_path,
            agent_id=agent_id
        )

        if diagnosis is None:
            return False, None

        # Save diagnosis artifact
        save_artifact(diagnosis, str(diagnosis_path))
        self.artifacts_generated.append(str(diagnosis_path))

        has_fixable = diagnosis.fixable_failures > 0
        self.log(f"Reviewer found {diagnosis.fixable_failures} fixable failures")

        return has_fixable, str(diagnosis_path)

    def run(self) -> SynthesisReport:
        """
        Execute full orchestration cycle.

        Flow:
        1. Spawn executor → Execute commands
        2. Spawn verifier → Check criteria
        3. If failed: Spawn reviewer → Diagnose
        4. If fixable: Retry (up to max_rounds)
        5. Synthesize results
        """
        self.log(f"Starting orchestration for task: {self.task_file}")
        self.log(f"Max rounds: {self.max_rounds}")
        print("")

        final_status = "incomplete"
        execution_round = 0

        for round_num in range(1, self.max_rounds + 1):
            execution_round = round_num
            self.log(f"=== Round {round_num}/{self.max_rounds} ===")
            print("")

            # Phase 1: Execute
            exec_success, transcript_path = self.spawn_executor()
            print("")

            if not exec_success:
                self.log("Execution failed - commands did not complete successfully")
                # Try verification anyway to see what passed
            else:
                self.log("Execution succeeded - all commands completed")

            # Phase 2: Verify
            verify_success, report_path = self.spawn_verifier(transcript_path)
            print("")

            if verify_success:
                self.log("Verification PASSED - task complete!")
                final_status = "complete"
                break

            self.log("Verification FAILED - criteria not met")

            # Phase 3: Review & diagnose
            has_fixable, diagnosis_path = self.spawn_reviewer(transcript_path, report_path)
            print("")

            if not has_fixable:
                self.log("No fixable failures found - manual intervention needed")
                final_status = "needs_human"
                break

            # Phase 4: Should we retry?
            if round_num < self.max_rounds:
                self.log(f"Will retry with fixes in round {round_num + 1}")
                print("")
                # In full version, would apply fixes from diagnosis
                # For now, just retry (demonstrates loop)
            else:
                self.log("Max rounds reached - stopping")
                final_status = "incomplete"

        # Synthesize results
        timestamp_end = timestamp_now()
        duration = (time.time() - time.mktime(time.strptime(self.timestamp_start[:19], "%Y-%m-%dT%H:%M:%S")))

        # Collect metrics
        executors = [a for a in self.agents_spawned if a["type"] == "executor"]
        verifiers = [a for a in self.agents_spawned if a["type"] == "verifier"]
        reviewers = [a for a in self.agents_spawned if a["type"] == "reviewer"]

        metrics = {
            "total_agents": len(self.agents_spawned),
            "executors_spawned": len(executors),
            "verifiers_spawned": len(verifiers),
            "reviewers_spawned": len(reviewers),
            "artifacts_generated": len(self.artifacts_generated),
            "rounds_executed": execution_round
        }

        synthesis = SynthesisReport(
            task_file=self.task_file,
            orchestrator_id=self.orchestrator_id,
            agents_spawned=self.agents_spawned,
            execution_rounds=execution_round,
            final_status=final_status,
            artifacts_generated=self.artifacts_generated,
            metrics=metrics,
            timestamp_start=self.timestamp_start,
            timestamp_end=timestamp_end,
            total_duration_sec=duration
        )

        # Save synthesis report
        synthesis_path = self.artifacts_dir / f"{self.orchestrator_id}_synthesis.json"
        save_artifact(synthesis, str(synthesis_path))

        self.log("=== Orchestration Complete ===")
        print("")
        print(f"Final Status: {final_status}")
        print(f"Rounds: {execution_round}/{self.max_rounds}")
        print(f"Agents spawned: {len(self.agents_spawned)}")
        print(f"Artifacts: {len(self.artifacts_generated)}")
        print(f"Duration: {duration:.2f}s")
        print(f"\nSynthesis report: {synthesis_path}")

        return synthesis


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="AAv2 Orchestrator - Multi-agent task execution")
    ap.add_argument("task", help="Path to task file with EXECUTE: and SUCCESS_CRITERIA blocks")
    ap.add_argument("--max-rounds", type=int, default=3, help="Maximum execution rounds (default: 3)")
    ap.add_argument("--artifacts-dir", default="reports/aav2", help="Directory for artifacts")
    args = ap.parse_args()

    if not Path(args.task).exists():
        print(f"ERROR: Task file not found: {args.task}")
        sys.exit(1)

    # Run orchestration
    orchestrator = AAv2Orchestrator(
        task_file=args.task,
        max_rounds=args.max_rounds,
        artifacts_dir=args.artifacts_dir
    )

    synthesis = orchestrator.run()

    # Exit code based on final status
    exit_code = 0 if synthesis.final_status == "complete" else 1
    sys.exit(exit_code)
