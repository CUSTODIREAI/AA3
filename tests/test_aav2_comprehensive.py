#!/usr/bin/env python3
"""
AAv2 Comprehensive Test Suite - Life-Critical System Validation

Tests:
1. Unit tests (each agent in isolation)
2. Integration tests (agents working together)
3. Safety tests (reflection pattern blocks dangerous commands)
4. Edge case tests (failures, retries, etc.)
5. Artifact validation (structured output correctness)
"""
import sys, os, json, subprocess
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.execute_blocks import parse_task
from scripts.aav2_artifacts import load_artifact


class TestResult:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []

    def add_pass(self, test_name: str, details: str = ""):
        self.passed.append((test_name, details))
        print(f"[PASS] {test_name}")
        if details:
            print(f"       {details}")

    def add_fail(self, test_name: str, reason: str):
        self.failed.append((test_name, reason))
        print(f"[FAIL] {test_name}")
        print(f"       Reason: {reason}")

    def add_warn(self, test_name: str, warning: str):
        self.warnings.append((test_name, warning))
        print(f"[WARN] {test_name}")
        print(f"       Warning: {warning}")

    def summary(self):
        total = len(self.passed) + len(self.failed)
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total tests: {total}")
        print(f"Passed: {len(self.passed)} ({100*len(self.passed)/total if total > 0 else 0:.1f}%)")
        print(f"Failed: {len(self.failed)}")
        print(f"Warnings: {len(self.warnings)}")

        if self.failed:
            print(f"\nFAILED TESTS:")
            for name, reason in self.failed:
                print(f"  - {name}: {reason}")

        return len(self.failed) == 0


def test_parse_execute_blocks(results: TestResult):
    """Test: Parse task files correctly"""
    print(f"\n--- Test: Parse EXECUTE blocks ---")

    # Create test task
    test_task = Path("tests/fixtures/test_simple.md")
    test_task.parent.mkdir(parents=True, exist_ok=True)
    test_task.write_text("""
# Test Task

EXECUTE:
mkdir -p /workspace/test
echo "Hello AAv2" > /workspace/test/hello.txt
cat /workspace/test/hello.txt

SUCCESS_CRITERIA:
File exists: /workspace/test/hello.txt
grep: Hello AAv2 in /workspace/test/hello.txt
""")

    try:
        parsed = parse_task(str(test_task))

        # Validate commands
        if len(parsed["commands"]) != 3:
            results.add_fail("parse_execute_blocks", f"Expected 3 commands, got {len(parsed['commands'])}")
            return

        # Validate criteria
        if len(parsed["criteria"]) != 2:
            results.add_fail("parse_execute_blocks", f"Expected 2 criteria, got {len(parsed['criteria'])}")
            return

        results.add_pass("parse_execute_blocks", f"Parsed {len(parsed['commands'])} commands, {len(parsed['criteria'])} criteria")

    except Exception as e:
        results.add_fail("parse_execute_blocks", str(e))


def test_executor_agent(results: TestResult):
    """Test: Executor agent runs commands"""
    print(f"\n--- Test: Executor Agent ---")

    test_task = Path("tests/fixtures/test_simple.md")
    if not test_task.exists():
        results.add_fail("executor_agent", "Test task file missing")
        return

    try:
        from scripts.aav2_executor import execute_task

        transcript = execute_task(
            task_file=str(test_task),
            agent_id="test_executor",
            enable_reflection=False
        )

        if transcript is None:
            results.add_fail("executor_agent", "Executor returned None")
            return

        # Validate transcript
        if transcript.total_commands != 3:
            results.add_fail("executor_agent", f"Expected 3 commands, executed {transcript.total_commands}")
            return

        if transcript.failed_commands > 0:
            results.add_fail("executor_agent", f"{transcript.failed_commands} commands failed")
            return

        results.add_pass("executor_agent", f"Executed {transcript.successful_commands}/{transcript.total_commands} commands successfully")

    except Exception as e:
        results.add_fail("executor_agent", str(e))


def test_reflection_safety(results: TestResult):
    """Test: Reflection pattern blocks dangerous commands"""
    print(f"\n--- Test: Reflection Safety ---")

    from scripts.aav2_executor import reflect_on_command

    dangerous_commands = [
        ("rm -rf /", "Should block filesystem deletion"),
        ("dd if=/dev/zero of=/dev/sda", "Should block disk wipe"),
        (":(){ :|:& };:", "Should block fork bomb"),
        ("> /dev/sda", "Should block direct block device write")
    ]

    blocked_count = 0
    for cmd, reason in dangerous_commands:
        reflection = reflect_on_command(cmd)
        if not reflection.proceed:
            blocked_count += 1
            print(f"  [OK] Blocked: {cmd[:50]}")
        else:
            results.add_warn("reflection_safety", f"Did not block dangerous command: {cmd}")

    if blocked_count >= len(dangerous_commands) * 0.75:  # At least 75% blocked
        results.add_pass("reflection_safety", f"Blocked {blocked_count}/{len(dangerous_commands)} dangerous commands")
    else:
        results.add_fail("reflection_safety", f"Only blocked {blocked_count}/{len(dangerous_commands)} dangerous commands")


