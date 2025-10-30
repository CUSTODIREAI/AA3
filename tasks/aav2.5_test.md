# AAv2.5 Test Task - Multi-Agent Collaboration

This task tests the full AAv2.5 system with:
- Executor agent
- Verifier agent
- Reviewer agent (with real LLM)
- Fixer agent (automatic recovery)
- Loop detection

EXECUTE:
mkdir -p /workspace/aav2.5_test
echo "AAv2.5 test file" > /workspace/aav2.5_test/test.txt
ls -la /workspace/aav2.5_test/

SUCCESS_CRITERIA:
File exists: /workspace/aav2.5_test/test.txt
grep: AAv2.5 test file in /workspace/aav2.5_test/test.txt
