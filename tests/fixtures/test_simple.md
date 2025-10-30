
# Test Task

EXECUTE:
mkdir -p /workspace/test
echo "Hello AAv2" > /workspace/test/hello.txt
cat /workspace/test/hello.txt

SUCCESS_CRITERIA:
File exists: /workspace/test/hello.txt
grep: Hello AAv2 in /workspace/test/hello.txt
