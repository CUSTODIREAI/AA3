# AAv3 REAL - Autonomous Agent System v3 (Real LLM Implementation)

[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](https://github.com/CUSTODIREAI/AA3)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**AAv3 REAL** is a sophisticated autonomous multi-agent deliberation system that uses real LLM calls to enable multiple specialized AI agents to collaboratively plan, execute, test, and refine complex software engineering tasks.

## Key Features

- **Multi-Agent Deliberation**: Six specialized agents (Planner, Implementer, Tester, Debugger, Critic, Meta) collaborate through structured phases
- **Real LLM Integration**: Direct OpenAI API calls - no mock responses, no hardcoded plans
- **Environment-Aware Planning**: v1.1.0+ includes preflight system capability detection to prevent impossible tests
- **Iterative Refinement**: Automatic test execution and intelligent fixing based on real failures
- **Comprehensive Testing**: Built-in adapters for Python, Rust, Docker, GPU smoke tests, and security scans
- **Cross-Platform**: Works on Windows (WSL), Linux, and macOS
- **Audit Trail**: Complete session logging with test results, agent decisions, and execution transcripts

## Quick Start

### Prerequisites

- Python 3.10+
- OpenAI API key with GPT-4 access
- Git (for repository operations)
- Docker (optional, for container-based tests)
- NVIDIA GPU + CUDA toolkit (optional, for GPU tests)

### Installation

```bash
# Clone the repository
git clone https://github.com/CUSTODIREAI/AA3.git
cd AA3

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set your OpenAI API key
export OPENAI_API_KEY='your-key-here'  # On Windows: set OPENAI_API_KEY=your-key-here
```

### Basic Usage

Create a task file (e.g., `tasks/my_task.md`):

```markdown
# Build a factorial module

Implement a Python module `factorial.py` that:
- Computes factorial for non-negative integers
- Validates input (rejects negatives, non-integers)
- Includes comprehensive tests
- Has proper documentation
```

Run the orchestrator:

```bash
# On Linux/macOS
python scripts/aav3_orchestrator_real.py --task tasks/my_task.md --max-rounds 3

# On Windows with WSL
cd "X:\path\to\AA3"
wsl bash -c "cd /mnt/x/path/to/AA3 && source venv/bin/activate && python scripts/aav3_orchestrator_real.py --task tasks/my_task.md --max-rounds 3"
```

Results appear in `reports/aav3_real_sessions/<session_id>/`:
- `test_result.json` - Test outcomes and verdict
- `workspace/` - Generated code and test files
- `session_log.json` - Complete conversation history
- `environment_capabilities.json` - System capability report (v1.1.0+)

## Architecture

AAv3 REAL uses a **six-phase workflow** with real LLM deliberation:

```
┌─────────────────────────────────────────────────────────────┐
│                    AAv3 REAL Workflow                        │
├─────────────────────────────────────────────────────────────┤
│  0. Preflight: Environment capability detection (v1.1.0+)   │
│  1. Planning:  Planner proposes test plan                   │
│  2. Critique:  Critic reviews plan for flaws                │
│  3. Revision:  Planner refines based on feedback             │
│  4. Implementation: Implementer creates files                │
│  5. Testing:   Tester executes tests, Debugger fixes issues  │
│  6. Meta-Review: Meta agent evaluates overall quality        │
└─────────────────────────────────────────────────────────────┘
```

### Agent Roles

- **Planner**: Designs test plan with implementation strategy, files to create, and key decisions
- **Critic**: Reviews plans for feasibility, completeness, and potential issues
- **Implementer**: Generates code files based on approved plan
- **Tester**: Executes tests (Python unittest, Rust cargo test, Docker builds, etc.)
- **Debugger**: Analyzes failures and proposes fixes
- **Meta**: Provides high-level evaluation and improvement suggestions

## What's New in v1.1.0

### Environment Capability Detection

AAv3 now performs preflight system scanning to detect available tools and resources before planning:

```python
from src.utils.environment_check import get_environment_capabilities

capabilities = get_environment_capabilities()
# Returns: {docker, gpu, multimedia, languages, security, network}
```

This prevents agents from proposing tests that will fail due to missing system capabilities (e.g., Docker builds when Docker is unavailable).

### Additional Test Adapters

**GPU Smoke Tests** (`src/utils/test_adapters.py`):
- NVIDIA GPU detection via nvidia-smi
- CUDA compiler checks and simple kernel compilation
- TensorFlow and PyTorch GPU availability tests

**Security Scanning** (`src/utils/test_adapters.py`):
- Secrets detection (API keys, tokens, private keys)
- SBOM generation (syft, pip list, npm list)
- Vulnerability scanning (grype, pip-audit)

Example usage:

```python
from src.utils.test_adapters import run_gpu_smoke_tests, run_security_scans

gpu_results = run_gpu_smoke_tests(workspace_dir)
security_results = run_security_scans(workspace_dir)
```

## Project Structure

```
custodire-aa-system/
├── scripts/
│   └── aav3_orchestrator_real.py    # Main orchestrator
├── src/
│   ├── agents/                       # Agent implementations
│   │   ├── planner.py
│   │   ├── critic.py
│   │   ├── implementer.py
│   │   ├── tester.py
│   │   ├── debugger.py
│   │   └── meta.py
│   └── utils/
│       ├── environment_check.py      # Capability detection (v1.1.0+)
│       └── test_adapters.py          # GPU & security tests (v1.1.0+)
├── tasks/                            # Task definition files
├── reports/
│   └── aav3_real_sessions/          # Session outputs
├── docs/
│   └── AAv3_REAL_System_Documentation.md
└── requirements.txt
```

## Environment Variables

```bash
# Required
export OPENAI_API_KEY='your-openai-api-key'

# Optional
export OPENAI_MODEL='gpt-4'           # Default model
export MAX_ROUNDS='3'                 # Maximum deliberation rounds
export LOG_LEVEL='INFO'               # Logging verbosity
```

## Examples

### Example 1: Simple Python Module

```bash
python scripts/aav3_orchestrator_real.py --task tasks/aav3_test_simple.md --max-rounds 2
```

Task: "Create a Python module that computes factorial with full validation and tests."

**Result**: `factorial.py` with comprehensive implementation, input validation, doctests, and test suite.

### Example 2: Docker Build Task

```bash
python scripts/aav3_orchestrator_real.py --task tasks/build_dfl_docker_rtx4090.md --max-rounds 3
```

Task: "Build a Docker image for DeepFaceLab with NVIDIA RTX 4090 support."

**Result**: Dockerfile with CUDA base, proper dependencies, and GPU runtime configuration. *Note: v1.1.0+ will detect if Docker is unavailable and adapt the plan accordingly.*

### Example 3: Rust Project

```bash
python scripts/aav3_orchestrator_real.py --task tasks/rust_cli_tool.md --max-rounds 2
```

Task: "Create a Rust CLI tool that parses JSON and outputs formatted text."

**Result**: `src/main.rs`, `Cargo.toml`, and passing `cargo test` results.

## Testing

Run AAv3's own test suite:

```bash
# Environment capability check
python src/utils/environment_check.py

# GPU smoke tests (requires NVIDIA GPU)
python src/utils/test_adapters.py

# Full system test
python scripts/aav3_orchestrator_real.py --task tasks/aav3_test_simple.md
```

## Known Limitations

- **LLM Costs**: Real OpenAI API calls incur costs (typically $0.10-$2.00 per session depending on task complexity)
- **Execution Time**: Complex tasks may take 5-15 minutes with multiple deliberation rounds
- **Docker Access**: Some environments (Windows, restricted VMs) may have limited Docker functionality
- **GPU Requirements**: GPU tests require actual NVIDIA/AMD hardware with drivers installed
- **Network Dependency**: Requires internet access for LLM API calls and package downloads

## Troubleshooting

### "Docker not available" warnings

AAv3 v1.1.0+ detects this and adapts plans automatically. To enable Docker tests:
- Linux: Install Docker and add user to `docker` group
- Windows: Install Docker Desktop with WSL 2 backend
- Verify: `docker ps` should run without sudo

### "No GPU detected" messages

Normal if system has no GPU. GPU tests will be skipped. To enable:
- Install NVIDIA drivers and CUDA toolkit
- Verify: `nvidia-smi` should show GPU information

### OpenAI API errors

- Check API key: `echo $OPENAI_API_KEY`
- Verify billing: https://platform.openai.com/account/billing
- Rate limits: Add delays between requests or upgrade plan

### WSL path issues (Windows)

Use WSL-style paths: `/mnt/x/path/to/AA3` instead of `X:\path\to\AA3`

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes with tests
4. Commit with clear messages: `git commit -m "Add feature X"`
5. Push and open a Pull Request

## Version History

### v1.1.0 (2025-01-XX)
- **Added**: Environment capability detection (`src/utils/environment_check.py`)
- **Added**: GPU smoke test adapter
- **Added**: Security scan adapter (secrets, SBOM, CVE)
- **Changed**: Planner now receives environment constraints before planning
- **Fixed**: Docker build failures in environments without Docker access
- **Improved**: Documentation with comprehensive examples

### v1.0.0 (2025-01-XX)
- Initial release
- Six-agent deliberation system with real LLM calls
- Python, Rust, and Docker test adapters
- Complete audit trail and session logging

## License

MIT License - see [LICENSE](LICENSE) for details

## Citation

If you use AAv3 REAL in your research or project, please cite:

```bibtex
@software{aav3_real_2025,
  title = {AAv3 REAL: Autonomous Agent System v3},
  author = {Custodire AI},
  year = {2025},
  url = {https://github.com/CUSTODIREAI/AA3}
}
```

## Documentation

- **System Documentation**: [docs/AAv3_REAL_System_Documentation.md](docs/AAv3_REAL_System_Documentation.md)
- **Architecture Details**: See "Core Concepts" in system documentation
- **Agent Protocols**: See "Agent Roles and Responsibilities" section
- **API Reference**: See docstrings in `src/agents/` modules

## Support

- **Issues**: https://github.com/CUSTODIREAI/AA3/issues
- **Discussions**: https://github.com/CUSTODIREAI/AA3/discussions

---

**Built with Claude Code** - Autonomous agent engineering at scale.
