#!/usr/bin/env python3
"""
AAv2.5 Enhanced Orchestrator - Full Multi-Agent Collaboration

This is the COMPLETE system with:
- Real LLM integration (Claude + Codex)
- Automatic fix application (Fixer agent)
- Loop detection with breakout
- Parallel execution (infrastructure ready)
- Context auto-compaction
- Full Executor → Verifier → Reviewer → Fixer cycle

This is what "2 LLMs working together" means in 2025.
"""
from __future__ import annotations
import sys, time, uuid
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import concurrent.futures

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.aav2_artifacts import (
    ExecutionTranscript, VerificationReport, DiagnosisDocument, SynthesisReport,
    timestamp_now, save_artifact, load_artifact
)
from scripts.aav2_executor import execute_task
from scripts.aav2_verifier import verify_task
from scripts.aav2_reviewer import review_failures
from scripts.aav2_fixer import apply_fix
from scripts.aav2_loop_detector import LoopDetector
from scripts.aav2_llm_integration import compress_context_with_llm, generate_plan_with_llm


class AAv25Orchestrator:
    """
    Enhanced orchestrator with full AAv2.5 features.

    New in v2.5:
    - Real LLM diagnosis (Codex)
    - Automatic fix application
    - Loop detection
    - Parallel execution support
    - Context compaction
    """

    def __init__(
        self,
        task_file: str,
        max_rounds: int = 5,
        artifacts_dir: str = "reports/aav2",
        enable_parallel: bool = False,
        enable_fixer: bool = True,
        enable_loop_detection: bool = True,
        context_threshold: int = 8000
    ):
        self.task_file = task_file
        self.max_rounds = max_rounds
        self.artifacts_dir = Path(artifacts_dir)
        self.enable_parallel = enable_parallel
        self.enable_fixer = enable_fixer
        self.enable_loop_detection = enable_loop_detection
        self.context_threshold = context_threshold

        self.orchestrator_id = f"orch_v2.5_{uuid.uuid4().hex[:8]}"
        self.start_time = time.time()
        self.agents_spawned = []
        self.context = ""

        # Loop detector
        self.loop_detector = LoopDetector() if enable_loop_detection else None

        # Create artifacts directory
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> str:
        """
        Run full AAv2.5 orchestration workflow.

        Returns: Final status (complete, incomplete, failed, needs_human)
        """
        print(f"\n{'='*60}")
        print(f"AAv2.5 ENHANCED ORCHESTRATOR")
        print(f"{'='*60}")
        print(f"ID: {self.orchestrator_id}")
        print(f"Task: {self.task_file}")
        print(f"Max rounds: {self.max_rounds}")
        print(f"Features: Fixer={self.enable_fixer}, LoopDetect={self.enable_loop_detection}, Parallel={self.enable_parallel}")
        print("")

        # Phase 0: LLM-generated plan (optional)
        # self._generate_plan()  # Uncomment for AI-planned execution

        final_status = "incomplete"

        for round_num in range(1, self.max_rounds + 1):
            print(f"\n{'='*60}")
            print(f"ROUND {round_num}/{self.max_rounds}")
            print(f"{'='*60}\n")

            # Phase 1: Execute
            exec_success, transcript_path = self.spawn_executor(round_num)

            if not exec_success:
                print(f"\n[Round {round_num}] Execution failed completely")
                final_status = "failed"
                break

            # Phase 2: Verify
            verify_success, report_path = self.spawn_verifier(transcript_path, round_num)

            if verify_success:
                print(f"\n[Round {round_num}] ✅ All criteria passed - TASK COMPLETE")
                final_status = "complete"
                break

            print(f"\n[Round {round_num}] ❌ Verification failed - analyzing...")

            # Phase 3: Review & diagnose with REAL LLM
            has_fixable, diagnosis_path = self.spawn_reviewer(transcript_path, report_path, round_num)

            if not has_fixable:
                print(f"\n[Round {round_num}] No fixable failures - needs human intervention")
                final_status = "needs_human"
                break

            # Phase 4: Loop detection (NEW in v2.5)
            if self.enable_loop_detection:
                loop_result = self._check_loop(transcript_path)
                if loop_result["is_loop"]:
                    print(f"\n[Round {round_num}] ⚠️ LOOP DETECTED: {loop_result['pattern']}")
                    print(f"Confidence: {loop_result['confidence']:.0%}")

                    # Get breakout suggestion
                    breakout = self.loop_detector.suggest_breakout()
                    print(f"Breakout strategy: {breakout}")

                    # Decide whether to continue or abort
                    if round_num >= self.max_rounds - 1:
                        print(f"Max rounds approaching - aborting")
                        final_status = "needs_human"
                        break

            # Phase 5: Automatic fixing (NEW in v2.5)
            if self.enable_fixer:
                fix_success, fix_transcript_path = self.spawn_fixer(diagnosis_path, round_num)

                if fix_success:
                    print(f"\n[Round {round_num}] Fixes applied successfully - retrying verification")
                    # Continue to next round
                else:
                    print(f"\n[Round {round_num}] Fixes failed - may need human intervention")
                    # Still continue, executor will retry

            # Phase 6: Context compaction (if needed)
            if len(self.context) > self.context_threshold:
                print(f"\n[Context Compaction] Current size: {len(self.context)} chars")
                self.context = compress_context_with_llm(self.context, max_length=2000)
                print(f"Compressed to: {len(self.context)} chars")

            # Check if we're out of rounds
            if round_num >= self.max_rounds:
                print(f"\n[Max rounds reached] Task incomplete after {self.max_rounds} attempts")
                final_status = "incomplete"

        # Generate synthesis report
        duration = time.time() - self.start_time
        self._generate_synthesis_report(final_status, round_num, duration)

        print(f"\n{'='*60}")
        print(f"ORCHESTRATION COMPLETE")
        print(f"{'='*60}")
        print(f"Status: {final_status}")
        print(f"Rounds: {round_num}")
        print(f"Agents spawned: {len(self.agents_spawned)}")
        print(f"Duration: {duration:.2f}s")
        print("")

        return final_status

    def spawn_executor(self, round_num: int) -> Tuple[bool, str]:
        """Spawn executor agent."""
        agent_id = f"{self.orchestrator_id}_executor_r{round_num}"
        self.agents_spawned.append({"type": "executor", "id": agent_id, "round": round_num})

        print(f"[Spawning Executor Agent]")
        print(f"Agent ID: {agent_id}")

        try:
            transcript = execute_task(self.task_file, agent_id=agent_id)

            if transcript is None:
                return False, None

            # Save artifact
            transcript_path = self.artifacts_dir / f"{agent_id}_transcript.json"
            save_artifact(transcript, str(transcript_path))

            # Update context
            self.context += f"\n[Executor Round {round_num}] Executed {transcript.total_commands} commands, {transcript.successful_commands} succeeded"

            # Update loop detector
            if self.enable_loop_detection and transcript.commands_executed:
                last_cmd = transcript.commands_executed[-1]["command"]
                self.loop_detector.add_command(last_cmd)

            success = transcript.failed_commands == 0
            return success, str(transcript_path)

        except Exception as e:
            print(f"[ERROR] Executor failed: {e}")
            return False, None

    def spawn_verifier(self, transcript_path: str, round_num: int) -> Tuple[bool, str]:
        """Spawn verifier agent."""
        agent_id = f"{self.orchestrator_id}_verifier_r{round_num}"
        self.agents_spawned.append({"type": "verifier", "id": agent_id, "round": round_num})

        print(f"[Spawning Verifier Agent]")
        print(f"Agent ID: {agent_id}")

        try:
            report = verify_task(self.task_file, transcript_path, agent_id=agent_id)

            if report is None:
                return False, None

            # Save artifact
            report_path = self.artifacts_dir / f"{agent_id}_report.json"
            save_artifact(report, str(report_path))

            # Update context
            passed = sum(1 for c in report.criteria_checked if c.passed)
            total = len(report.criteria_checked)
            self.context += f"\n[Verifier Round {round_num}] {passed}/{total} criteria passed"

            return report.overall_pass, str(report_path)

        except Exception as e:
            print(f"[ERROR] Verifier failed: {e}")
            return False, None

    def spawn_reviewer(self, transcript_path: str, report_path: str, round_num: int) -> Tuple[bool, str]:
        """Spawn reviewer agent with REAL LLM diagnosis."""
        agent_id = f"{self.orchestrator_id}_reviewer_r{round_num}"
        self.agents_spawned.append({"type": "reviewer", "id": agent_id, "round": round_num})

        print(f"[Spawning Reviewer Agent (Codex)]")
        print(f"Agent ID: {agent_id}")

        try:
            # Get task context for better diagnosis
            with open(self.task_file, 'r') as f:
                task_context = f.read()[:500]

            diagnosis = review_failures(
                transcript_path=transcript_path,
                report_path=report_path,
                agent_id=agent_id,
                task_context=task_context  # NEW: Pass context for better LLM diagnosis
            )

            if diagnosis is None:
                return False, None

            # Save artifact
            diagnosis_path = self.artifacts_dir / f"{agent_id}_diagnosis.json"
            save_artifact(diagnosis, str(diagnosis_path))

            # Update context
            fixable = diagnosis.fixable_failures
            total = diagnosis.total_failures
            self.context += f"\n[Reviewer Round {round_num}] {fixable}/{total} failures are fixable"

            has_fixable = diagnosis.fixable_failures > 0
            return has_fixable, str(diagnosis_path)

        except Exception as e:
            print(f"[ERROR] Reviewer failed: {e}")
            return False, None

    def spawn_fixer(self, diagnosis_path: str, round_num: int) -> Tuple[bool, str]:
        """Spawn fixer agent to apply fixes (NEW in v2.5)."""
        agent_id = f"{self.orchestrator_id}_fixer_r{round_num}"
        self.agents_spawned.append({"type": "fixer", "id": agent_id, "round": round_num})

        print(f"[Spawning Fixer Agent (Claude)]")
        print(f"Agent ID: {agent_id}")

        try:
            transcript = apply_fix(
                diagnosis_path=diagnosis_path,
                original_task_path=self.task_file,
                agent_id=agent_id,
                use_claude=True  # Use Claude for fix generation
            )

            if transcript is None:
                return False, None

            # Save artifact
            transcript_path = self.artifacts_dir / f"{agent_id}_transcript.json"
            save_artifact(transcript, str(transcript_path))

            # Update context
            self.context += f"\n[Fixer Round {round_num}] Applied {transcript.successful_commands}/{transcript.total_commands} fixes"

            success = transcript.failed_commands == 0
            return success, str(transcript_path)

        except Exception as e:
            print(f"[ERROR] Fixer failed: {e}")
            return False, None

    def _check_loop(self, transcript_path: str) -> Dict:
        """Check for loops in execution (NEW in v2.5)."""
        if not self.enable_loop_detection:
            return {"is_loop": False}

        # The loop detector already has commands added in spawn_executor
        return self.loop_detector.detect_loop()

    def _generate_plan(self):
        """Optional: Use LLM to generate execution plan."""
        print("[Generating Execution Plan with LLM]")

        with open(self.task_file, 'r') as f:
            task_description = f.read()

        plan = generate_plan_with_llm(task_description)

        print("Generated plan:")
        for i, step in enumerate(plan, 1):
            print(f"  {i}. {step}")
        print("")

    def spawn_executors_parallel(self, task_chunks: List[str]) -> List[str]:
        """
        Spawn multiple executors in parallel (NEW in v2.5).

        This is the Anthropic-proven 90% improvement pattern.
        """
        if not self.enable_parallel:
            raise RuntimeError("Parallel execution not enabled")

        print(f"[Spawning {len(task_chunks)} Parallel Executors]")

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(3, len(task_chunks))) as executor:
            futures = []

            for i, chunk_file in enumerate(task_chunks):
                agent_id = f"{self.orchestrator_id}_executor_parallel_{i}"
                self.agents_spawned.append({"type": "executor", "id": agent_id, "parallel": True})

                future = executor.submit(execute_task, chunk_file, agent_id)
                futures.append((future, agent_id))

            # Wait for all to complete
            results = []
            for future, agent_id in futures:
                try:
                    transcript = future.result()
                    if transcript:
                        transcript_path = self.artifacts_dir / f"{agent_id}_transcript.json"
                        save_artifact(transcript, str(transcript_path))
                        results.append(str(transcript_path))
                        print(f"  ✅ {agent_id}: {transcript.successful_commands}/{transcript.total_commands} commands succeeded")
                    else:
                        print(f"  ❌ {agent_id}: failed")
                except Exception as e:
                    print(f"  ❌ {agent_id}: {e}")

        return results

    def _generate_synthesis_report(self, status: str, rounds: int, duration: float):
        """Generate final synthesis report."""
        synthesis = SynthesisReport(
            orchestrator_id=self.orchestrator_id,
            task_file=self.task_file,
            agents_spawned=self.agents_spawned,
            total_rounds=rounds,
            final_status=status,
            duration_seconds=duration,
            artifacts_directory=str(self.artifacts_dir),
            timestamp=timestamp_now()
        )

        # Save synthesis
        synthesis_path = self.artifacts_dir / f"{self.orchestrator_id}_synthesis.json"
        save_artifact(synthesis, str(synthesis_path))

        print(f"\n[Synthesis Report Saved]")
        print(f"Path: {synthesis_path}")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="AAv2.5 Enhanced Orchestrator - Full multi-agent collaboration")
    ap.add_argument("task", help="Path to task file")
    ap.add_argument("--max-rounds", type=int, default=5, help="Maximum execution rounds")
    ap.add_argument("--artifacts-dir", default="reports/aav2", help="Directory for artifacts")
    ap.add_argument("--enable-parallel", action="store_true", help="Enable parallel execution (experimental)")
    ap.add_argument("--disable-fixer", action="store_true", help="Disable automatic fix application")
    ap.add_argument("--disable-loop-detection", action="store_true", help="Disable loop detection")
    ap.add_argument("--context-threshold", type=int, default=8000, help="Context size threshold for compaction")
    args = ap.parse_args()

    if not Path(args.task).exists():
        print(f"ERROR: Task file not found: {args.task}")
        sys.exit(1)

    # Create orchestrator
    orchestrator = AAv25Orchestrator(
        task_file=args.task,
        max_rounds=args.max_rounds,
        artifacts_dir=args.artifacts_dir,
        enable_parallel=args.enable_parallel,
        enable_fixer=not args.disable_fixer,
        enable_loop_detection=not args.disable_loop_detection,
        context_threshold=args.context_threshold
    )

    # Run orchestration
    final_status = orchestrator.run()

    # Exit with appropriate code
    exit_codes = {
        "complete": 0,
        "incomplete": 1,
        "failed": 2,
        "needs_human": 3
    }

    sys.exit(exit_codes.get(final_status, 1))
