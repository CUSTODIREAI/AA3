# AAv3 REAL - Autonomous Multi-Agent System Documentation

## Executive Summary

AAv3 REAL is a fully autonomous, multi-agent deliberation system that uses real LLM calls to plan, research, implement, review, test, and reach consensus on software engineering tasks. Unlike prototype systems with hardcoded responses, AAv3 REAL agents truly reason and communicate through actual Claude/Codex API calls.

**Key Achievement**: Zero human intervention from task input to deliverable output with objective quality gates.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Core Components](#core-components)
3. [Installation & Setup](#installation--setup)
4. [Configuration](#configuration)
5. [Usage Guide](#usage-guide)
6. [Technical Implementation](#technical-implementation)
7. [Troubleshooting](#troubleshooting)
8. [Performance Metrics](#performance-metrics)

---

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    AAv3 Orchestrator                        │
│  (Coordinates 6-phase autonomous workflow)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │   Shared Memory         │
        │ (Conversation History)  │
        └────────────┬────────────┘
                     │
     ┌───────────────┼───────────────┐
     │               │               │
┌────▼────┐    ┌────▼────┐    ┌────▼────┐
│ Planner │    │Research │    │  Coder  │
│  Agent  │    │  Agent  │    │  Agent  │
└─────────┘    └─────────┘    └─────────┘
     │               │               │
┌────▼────┐    ┌────▼────┐         │
│Reviewer │    │ Tester  │         │
│  Agent  │    │  Agent  │         │
└─────────┘    └─────────┘         │
                     │              │
                ┌────▼──────────────▼────┐
                │  Tool Execution Engine │
                │ (Python, Docker, etc.) │
                └────────────────────────┘
```

### Six-Phase Workflow

**Preflight: Environment Capability Check** - System scans for available tools (Docker, GPU, programming languages, security tools) and generates constraint context for Planner

1. **Planning** - Planner agent analyzes task with environment constraints, proposes strategy, identifies unknowns
2. **Research** - Researcher agent gathers information to resolve unknowns
3. **Implementation** - Coder agent creates files based on plan and research
4. **Review** - Reviewer agent checks code quality and completeness
5. **Testing** - Tester agent executes objective tests (syntax checks, builds, runtime tests, GPU smoke tests, security scans)
6. **Consensus** - All agents vote on quality based on test results

### Auto-Fix Loop

```python
while test_result.verdict == 'needs_fixes' and iteration < max_rounds:
    implementation = coder.fix(implementation, test_result)
    test_result = tester.test(implementation)
    iteration += 1
```

**Default**: 50 rounds (configurable)
**Purpose**: Persist until success, not arbitrary iteration limits

---

## Core Components

### 1. AAv3OrchestratorReal (`scripts/aav3_orchestrator_real.py`)

**Purpose**: Main orchestration engine that coordinates all agents through the 6-phase workflow.

**Key Features**:
- Session management with unique IDs
- Shared memory for inter-agent communication
- Workspace directory creation and isolation
- Auto-fix iteration with configurable limits
- Final consensus voting with objective criteria

**Entry Point**:
```python
class AAv3OrchestratorReal:
    def __init__(self, task: str, session_id: str = None, max_rounds: int = 50)
    def run(self) -> Dict
```

### 2. AAv3AgentReal (`src/agents/aav3_agents.py`)

**Purpose**: Real LLM-powered agent implementation. Each agent has a specialized role prompt.

**Agent Types**:

| Agent      | Role                                    | Specialization                        |
|------------|-----------------------------------------|---------------------------------------|
| Planner    | Strategic thinking & decomposition      | Plans, steps, unknowns                |
| Researcher | Information gathering                   | Web search, documentation research    |
| Coder      | Implementation                          | File creation, code writing           |
| Reviewer   | Quality assurance                       | Code review, best practices           |
| Tester     | Validation                              | Objective testing, pass/fail criteria |

**Key Method**:
```python
def call_with_context(
    self,
    user_prompt: str,
    conversation_history: List[Dict],
    use_claude: bool = False,
    timeout: int = 900  # 15 minutes
) -> str
```

**Role-Specific Prompts** (excerpt from `aav3_agents.py`):
```python
"planner": "You are a strategic planner. Analyze the task and create a detailed implementation plan...",
"researcher": "You are a researcher. Find information to answer specific questions...",
"coder": "You are a skilled coder. Implement solutions based on plans and research...",
"reviewer": "You are a code reviewer. Evaluate quality, completeness, and best practices...",
"tester": "You are a QA tester. Run objective tests and report pass/fail results..."
```

### 3. SharedMemory (`scripts/aav3_shared_memory.py`)

**Purpose**: Conversation history and artifact storage for agent communication.

**Key Methods**:
```python
class SharedMemory:
    def add_message(self, from_agent: str, message_type: str, content: Dict, role: str = None)
    def get_messages_as_dicts(self, last_n: int = None) -> List[Dict]
    def get_latest_implementation(self) -> Optional[Dict]
```

**Message Format**:
```python
{
    "from_agent": "coder",
    "role": "implementation",
    "message_type": "files_created",
    "content": {
        "files_to_create": [
            {"path": "factorial.py", "content": "..."}
        ],
        "status": "complete"
    },
    "timestamp": "2025-10-30T16:45:00.000Z"
}
```

### 4. Environment Check Utilities (`src/utils/environment_check.py`)

**Purpose**: Preflight environment capability detection to prevent agents from proposing tests that will fail due to missing system capabilities.

**Key Features**:
- Docker availability and configuration detection
- GPU detection (NVIDIA/AMD/Apple Silicon) with CUDA version
- Programming language runtime detection (Python, Node.js, Rust, Go, Java)
- Security tool detection (git, grep, trivy, syft, grype)
- Network connectivity checks (internet, GitHub, PyPI, npm)
- Multimedia tool detection (ffmpeg, imagemagick, opencv)

**Key Functions**:
```python
def get_environment_capabilities() -> Dict:
    """
    Comprehensive environment scan returning:
    {
        "docker": {"available": bool, "version": str, "compose": bool, "buildx": bool},
        "gpu": {"nvidia": bool, "amd": bool, "cuda_version": str, "devices": []},
        "multimedia": {"ffmpeg": bool, "opencv": bool, ...},
        "languages": {"python": bool, "node": bool, "rust": bool, ...},
        "security": {"git": bool, "syft": bool, "grype": bool, ...},
        "network": {"internet": bool, "github": bool, ...},
        "summary": "Human-readable summary string"
    }
    """

def generate_planner_context(capabilities: Dict) -> str:
    """
    Generate formatted constraint context for Planner agent.

    Example output:
    ⚠ Docker NOT available: Do not propose Docker builds, container tests...
    ✓ NVIDIA GPU: Can test CUDA code, TensorFlow GPU, PyTorch GPU...
    ✓ Languages: python, node, rust
    """
```

**Integration**: Called during orchestrator initialization (before Phase 1) and passed to Planner via task context.

**Benefit**: Directly addresses DFL Docker failure scenario where agents proposed Docker builds in environments without Docker access.

### 5. Test Adapters (`src/utils/test_adapters.py`)

**Purpose**: Extensible test adapters for GPU smoke tests and security scanning to increase objective test coverage.

**GPUSmokeTestAdapter**:
- NVIDIA GPU detection via nvidia-smi
- CUDA compiler (nvcc) availability check
- CUDA program compilation and execution test
- TensorFlow GPU availability test
- PyTorch GPU availability test

**SecurityScanAdapter**:
- **Secrets Detection**: Regex-based scanning for API keys, AWS credentials, GitHub tokens, private keys, passwords
- **SBOM Generation**: Software Bill of Materials via syft, pip list, or npm list
- **Vulnerability Scanning**: CVE detection via grype or pip-audit with severity breakdown

**Usage Example**:
```python
from src.utils.test_adapters import run_gpu_smoke_tests, run_security_scans

gpu_results = run_gpu_smoke_tests(workspace_dir)
# Returns: {"test_suite": "GPU Smoke Tests", "tests": [...], "passed": bool}

security_results = run_security_scans(workspace_dir)
# Returns: {"test_suite": "Security Scans", "tests": [...], "passed": bool}
```

**Pattern**: Follows existing Rust test adapter pattern for easy extension.

### 6. Tool Execution Engine (embedded in orchestrator)

**Purpose**: Execute real commands for testing code.

**Supported Tests**:

1. **Python Syntax Validation**
   ```python
   subprocess.run(
       ['python', '-m', 'py_compile', str(relative_path)],
       cwd=str(workspace_dir),
       capture_output=True,
       timeout=30
   )
   ```

2. **Docker Build Validation** (with fixed path resolution)
   ```python
   relative_dockerfile = file_path_obj.relative_to(workspace_dir)
   subprocess.run(
       ['docker', 'build', '-f', str(relative_dockerfile), '-t', image_tag, '.'],
       cwd=str(workspace_dir),
       capture_output=True,
       timeout=600
   )
   ```

3. **Runtime Tests**
   ```python
   subprocess.run(
       ['python', '-m', 'unittest', test_file],
       cwd=str(workspace_dir),
       capture_output=True,
       timeout=120
   )
   ```

---

## Installation & Setup

### Prerequisites

- Python 3.10+
- WSL (Windows Subsystem for Linux) if on Windows
- Docker (optional, for Docker-related tasks)
- Claude Code CLI (`codex`) configured with API key
- Git

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/custodire-aa-system.git
cd custodire-aa-system
```

### Step 2: Create Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows WSL: source venv/bin/activate
pip install --upgrade pip setuptools wheel
```

### Step 3: Install Dependencies

```bash
pip install anthropic requests pathlib
```

### Step 4: Configure Claude Code CLI

```bash
# Set up Codex CLI with your API key
codex config set api_key YOUR_ANTHROPIC_API_KEY

# Verify installation
codex --version
```

### Step 5: Directory Structure

Create the following directory structure:

```
custodire-aa-system/
├── scripts/
│   ├── aav3_orchestrator_real.py     # Main orchestrator
│   └── aav3_shared_memory.py         # Shared memory
├── src/
│   ├── agents/
│   │   ├── aav3_agents.py            # Agent implementations
│   │   └── agent_wrapper.py          # LLM call wrapper
│   └── utils/
│       ├── environment_check.py      # Environment capability detection
│       └── test_adapters.py          # GPU & security test adapters
├── tasks/
│   ├── aav3_test_simple.md           # Simple test tasks
│   └── build_dfl_docker_rtx4090.md   # Complex tasks
├── reports/
│   └── aav3_real_sessions/           # Session outputs
└── docs/
    └── AAv3_REAL_System_Documentation.md
```

### Step 6: Verify Installation

```bash
python scripts/aav3_orchestrator_real.py --help
```

---

## Configuration

### Agent Wrapper Configuration (`src/agents/agent_wrapper.py`)

**LLM Call Function**:
```python
def call_codex_cli(prompt: str, timeout: int = 900) -> str:
    """Call Codex CLI with prompt, return response."""
    result = subprocess.run(
        ['codex', 'query', prompt],
        capture_output=True,
        text=True,
        timeout=timeout
    )
    return result.stdout.strip()
```

**Timeout Settings**:
- Default: 900 seconds (15 minutes)
- Adjust in `AAv3AgentReal.call_with_context()` if needed

### Orchestrator Configuration

**Max Rounds** (line 35 in `aav3_orchestrator_real.py`):
```python
def __init__(self, task: str, session_id: str = None, max_rounds: int = 50):
```

**Recommendation**: 50 rounds ensures persistence. Increase for highly complex tasks.

### Workspace Isolation

**Session Workspaces** (automatically created):
```
reports/aav3_real_sessions/aav3_real_{session_id}/
├── workspace/              # Isolated workspace for files
├── test_result.json        # Test execution results
├── implementation.json     # Implementation details
├── review.json             # Review feedback
└── consensus.json          # Final vote results
```

### Tool Execution Paths (Fixed in Latest Version)

**CRITICAL**: Line 484 and 524 fixes in `aav3_orchestrator_real.py`:

```python
# Line 484: Python syntax test path resolution
relative_path = file_path_obj.relative_to(workspace_dir) if file_path_obj.is_absolute() else file_path_obj
result = subprocess.run(
    ['python', '-m', 'py_compile', str(relative_path)],
    cwd=str(workspace_dir)
)

# Line 524: Docker build path resolution
relative_dockerfile = file_path_obj.relative_to(workspace_dir) if file_path_obj.is_absolute() else file_path_obj
result = subprocess.run(
    ['docker', 'build', '-f', str(relative_dockerfile), '-t', image_tag, '.'],
    cwd=str(workspace_dir)
)
```

**Why This Matters**: Ensures Docker build context and Dockerfile path are properly resolved, preventing "lstat reports: no such file or directory" errors.

---

## Usage Guide

### Basic Usage

```bash
cd custodire-aa-system
source venv/bin/activate

# Run with simple task
python scripts/aav3_orchestrator_real.py --task tasks/aav3_test_simple.md

# Run with max rounds override
python scripts/aav3_orchestrator_real.py --task tasks/aav3_test_simple.md --max-rounds 100
```

### Task File Format

Create a Markdown file in `tasks/` directory:

```markdown
# Task Title

Brief description of what needs to be built.

## Requirements

- Requirement 1
- Requirement 2
- Requirement 3

## Success Criteria

1. Criterion 1
2. Criterion 2

## Context

Additional context or background information.
```

**Example** (`tasks/aav3_test_simple.md`):
```markdown
# Simple Test Task for AAv3 Real

Create a Python script that calculates the factorial of a number.

Requirements:
- Function should handle n >= 0
- Include error handling for negative numbers
- Add docstring with examples
- Include basic test cases
```

### Monitoring Execution

**Real-time Output** (with unbuffered Python):
```bash
python -u scripts/aav3_orchestrator_real.py --task tasks/your_task.md 2>&1
```

**Background Execution**:
```bash
nohup python -u scripts/aav3_orchestrator_real.py --task tasks/your_task.md > output.log 2>&1 &
```

**Check Progress**:
```bash
tail -f output.log
```

### Examining Results

**Session Directory**:
```bash
ls -la reports/aav3_real_sessions/aav3_real_*/
```

**View Implementation**:
```bash
cat reports/aav3_real_sessions/aav3_real_*/implementation.json | python -m json.tool
```

**View Test Results**:
```bash
cat reports/aav3_real_sessions/aav3_real_*/test_result.json | python -m json.tool
```

**View Consensus**:
```bash
cat reports/aav3_real_sessions/aav3_real_*/consensus.json | python -m json.tool
```

---

## Technical Implementation

### Phase 1: Planning

**Planner Agent Input**:
```json
{
  "user_prompt": "Analyze this task and propose implementation approach: {task}",
  "conversation_history": [],
  "tools_context": "You have access to file creation, web search, and testing tools..."
}
```

**Expected Output**:
```json
{
  "strategy": "Description of overall approach",
  "steps": ["Step 1", "Step 2", "..."],
  "unknowns": ["Question 1", "Question 2", "..."]
}
```

### Phase 2: Research

**Researcher Agent Input**:
```json
{
  "user_prompt": "Research these questions: {unknowns}",
  "conversation_history": [planner_message],
  "tools_context": "..."
}
```

**Expected Output**:
```json
{
  "findings": ["Finding 1", "Finding 2", "..."],
  "recommendation": "Summary recommendation based on research",
  "confidence": "high|medium|low"
}
```

### Phase 3: Implementation

**Coder Agent Input**:
```json
{
  "user_prompt": "Implement the solution based on plan and research",
  "conversation_history": [planner_message, researcher_message],
  "tools_context": "..."
}
```

**Expected Output**:
```json
{
  "files_to_create": [
    {
      "path": "relative/path/to/file.py",
      "content": "full file content..."
    }
  ],
  "key_decisions": ["Decision 1", "Decision 2", "..."],
  "status": "complete"
}
```

### Phase 4: Review

**Reviewer Agent Input**:
```json
{
  "user_prompt": "Review this implementation for quality",
  "conversation_history": [...],
  "tools_context": "..."
}
```

**Expected Output**:
```json
{
  "verdict": "approved|needs_revision|rejected",
  "strengths": ["Strength 1", "..."],
  "issues": ["Issue 1", "..."],
  "suggestions": ["Suggestion 1", "..."]
}
```

### Phase 5: Testing

**Tester Agent Input**:
```json
{
  "user_prompt": "Validate this implementation with objective tests",
  "conversation_history": [...],
  "tools_context": "..."
}
```

**Orchestrator Executes Real Tests**:
1. Python syntax validation for `.py` files
2. Docker builds for `Dockerfile` files
3. Runtime tests if test files present

**Test Result Format**:
```json
{
  "verdict": "pass|needs_fixes",
  "tests_executed": 10,
  "tests_passed": 8,
  "tests_failed": 2,
  "issues_found": [
    {
      "test": "Docker build: dfl-base.Dockerfile",
      "result": "fail",
      "error": "ERROR: failed to build: ..."
    }
  ]
}
```

### Phase 6: Consensus

**All Agents Vote**:
```python
consensus_votes = {}
for agent_name, agent in self.agents.items():
    vote = agent.vote_on_quality(implementation, review, test_result)
    consensus_votes[agent_name] = vote  # "approve" or "reject"
```

**Approval Threshold**: 80% (4/5 agents must approve)

**Consensus Result**:
```json
{
  "approved": false,
  "approval_rate": 0.0,
  "votes": {
    "planner": "reject",
    "researcher": "reject",
    "coder": "reject",
    "reviewer": "reject",
    "tester": "reject"
  },
  "reason": "Tests still failing after max iterations"
}
```

### Auto-Fix Iteration

**Loop Logic** (lines 126-136):
```python
test_iteration = 1
while test_result.get('verdict') == 'needs_fixes' and test_iteration < self.max_rounds:
    print(f"\n[Test Iteration {test_iteration}] Tests failed, auto-fixing...\n")

    # Coder fixes based on test failures
    implementation = self._fix_test_failures(implementation, test_result)

    # Re-test
    test_result = self._testing_phase(implementation)
    test_iteration += 1
```

**Fix Prompt to Coder**:
```
The tests failed with the following issues:
{test_issues}

Please fix the implementation to address these failures.
Previous implementation:
{previous_implementation}
```

---

## Troubleshooting

### Common Issues

#### 1. "lstat reports: no such file or directory" (Docker builds)

**Cause**: Absolute path passed to `docker build -f` while build context is relative.

**Fix**: Lines 484 and 524 in `aav3_orchestrator_real.py` must use relative path resolution:
```python
relative_dockerfile = file_path_obj.relative_to(workspace_dir) if file_path_obj.is_absolute() else file_path_obj
```

#### 2. Python Syntax Errors Not Fixed

**Cause**: Coder agent not receiving detailed error messages.

**Fix**: Ensure error output is included in test result:
```python
test_result["issues_found"].append({
    "test": f"Python syntax: {file_path}",
    "result": "fail",
    "error": result.stderr.decode()
})
```

#### 3. Agents Give Up After 3 Rounds

**Cause**: Default `max_rounds` too low.

**Fix**: Increase default to 50 (line 35):
```python
def __init__(self, task: str, session_id: str = None, max_rounds: int = 50):
```

#### 4. LLM Timeout Errors

**Cause**: Complex tasks taking longer than 15 minutes.

**Fix**: Increase timeout in `AAv3AgentReal.call_with_context`:
```python
timeout: int = 1800  # 30 minutes
```

#### 5. Consensus Always Rejects

**Cause**: Agents voting based on subjective criteria instead of test results.

**Fix**: Update agent prompts to emphasize:
```
Vote "approve" if and only if test_result.verdict == "pass".
Vote "reject" if test_result.verdict == "needs_fixes" or tests are failing.
```

---

## Performance Metrics

### Successful Test Case: Factorial Implementation

**Task**: Create Python factorial function with error handling and tests.

**Results**:
- **Duration**: 5-10 minutes
- **Phases Completed**: 6/6
- **Auto-Fix Iterations**: 2-3
- **Files Created**: 1 (factorial.py with tests)
- **Test Pass Rate**: 100% after fixes
- **Consensus**: 100% approval (5/5 agents)

### Failing Test Case: DFL Docker Build (Infrastructure Limitations)

**Task**: Build production Docker images for DeepFaceLab on RTX 4090.

**Results**:
- **Duration**: 18 minutes
- **Phases Completed**: 6/6
- **Auto-Fix Iterations**: 3 (reached limit)
- **Files Created**: 15 (Dockerfiles, scripts, docs)
- **Test Pass Rate**: 0% (sandbox lacks Docker runtime)
- **Consensus**: 0% approval (0/5 agents) - **CORRECT BEHAVIOR**

**Why Correct**: Agents properly rejected incomplete work based on objective test failures.

### Key Metrics

| Metric                     | Target    | Actual   |
|----------------------------|-----------|----------|
| Zero Human Intervention    | Required  | ✅ Yes   |
| Real LLM Calls             | Required  | ✅ Yes   |
| Objective Test Execution   | Required  | ✅ Yes   |
| Auto-Fix Capability        | Required  | ✅ Yes   |
| Quality-Based Consensus    | Required  | ✅ Yes   |
| File Creation Capability   | Required  | ✅ Yes   |
| Infrastructure Awareness   | Desired   | ✅ Yes   |

---

## Advanced Configuration

### Custom Agent Roles

Add new agent types in `aav3_agents.py`:

```python
ROLE_PROMPTS = {
    # Existing agents...
    "security_auditor": """
    You are a security auditor. Review code for security vulnerabilities,
    including SQL injection, XSS, CSRF, insecure dependencies, and secrets.
    Provide specific remediation steps.
    """,
    "performance_optimizer": """
    You are a performance optimization expert. Analyze code for performance
    bottlenecks, suggest algorithmic improvements, and recommend caching strategies.
    """
}
```

Register in orchestrator:
```python
self.agents = {
    # Existing agents...
    "security": AAv3AgentReal("security_auditor", f"security_{self.session_id}"),
    "perf": AAv3AgentReal("performance_optimizer", f"perf_{self.session_id}"),
}
```

### Custom Test Types

Add test execution logic in orchestrator:

```python
def _run_custom_test(self, file_path: Path, workspace_dir: Path) -> Dict:
    """Run custom validation logic."""
    if file_path.suffix == '.rs':  # Rust code
        result = subprocess.run(
            ['cargo', 'check'],
            cwd=str(workspace_dir),
            capture_output=True,
            timeout=120
        )
        return {
            "test": f"Rust check: {file_path.name}",
            "result": "pass" if result.returncode == 0 else "fail",
            "error": result.stderr.decode() if result.returncode != 0 else ""
        }
```

### Consensus Threshold Adjustment

Change approval threshold in `_consensus_phase`:

```python
# Current: 80% (4/5)
approval_threshold = 0.80

# Strict: 100% (5/5)
approval_threshold = 1.0

# Lenient: 60% (3/5)
approval_threshold = 0.60
```

---

## Roadmap & Future Enhancements

### Planned Features

1. **Multi-Task Orchestration**: Handle multiple tasks in parallel
2. **Learning from History**: Agents learn from past successes/failures
3. **Cost Optimization**: Cache common patterns to reduce LLM calls
4. **Sandboxed Execution**: Full Docker/VM isolation for untrusted code
5. **Web UI Dashboard**: Real-time monitoring and control interface
6. **Distributed Execution**: Run agents across multiple machines
7. **Custom LLM Backends**: Support for local models (Llama, Mistral)

### Known Limitations

1. **Infrastructure Awareness**: ✅ IMPROVED - Now detects unavailable tools (Docker, GPU, etc.) during preflight and informs Planner. Prevents proposing impossible tests. Note: Agents may still struggle with workarounds in limited environments.
2. **Cost**: Real LLM calls can be expensive for complex tasks
3. **Time**: Full workflow can take 10-30 minutes for complex tasks
4. **Determinism**: LLM responses vary, results not 100% reproducible

---

## Appendix A: File Locations Reference

```
scripts/aav3_orchestrator_real.py       # Main orchestrator (730 lines)
scripts/aav3_shared_memory.py           # Shared memory (150 lines)
src/agents/aav3_agents.py               # Agent implementations (400 lines)
src/agents/agent_wrapper.py            # LLM call wrapper (100 lines)
src/utils/environment_check.py          # Environment capability detection (388 lines)
src/utils/test_adapters.py              # GPU & security test adapters (475 lines)
tasks/aav3_test_simple.md               # Simple test task
tasks/build_dfl_docker_rtx4090.md       # Complex Docker task
reports/aav3_real_sessions/             # Session outputs directory
```

## Appendix B: Critical Code Locations

| Feature                     | File                              | Line(s) |
|-----------------------------|-----------------------------------|---------|
| Max rounds configuration    | `aav3_orchestrator_real.py`       | 35      |
| Auto-fix loop               | `aav3_orchestrator_real.py`       | 126-136 |
| Python syntax test fix      | `aav3_orchestrator_real.py`       | 484     |
| Docker build path fix       | `aav3_orchestrator_real.py`       | 524     |
| Role prompts                | `aav3_agents.py`                  | 50-150  |
| LLM call wrapper            | `agent_wrapper.py`                | 10-30   |
| Shared memory               | `aav3_shared_memory.py`           | 20-100  |

## Appendix C: Example Session Output

**Session**: `aav3_real_4da8282e`
**Task**: Build DFL Docker images
**Duration**: 18.4 minutes (1105 seconds)

**Files Created**:
- `docker/Dockerfile.base` (2227 bytes)
- `docker/Dockerfile.dfl` (2224 bytes)
- `docker/.dockerignore` (227 bytes)
- `scripts/build_base.sh` (584 bytes)
- `scripts/build_dfl.sh` (950 bytes)
- `scripts/test_gpu.sh` (325 bytes)
- `scripts/test_tf_gpu.py` (591 bytes)
- `scripts/test_dfl_smoke.sh` (528 bytes)
- `scripts/export_images.sh` (1286 bytes)
- `docker-compose.yml` (446 bytes)
- `dfl/entrypoint.sh` (1030 bytes)
- `docs/DFL_DOCKER.md` (1181 bytes)
- `docs/VERSION_MATRIX.md` (713 bytes)
- `metadata/version_matrix.json` (292 bytes)
- `staging/README.txt` (174 bytes)

**Test Iterations**: 3
**Final Consensus**: 0% approval (correctly rejected due to failing tests)

---

## Support & Contribution

### Getting Help

1. Check this documentation first
2. Review troubleshooting section
3. Examine session logs in `reports/aav3_real_sessions/`
4. Open GitHub issue with session ID and logs

### Contributing

1. Fork repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request with detailed description

---

## License

[Your License Here]

## Changelog

### v1.1.0 (2025-10-30)

- ✅ **Environment Capability Detection**: Preflight environment scanning before Phase 1 Planning
  - Detects Docker availability and configuration (compose, buildx, network)
  - GPU detection (NVIDIA/AMD/Apple Silicon) with CUDA version
  - Programming language runtime detection (Python, Node.js, Rust, Go, Java)
  - Security tool detection (git, grep, trivy, syft, grype)
  - Network connectivity checks (internet, GitHub, PyPI, npm)
  - Multimedia tool detection (ffmpeg, imagemagick, opencv)
- ✅ **Environment Constraint Context for Planner**: Planner agent receives formatted constraints
  - "⚠ Docker NOT available: Do not propose Docker builds..." format
  - Directly addresses DFL Docker failure scenario
  - Saves environment report to session directory
- ✅ **GPU Smoke Test Adapter**: Extensible test adapter for GPU testing
  - nvidia-smi GPU detection
  - CUDA compiler (nvcc) availability check
  - CUDA program compilation and execution test
  - TensorFlow GPU availability test
  - PyTorch GPU availability test
- ✅ **Security Scan Adapter**: Extensible test adapter for security scanning
  - Regex-based secrets detection (API keys, AWS credentials, GitHub tokens, passwords, private keys)
  - SBOM generation via syft, pip list, or npm list
  - Vulnerability scanning via grype or pip-audit with severity breakdown
- ✅ **Improved Infrastructure Awareness**: System now prevents proposing tests for unavailable tools

### v1.0.0 (2025-10-30)

- ✅ Initial release with full autonomous operation
- ✅ 50-round auto-fix persistence
- ✅ Fixed Docker build path resolution
- ✅ Fixed Python syntax test path resolution
- ✅ Objective quality-based consensus
- ✅ Real LLM agent calls (no simulations)
- ✅ Six-phase deliberation workflow
- ✅ Shared memory for agent communication

---

**Document Version**: 1.1.0
**Last Updated**: 2025-10-30
**Author**: AAv3 Development Team
**Status**: Production Ready