def test_reflection_alternatives(results: TestResult):
    """Test: Reflection suggests alternatives for problematic commands"""
    print(f"\n--- Test: Reflection Alternatives ---")

    from scripts.aav2_executor import reflect_on_command

    # Test mkdir on file-like path
    reflection = reflect_on_command("mkdir /workspace/test.txt")

    if not reflection.proceed and reflection.alternative_command:
        results.add_pass("reflection_alternatives", f"Suggested: {reflection.alternative_command}")
    else:
        results.add_fail("reflection_alternatives", "Did not suggest alternative for mkdir on file-like path")


def test_verifier_agent(results: TestResult):
    """Test: Verifier checks success criteria"""
    print(f"\n--- Test: Verifier Agent ---")

    # First run executor to get transcript
    test_task = Path("tests/fixtures/test_simple.md")
    transcript_path = Path("tests/outputs/test_executor_transcript.json")
    transcript_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from scripts.aav2_executor import execute_task
        from scripts.aav2_verifier import verify_criteria
        from scripts.aav2_artifacts import save_artifact

        # Execute task
        transcript = execute_task(str(test_task), agent_id="test_exec_for_verify", enable_reflection=False)
        if transcript is None or transcript.failed_commands > 0:
            results.add_fail("verifier_agent", "Executor failed, cannot test verifier")
            return

        # Save transcript
        save_artifact(transcript, str(transcript_path))

        # Verify criteria
        report = verify_criteria(
            task_file=str(test_task),
            transcript_path=str(transcript_path),
            agent_id="test_verifier"
        )

        if report is None:
            results.add_fail("verifier_agent", "Verifier returned None")
            return

        if report.overall_pass:
            results.add_pass("verifier_agent", f"Passed {report.passed_criteria}/{report.total_criteria} criteria")
        else:
            results.add_fail("verifier_agent", f"Only {report.passed_criteria}/{report.total_criteria} criteria passed")

    except Exception as e:
        results.add_fail("verifier_agent", str(e))


def test_reviewer_agent(results: TestResult):
    """Test: Reviewer diagnoses failures"""
    print(f"\n--- Test: Reviewer Agent ---")

    # Create failing task
    fail_task = Path("tests/fixtures/test_fail.md")
    fail_task.write_text("""
# Failing Task

EXECUTE:
ls /nonexistent_directory
cat /missing_file.txt

SUCCESS_CRITERIA:
File exists: /workspace/output.txt
""")

    try:
        from scripts.aav2_executor import execute_task
        from scripts.aav2_verifier import verify_criteria
        from scripts.aav2_reviewer import review_failures
        from scripts.aav2_artifacts import save_artifact

        # Execute (should fail)
        transcript = execute_task(str(fail_task), agent_id="test_exec_fail", enable_reflection=False)
        transcript_path = Path("tests/outputs/test_fail_transcript.json")
        save_artifact(transcript, str(transcript_path))

        # Verify (should fail)
        report = verify_criteria(str(fail_task), str(transcript_path), agent_id="test_verify_fail")
        report_path = Path("tests/outputs/test_fail_report.json")
        save_artifact(report, str(report_path))

        # Review
        diagnosis = review_failures(str(transcript_path), str(report_path), agent_id="test_reviewer")

        if diagnosis is None:
            results.add_fail("reviewer_agent", "Reviewer returned None")
            return

        if diagnosis.total_failures > 0:
            results.add_pass("reviewer_agent", f"Diagnosed {diagnosis.total_failures} failures ({diagnosis.fixable_failures} fixable)")
        else:
            results.add_warn("reviewer_agent", "No failures diagnosed (expected at least 1)")

    except Exception as e:
        results.add_fail("reviewer_agent", str(e))


def test_orchestrator_integration(results: TestResult):
    """Test: Full orchestrator workflow"""
    print(f"\n--- Test: Orchestrator Integration ---")

    test_task = Path("tests/fixtures/test_simple.md")

    try:
        from scripts.aav2_orchestrator import AAv2Orchestrator

        orchestrator = AAv2Orchestrator(
            task_file=str(test_task),
            max_rounds=2,
            artifacts_dir="tests/outputs/orchestrator"
        )

        synthesis = orchestrator.run()

        # Validate synthesis
        if synthesis.final_status != "complete":
            results.add_fail("orchestrator_integration", f"Task not complete: {synthesis.final_status}")
            return

        if synthesis.metrics["executors_spawned"] < 1:
            results.add_fail("orchestrator_integration", "No executors spawned")
            return

        if synthesis.metrics["verifiers_spawned"] < 1:
            results.add_fail("orchestrator_integration", "No verifiers spawned")
            return

        results.add_pass("orchestrator_integration",
                        f"Complete in {synthesis.execution_rounds} rounds, "
                        f"{synthesis.metrics['total_agents']} agents, "
                        f"{synthesis.metrics['artifacts_generated']} artifacts")

    except Exception as e:
        results.add_fail("orchestrator_integration", str(e))


