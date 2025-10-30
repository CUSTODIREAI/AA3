#!/usr/bin/env python3
"""
AAv3 REAL Orchestrator - True Multi-Agent Deliberation

This is the PRODUCTION version that actually calls LLMs.
Unlike the prototype, agents truly reason and communicate.

Key differences from prototype:
- Agents call real LLMs (Claude/Codex) instead of hardcoded responses
- Uses simple consensus protocol from deliberate.py (proven 100% success)
- Agents actually discuss and reach agreement
- No complex decision schemas that break
"""
from __future__ import annotations
import sys, uuid, time, json
from pathlib import Path
from typing import List, Dict, Optional

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.aav3_agents import AAv3AgentReal
from src.agents.agent_wrapper import save_json
from scripts.aav3_shared_memory import SharedMemory
from src.utils.environment_check import get_environment_capabilities, generate_planner_context


class AAv3OrchestratorReal:
    """
    Real Deliberative Multi-Agent Orchestrator.

    Agents are REAL LLM calls, not simulations.
    Uses simple consensus protocol that actually works.
    """

    def __init__(self, task: str, session_id: str = None, max_rounds: int = 50):
        self.task = task
        self.session_id = session_id or f"aav3_real_{uuid.uuid4().hex[:8]}"
        self.max_rounds = max_rounds
        self.start_time = time.time()

        # Create shared memory
        self.memory = SharedMemory(self.session_id)

        # Create REAL agent instances (will call LLMs)
        self.agents = {
            "planner": AAv3AgentReal("planner", f"planner_{self.session_id}"),
            "researcher": AAv3AgentReal("researcher", f"researcher_{self.session_id}"),
            "coder": AAv3AgentReal("coder", f"coder_{self.session_id}"),
            "reviewer": AAv3AgentReal("reviewer", f"reviewer_{self.session_id}"),
            "tester": AAv3AgentReal("tester", f"tester_{self.session_id}"),
        }

        # Session directory for logs
        self.session_dir = Path(f"reports/aav3_real_sessions/{self.session_id}")
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Run environment capability checks (preflight)
        print("[Environment Check] Scanning system capabilities...\n")
        self.env_capabilities = get_environment_capabilities()
        self.env_context = generate_planner_context(self.env_capabilities)

        # Save capabilities report
        save_json(str(self.session_dir / "environment_capabilities.json"), self.env_capabilities)

        # Print summary
        print(self.env_capabilities.get("summary", "Environment check complete"))
        print()

        print(f"\n{'='*70}")
        print(f"AAv3 REAL DELIBERATIVE MULTI-AGENT SYSTEM")
        print(f"{'='*70}")
        print(f"Session: {self.session_id}")
        print(f"Task: {task}")
        print(f"Agents: {', '.join(self.agents.keys())} (REAL LLM calls)")
        print(f"Max rounds: {max_rounds}")
        print("")

    def run(self) -> Dict:
        """
        Run REAL multi-agent deliberation workflow.

        Returns: {'success': bool, 'result': ..., 'consensus': bool, ...}
        """

        try:
            # Phase 1: Planning (Planner proposes)
            print(f"\n{'='*70}")
            print("PHASE 1: PLANNING")
            print(f"{'='*70}\n")

            plan = self._planning_phase()
            if not plan:
                return self._finalize(success=False, reason="Planning failed")

            # Phase 2: Research (Researcher validates/gathers info)
            print(f"\n{'='*70}")
            print("PHASE 2: RESEARCH")
            print(f"{'='*70}\n")

            research = self._research_phase(plan)

            # Phase 3: Implementation (Coder implements)
            print(f"\n{'='*70}")
            print("PHASE 3: IMPLEMENTATION")
            print(f"{'='*70}\n")

            implementation = self._implementation_phase(plan, research)
            if not implementation:
                return self._finalize(success=False, reason="Implementation failed")

            # Phase 4: Review (Reviewer critiques)
            print(f"\n{'='*70}")
            print("PHASE 4: REVIEW")
            print(f"{'='*70}\n")

            review = self._review_phase(implementation)

            # If reviewer requests changes, iterate (max rounds)
            iteration = 1
            while review.get('verdict') == 'request_changes' and iteration < self.max_rounds:
                print(f"\n[Iteration {iteration}] Reviewer requested changes, refining...\n")

                # Coder refines based on feedback
                implementation = self._refine_implementation(implementation, review)
                review = self._review_phase(implementation)
                iteration += 1

            if review.get('verdict') == 'reject':
                return self._finalize(success=False, reason="Review rejected implementation")

            # Phase 5: Testing & Validation with auto-fix iteration
            print(f"\n{'='*70}")
            print("PHASE 5: TESTING & VALIDATION")
            print(f"{'='*70}\n")

            test_result = self._testing_phase(implementation)

            # If tests fail, iterate to fix (max rounds)
            test_iteration = 1
            while test_result.get('verdict') == 'needs_fixes' and test_iteration < self.max_rounds:
                print(f"\n[Test Iteration {test_iteration}] Tests failed, auto-fixing...\n")

                # Coder fixes based on test failures
                implementation = self._fix_test_failures(implementation, test_result)

                # Re-test
                test_result = self._testing_phase(implementation)
                test_iteration += 1

            # Phase 6: Final Consensus
            print(f"\n{'='*70}")
            print("PHASE 6: FINAL CONSENSUS")
            print(f"{'='*70}\n")

            consensus = self._consensus_phase(implementation, review, test_result)

            if consensus['approved']:
                return self._finalize(
                    success=True,
                    result=implementation,
                    consensus=True,
                    approval_ratio=consensus['approval_ratio']
                )
            else:
                return self._finalize(
                    success=False,
                    reason=f"Consensus not reached ({consensus['approval_ratio']:.0%} approval)",
                    result=implementation
                )

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return self._finalize(success=False, reason=f"Exception: {e}")

    def _planning_phase(self) -> Optional[Dict]:
        """Phase 1: Planner proposes approach."""
        print("[Planner] Analyzing task and proposing approach...\n")

        conversation = self.memory.get_messages_as_dicts()

        # Prepend environment constraints to task for Planner
        task_with_env_context = f"""{self.env_context}

TASK:
{self.task}"""

        # REAL LLM CALL - Planner reasons about the task
        plan = self.agents["planner"].propose_plan(
            task=task_with_env_context,
            conversation_history=conversation
        )

        # Log to memory
        self.memory.post_message(
            from_agent="planner",
            role="planner",
            content=json.dumps(plan, indent=2),
            message_type="proposal"
        )

        # Save to session
        save_json(str(self.session_dir / "plan.json"), plan)

        print(f"[Planner] Proposed approach:")
        print(f"  Strategy: {plan.get('approach', 'N/A')}")
        print(f"  Steps: {len(plan.get('steps', []))} steps")
        print(f"  Unknowns: {plan.get('unknowns', [])}")
        print()

        return plan

    def _research_phase(self, plan: Dict) -> Optional[Dict]:
        """Phase 2: Researcher gathers information."""
        unknowns = plan.get('unknowns', [])

        if not unknowns:
            print("[Researcher] No research needed (no unknowns identified)\n")
            return {"findings": ["No research required"], "confidence": "n/a"}

        print(f"[Researcher] Researching {len(unknowns)} questions...\n")

        conversation = self.memory.get_messages_as_dicts()

        # REAL LLM CALL - Researcher investigates
        research = self.agents["researcher"].research(
            questions=unknowns,
            conversation_history=conversation
        )

        # Log to memory
        self.memory.post_message(
            from_agent="researcher",
            role="researcher",
            content=json.dumps(research, indent=2),
            message_type="answer"
        )

        # Save to session
        save_json(str(self.session_dir / "research.json"), research)

        print(f"[Researcher] Research complete:")
        print(f"  Findings: {len(research.get('findings', []))} key points")
        print(f"  Recommendation: {research.get('recommendation', 'N/A')[:100]}")
        print(f"  Confidence: {research.get('confidence', 'unknown')}")
        print()

        return research

    def _implementation_phase(self, plan: Dict, research: Optional[Dict]) -> Optional[Dict]:
        """Phase 3: Coder implements the solution."""
        print("[Coder] Implementing solution...\n")

        conversation = self.memory.get_messages_as_dicts()

        # REAL LLM CALL - Coder creates implementation
        implementation = self.agents["coder"].implement(
            plan=plan,
            research=research,
            conversation_history=conversation
        )

        # Log to memory
        self.memory.post_message(
            from_agent="coder",
            role="coder",
            content=json.dumps(implementation, indent=2),
            message_type="artifact"
        )

        # Save to session
        save_json(str(self.session_dir / "implementation.json"), implementation)

        # Actually create files if specified
        files_to_create = implementation.get('files_to_create', [])
        created_files = []

        if files_to_create:
            print(f"[Coder] Creating {len(files_to_create)} files...\n")

            # Create workspace directory in session
            workspace_dir = self.session_dir / "workspace"
            workspace_dir.mkdir(parents=True, exist_ok=True)

            for file_info in files_to_create:
                path = file_info.get('path', 'unknown')
                content = file_info.get('content', '')

                if path and content:
                    # Write file to workspace
                    file_path = workspace_dir / path
                    file_path.parent.mkdir(parents=True, exist_ok=True)

                    try:
                        file_path.write_text(content, encoding='utf-8')
                        created_files.append(str(file_path))
                        print(f"  ✓ Created {path} ({len(content)} bytes)")

                        # Store in shared memory as artifact
                        self.memory.create_artifact(
                            name=path,
                            type=path.split('.')[-1] if '.' in path else 'file',
                            content=content,
                            created_by="coder",
                            status="draft"
                        )
                    except Exception as e:
                        print(f"  ✗ Failed to create {path}: {e}")
                else:
                    print(f"  ⚠ Skipping {path} (missing path or content)")

            print()
            implementation['_created_files'] = created_files
        else:
            print("[Coder] No files to create (implementation description only)\n")

        print(f"[Coder] Implementation complete:")
        print(f"  Description: {implementation.get('implementation', 'N/A')[:150]}")
        print(f"  Files created: {len(created_files)}")
        print(f"  Status: {implementation.get('status', 'unknown')}")
        print()

        return implementation

    def _refine_implementation(self, implementation: Dict, review: Dict) -> Dict:
        """Coder refines based on reviewer feedback."""
        print("[Coder] Refining implementation based on review feedback...\n")

        conversation = self.memory.get_messages_as_dicts()

        # Build refinement prompt
        issues = review.get('issues', [])
        suggestions = review.get('suggestions', [])

        refinement_context = {
            "original_implementation": implementation,
            "review_issues": issues,
            "review_suggestions": suggestions
        }

        # For now, re-call implement with context about refinements
        # In a full system, this would be a separate refinement method
        refined = self.agents["coder"].implement(
            plan={"approach": "Refine previous implementation", "steps": suggestions},
            research={"findings": [f"Address: {issue}" for issue in issues]},
            conversation_history=conversation
        )

        self.memory.post_message(
            from_agent="coder",
            role="coder",
            content=json.dumps(refined, indent=2),
            message_type="artifact_refined"
        )

        print("[Coder] Refinement complete\n")
        return refined

    def _fix_test_failures(self, implementation: Dict, test_result: Dict) -> Dict:
        """Coder fixes code based on test failures."""
        print("[Coder] Fixing implementation based on test failures...\n")

        conversation = self.memory.get_messages_as_dicts()

        # Extract test failures
        issues_found = test_result.get('issues_found', [])
        executed_tests = test_result.get('executed_tests', [])

        # Build fix prompt
        fix_context = {
            "original_implementation": implementation,
            "test_failures": issues_found,
            "all_test_results": executed_tests
        }

        # Call coder to fix based on test results
        fixed = self.agents["coder"].implement(
            plan={"approach": "Fix test failures in previous implementation", "steps": [f"Fix: {issue.get('test', 'unknown')}" for issue in issues_found]},
            research={"findings": [f"Test failed: {issue.get('test', '')}, Error: {issue.get('error', 'unknown')}" for issue in issues_found]},
            conversation_history=conversation
        )

        # Update workspace files
        workspace_dir = self.session_dir / "workspace"
        files_to_create = fixed.get('files_to_create', [])
        created_files = []

        if files_to_create:
            print(f"[Coder] Updating {len(files_to_create)} files...\n")

            for file_info in files_to_create:
                path = file_info.get('path', 'unknown')
                content = file_info.get('content', '')

                if path and content:
                    file_path = workspace_dir / path
                    file_path.parent.mkdir(parents=True, exist_ok=True)

                    try:
                        file_path.write_text(content, encoding='utf-8')
                        created_files.append(str(file_path))
                        print(f"  ✓ Updated {path} ({len(content)} bytes)")

                        # Update artifact in shared memory
                        self.memory.create_artifact(
                            name=path,
                            type=path.split('.')[-1] if '.' in path else 'file',
                            content=content,
                            created_by="coder",
                            status="fixed"
                        )
                    except Exception as e:
                        print(f"  ✗ Failed to update {path}: {e}")

            fixed['_created_files'] = created_files

        self.memory.post_message(
            from_agent="coder",
            role="coder",
            content=json.dumps(fixed, indent=2),
            message_type="artifact_fixed"
        )

        print("[Coder] Fixes complete\n")
        return fixed

    def _review_phase(self, implementation: Dict) -> Dict:
        """Phase 4: Reviewer critiques quality."""
        print("[Reviewer] Reviewing implementation...\n")

        conversation = self.memory.get_messages_as_dicts()

        artifact_desc = json.dumps(implementation, indent=2)

        # REAL LLM CALL - Reviewer assesses quality
        review = self.agents["reviewer"].review(
            artifact_description=artifact_desc,
            conversation_history=conversation
        )

        # Log to memory
        self.memory.post_message(
            from_agent="reviewer",
            role="reviewer",
            content=json.dumps(review, indent=2),
            message_type="review"
        )

        # Save to session
        save_json(str(self.session_dir / "review.json"), review)

        verdict = review.get('verdict', 'unknown')
        print(f"[Reviewer] Review complete:")
        print(f"  Verdict: {verdict}")
        print(f"  Strengths: {len(review.get('strengths', []))} noted")
        print(f"  Issues: {len(review.get('issues', []))} found")
        print(f"  Suggestions: {len(review.get('suggestions', []))} provided")
        print()

        return review

    def _testing_phase(self, implementation: Dict) -> Dict:
        """Phase 5: Tester validates with ACTUAL test execution."""
        print("[Tester] Validating implementation...\n")

        conversation = self.memory.get_messages_as_dicts()
        workspace_dir = self.session_dir / "workspace"

        # Step 1: Ask Tester what to test
        artifact_desc = json.dumps(implementation, indent=2)
        test_plan = self.agents["tester"].test(
            artifact_description=artifact_desc,
            conversation_history=conversation
        )

        # Step 2: Execute actual test commands
        print("[Orchestrator] Executing test commands...\n")
        test_results = []

        # Extract test commands from implementation if available
        created_files = implementation.get('_created_files', [])

        if created_files:
            # Run basic validation tests
            for file_path in created_files:
                file_path_obj = Path(file_path)

                # Test 1: File exists and is readable
                if file_path_obj.exists():
                    test_results.append({
                        "test": f"File exists: {file_path_obj.name}",
                        "result": "pass"
                    })
                    print(f"  ✓ File exists: {file_path_obj.name}")

                    # Test 2: Python syntax validation for .py files
                    if file_path_obj.suffix == '.py':
                        try:
                            import subprocess
                            # Use relative path from workspace_dir
                            relative_path = file_path_obj.relative_to(workspace_dir) if file_path_obj.is_absolute() else file_path_obj
                            result = subprocess.run(
                                ['python', '-m', 'py_compile', str(relative_path)],
                                capture_output=True,
                                timeout=30,
                                cwd=str(workspace_dir)
                            )
                            if result.returncode == 0:
                                test_results.append({
                                    "test": f"Python syntax: {file_path_obj.name}",
                                    "result": "pass"
                                })
                                print(f"  ✓ Python syntax valid: {file_path_obj.name}")
                            else:
                                test_results.append({
                                    "test": f"Python syntax: {file_path_obj.name}",
                                    "result": "fail",
                                    "error": result.stderr.decode()
                                })
                                print(f"  ✗ Python syntax error: {file_path_obj.name}")
                        except Exception as e:
                            test_results.append({
                                "test": f"Python syntax: {file_path_obj.name}",
                                "result": "error",
                                "error": str(e)
                            })

                    # Test 3: Docker build for Dockerfiles
                    if 'Dockerfile' in file_path_obj.name:
                        try:
                            import subprocess
                            print(f"  [Docker] Building {file_path_obj.name}...")

                            # Determine image tag from filename
                            if 'base' in file_path_obj.name.lower():
                                image_tag = "test-dfl-base:latest"
                            else:
                                image_tag = "test-dfl:latest"

                            # Use relative path for -f flag to match build context
                            relative_dockerfile = file_path_obj.relative_to(workspace_dir) if file_path_obj.is_absolute() else file_path_obj

                            result = subprocess.run(
                                ['docker', 'build', '-f', str(relative_dockerfile), '-t', image_tag, '.'],
                                capture_output=True,
                                timeout=600,  # 10 min for Docker builds
                                cwd=str(workspace_dir)
                            )

                            if result.returncode == 0:
                                test_results.append({
                                    "test": f"Docker build: {file_path_obj.name}",
                                    "result": "pass",
                                    "image": image_tag
                                })
                                print(f"  ✓ Docker build successful: {file_path_obj.name} → {image_tag}")
                            else:
                                error_output = result.stderr.decode()[:500]
                                test_results.append({
                                    "test": f"Docker build: {file_path_obj.name}",
                                    "result": "fail",
                                    "error": error_output
                                })
                                print(f"  ✗ Docker build failed: {file_path_obj.name}")
                        except subprocess.TimeoutExpired:
                            test_results.append({
                                "test": f"Docker build: {file_path_obj.name}",
                                "result": "fail",
                                "error": "Build timed out after 10 minutes"
                            })
                            print(f"  ✗ Docker build timeout: {file_path_obj.name}")
                        except FileNotFoundError:
                            test_results.append({
                                "test": f"Docker build: {file_path_obj.name}",
                                "result": "skip",
                                "error": "Docker not available on this system"
                            })
                            print(f"  ⊘ Docker not available, skipping build test")
                        except Exception as e:
                            test_results.append({
                                "test": f"Docker build: {file_path_obj.name}",
                                "result": "error",
                                "error": str(e)
                            })
                else:
                    test_results.append({
                        "test": f"File exists: {file_path_obj.name}",
                        "result": "fail",
                        "error": "File not found"
                    })
                    print(f"  ✗ File not found: {file_path_obj.name}")

        # Step 3: Combine test plan with actual results
        test_result = {
            "test_plan": test_plan,
            "executed_tests": test_results,
            "verdict": "ready" if all(t.get('result') == 'pass' for t in test_results) else "needs_fixes",
            "issues_found": [t for t in test_results if t.get('result') != 'pass']
        }

        # Log to memory
        self.memory.post_message(
            from_agent="tester",
            role="tester",
            content=json.dumps(test_result, indent=2),
            message_type="test_result"
        )

        # Save to session
        save_json(str(self.session_dir / "test_result.json"), test_result)

        verdict = test_result.get('verdict', 'unknown')
        print(f"\n[Tester] Testing complete:")
        print(f"  Verdict: {verdict}")
        print(f"  Tests executed: {len(test_results)}")
        print(f"  Tests passed: {sum(1 for t in test_results if t.get('result') == 'pass')}")
        print()

        return test_result

    def _consensus_phase(self, implementation: Dict, review: Dict, test_result: Dict) -> Dict:
        """Phase 6: All agents vote on completion."""
        print("[Orchestrator] Requesting final consensus from all agents...\n")

        proposal_summary = f"""
Task: {self.task}

Implementation: {implementation.get('implementation', 'N/A')}
Review verdict: {review.get('verdict', 'unknown')}
Test verdict: {test_result.get('verdict', 'unknown')}

Should we approve this as complete?
"""

        conversation = self.memory.get_messages_as_dicts()

        votes = {}
        for agent_name, agent in self.agents.items():
            # REAL LLM CALL - Each agent votes
            vote_result = agent.vote(
                proposal_summary=proposal_summary,
                conversation_history=conversation
            )

            vote = vote_result.get('vote', 'reject')
            rationale = vote_result.get('rationale', 'No rationale')

            votes[agent_name] = vote
            print(f"  [{agent_name}] {vote} - {rationale[:80]}")

            # Record vote in memory
            self.memory.vote(
                proposal_id="final_completion",
                agent=agent_name,
                vote=vote
            )

        # Calculate consensus
        approve_count = sum(1 for v in votes.values() if v == 'approve')
        total = len(votes)
        approval_ratio = approve_count / total if total > 0 else 0.0

        consensus_reached = approval_ratio >= 0.67  # 2/3 majority

        print(f"\nConsensus: {approval_ratio:.0%} approval ({approve_count}/{total})")
        print(f"Result: {'APPROVED ✓' if consensus_reached else 'NOT APPROVED ✗'}\n")

        return {
            "approved": consensus_reached,
            "votes": votes,
            "approval_ratio": approval_ratio,
            "approve_count": approve_count,
            "total_votes": total
        }

    def _finalize(self, success: bool, reason: str = "", result: Dict = None, **kwargs) -> Dict:
        """Finalize and save session results."""
        duration = time.time() - self.start_time

        summary = {
            "session_id": self.session_id,
            "task": self.task,
            "success": success,
            "reason": reason,
            "duration_sec": duration,
            "messages": len(self.memory.messages),
            "artifacts": len(self.memory.artifacts),
            "result": result,
            **kwargs
        }

        # Save summary
        save_json(str(self.session_dir / "summary.json"), summary)

        print(f"{'='*70}")
        print("SESSION COMPLETE")
        print(f"{'='*70}")
        print(f"Success: {success}")
        if reason:
            print(f"Reason: {reason}")
        print(f"Duration: {duration:.2f}s")
        print(f"Messages: {len(self.memory.messages)}")
        print(f"Session dir: {self.session_dir}")
        print("")

        return summary


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="AAv3 REAL Multi-Agent Deliberation")
    ap.add_argument("--task", required=True, help="Task description or path to task file")
    ap.add_argument("--session-id", help="Session ID (auto-generated if not provided)")
    ap.add_argument("--max-rounds", type=int, default=50, help="Max refinement rounds")
    args = ap.parse_args()

    # Load task from file if it's a path
    task_text = args.task
    task_path = Path(args.task)
    if task_path.exists() and task_path.is_file():
        task_text = task_path.read_text(encoding='utf-8')
        print(f"Loaded task from: {task_path}")

    # Run orchestrator
    orchestrator = AAv3OrchestratorReal(
        task=task_text,
        session_id=args.session_id,
        max_rounds=args.max_rounds
    )

    result = orchestrator.run()

    # Exit with status code
    sys.exit(0 if result['success'] else 1)
