# Test Execute Blocks - Proof of Concept

Simple test to prove deterministic execution works.

EXECUTE:
mkdir -p /workspace/test
echo "Hello from Claude Build" > /workspace/test/hello.txt
cat /workspace/test/hello.txt
ls -la /workspace/test/

SUCCESS_CRITERIA:
File exists: /workspace/test/hello.txt
command: grep -q "Hello from Claude Build" /workspace/test/hello.txt
grep: Claude Build in /workspace/test/hello.txt