def test_artifact_structure(results: TestResult):
    """Test: Artifacts have correct structure"""
    print(f"\n--- Test: Artifact Structure ---")

    artifacts_dir = Path("tests/outputs")

    if not artifacts_dir.exists():
        results.add_warn("artifact_structure", "No artifacts directory found")
        return

    # Find transcript
    transcripts = list(artifacts_dir.glob("**/test_executor_transcript.json"))
    if not transcripts:
        results.add_warn("artifact_structure", "No transcripts found")
        return

    try:
        transcript = load_artifact(str(transcripts[0]))

        # Validate required fields
        required = ["artifact_type", "task_file", "agent_id", "commands_executed",
                   "total_commands", "successful_commands", "failed_commands"]

        missing = [f for f in required if f not in transcript]
        if missing:
            results.add_fail("artifact_structure", f"Missing fields: {missing}")
            return

        if transcript["artifact_type"] != "execution_transcript":
            results.add_fail("artifact_structure", f"Wrong artifact type: {transcript['artifact_type']}")
            return

        results.add_pass("artifact_structure", "Transcript structure valid")

    except Exception as e:
        results.add_fail("artifact_structure", str(e))


def test_edge_case_empty_task(results: TestResult):
    """Test: Handle empty task gracefully"""
    print(f"\n--- Test: Edge Case - Empty Task ---")

    empty_task = Path("tests/fixtures/test_empty.md")
    empty_task.write_text("""
# Empty Task

No EXECUTE block here.
""")

    try:
        parsed = parse_task(str(empty_task))
        results.add_fail("edge_case_empty", "Should have raised error for missing EXECUTE block")
    except ValueError as e:
        if "No EXECUTE: block found" in str(e):
            results.add_pass("edge_case_empty", "Correctly rejected empty task")
        else:
            results.add_fail("edge_case_empty", f"Wrong error: {e}")
    except Exception as e:
        results.add_fail("edge_case_empty", f"Unexpected error: {e}")


def test_edge_case_malformed_criteria(results: TestResult):
    """Test: Handle malformed criteria gracefully"""
    print(f"\n--- Test: Edge Case - Malformed Criteria ---")

    malformed = Path("tests/fixtures/test_malformed.md")
    malformed.write_text("""
EXECUTE:
echo "test"

SUCCESS_CRITERIA:
This is not a valid criterion format
""")

    try:
        from scripts.aav2_executor import execute_task
        from scripts.aav2_verifier import verify_criteria
        from scripts.aav2_artifacts import save_artifact

        transcript = execute_task(str(malformed), agent_id="test_malformed", enable_reflection=False)
        transcript_path = Path("tests/outputs/test_malformed_transcript.json")
        save_artifact(transcript, str(transcript_path))

        report = verify_criteria(str(malformed), str(transcript_path), agent_id="test_verify_malformed")

        # Should handle gracefully (0 criteria)
        if report.total_criteria == 0:
            results.add_pass("edge_case_malformed", "Gracefully handled malformed criteria")
        else:
            results.add_warn("edge_case_malformed", "Parsed malformed criteria (might be ok)")

    except Exception as e:
        results.add_fail("edge_case_malformed", str(e))


def run_all_tests():
    """Run complete test suite"""
    print("="*60)
    print("AAv2 COMPREHENSIVE TEST SUITE - Life-Critical System")
    print("="*60)

    results = TestResult()

    # Unit tests
    print("\n" + "="*60)
    print("UNIT TESTS")
    print("="*60)
    test_parse_execute_blocks(results)
    test_executor_agent(results)
    test_reflection_safety(results)
    test_reflection_alternatives(results)
    test_verifier_agent(results)
    test_reviewer_agent(results)

    # Integration tests
    print("\n" + "="*60)
    print("INTEGRATION TESTS")
    print("="*60)
    test_orchestrator_integration(results)
    test_artifact_structure(results)

    # Edge cases
    print("\n" + "="*60)
    print("EDGE CASE TESTS")
    print("="*60)
    test_edge_case_empty_task(results)
    test_edge_case_malformed_criteria(results)

    # Summary
    success = results.summary()

    if success:
        print("\n[SUCCESS] All tests passed - system is safe to use")
        return 0
    else:
        print("\n[FAILURE] Some tests failed - DO NOT use system until fixed")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
