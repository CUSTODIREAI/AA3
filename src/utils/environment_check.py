"""
Environment Capability Detection for AAv3 REAL

Performs preflight checks of available tools and resources before planning.
Prevents agents from proposing tests that can't execute in current environment.
"""

import subprocess
import shutil
from pathlib import Path
from typing import Dict, List
import json


def check_docker() -> Dict:
    """Check Docker availability and configuration."""
    result = {
        "available": False,
        "version": None,
        "compose": False,
        "buildx": False,
        "network": False
    }

    try:
        # Check docker command
        docker_version = subprocess.run(
            ['docker', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if docker_version.returncode == 0:
            result["available"] = True
            result["version"] = docker_version.stdout.strip()

            # Check docker-compose
            compose_check = subprocess.run(
                ['docker', 'compose', 'version'],
                capture_output=True,
                timeout=5
            )
            result["compose"] = compose_check.returncode == 0

            # Check buildx
            buildx_check = subprocess.run(
                ['docker', 'buildx', 'version'],
                capture_output=True,
                timeout=5
            )
            result["buildx"] = buildx_check.returncode == 0

            # Check network access (try to ping Docker Hub)
            network_check = subprocess.run(
                ['docker', 'pull', '--help'],
                capture_output=True,
                timeout=5
            )
            result["network"] = network_check.returncode == 0

    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass

    return result


def check_gpu() -> Dict:
    """Check GPU availability (NVIDIA/AMD/Apple Silicon)."""
    result = {
        "nvidia": False,
        "amd": False,
        "apple_silicon": False,
        "cuda_version": None,
        "devices": []
    }

    # Check NVIDIA GPU
    try:
        nvidia_smi = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,driver_version,memory.total', '--format=csv,noheader'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if nvidia_smi.returncode == 0:
            result["nvidia"] = True
            result["devices"] = [line.strip() for line in nvidia_smi.stdout.strip().split('\n')]

            # Get CUDA version
            cuda_check = subprocess.run(
                ['nvcc', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if cuda_check.returncode == 0:
                for line in cuda_check.stdout.split('\n'):
                    if 'release' in line.lower():
                        result["cuda_version"] = line.strip()
                        break
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass

    # Check AMD GPU (rocm-smi)
    try:
        rocm_check = subprocess.run(
            ['rocm-smi', '--showproductname'],
            capture_output=True,
            text=True,
            timeout=5
        )
        result["amd"] = rocm_check.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass

    # Check Apple Silicon GPU
    try:
        import platform
        if platform.system() == 'Darwin' and platform.processor() == 'arm':
            result["apple_silicon"] = True
    except Exception:
        pass

    return result


def check_multimedia_tools() -> Dict:
    """Check availability of multimedia processing tools."""
    tools = {
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "ffprobe": shutil.which("ffprobe") is not None,
        "imagemagick": shutil.which("convert") is not None,
        "opencv": False
    }

    # Check OpenCV (Python)
    try:
        import cv2
        tools["opencv"] = True
    except ImportError:
        pass

    return tools


def check_programming_languages() -> Dict:
    """Check available programming language runtimes."""
    languages = {}

    checks = {
        "python": ["python", "--version"],
        "python3": ["python3", "--version"],
        "node": ["node", "--version"],
        "npm": ["npm", "--version"],
        "rust": ["rustc", "--version"],
        "cargo": ["cargo", "--version"],
        "go": ["go", "version"],
        "java": ["java", "-version"],
        "javac": ["javac", "-version"]
    }

    for lang, cmd in checks.items():
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            languages[lang] = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            languages[lang] = False

    return languages


def check_security_tools() -> Dict:
    """Check availability of security scanning tools."""
    tools = {
        "git": shutil.which("git") is not None,
        "grep": shutil.which("grep") is not None,
        "rg": shutil.which("rg") is not None,  # ripgrep for secrets
        "trivy": shutil.which("trivy") is not None,  # container scanning
        "syft": shutil.which("syft") is not None,  # SBOM generation
        "grype": shutil.which("grype") is not None,  # vulnerability scanning
    }

    return tools


def check_network_access() -> Dict:
    """Check network connectivity and access."""
    result = {
        "internet": False,
        "github": False,
        "pypi": False,
        "npm_registry": False
    }

    # Basic internet check (ping 8.8.8.8)
    try:
        ping_check = subprocess.run(
            ['ping', '-c', '1', '-W', '2', '8.8.8.8'],
            capture_output=True,
            timeout=3
        )
        result["internet"] = ping_check.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass

    # Check specific services (DNS lookup)
    services = {
        "github": "github.com",
        "pypi": "pypi.org",
        "npm_registry": "registry.npmjs.org"
    }

    for service, host in services.items():
        try:
            dns_check = subprocess.run(
                ['nslookup', host],
                capture_output=True,
                timeout=3
            )
            result[service] = dns_check.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            pass

    return result


def get_environment_capabilities() -> Dict:
    """
    Run all environment checks and return comprehensive capabilities report.

    Returns:
        Dict with keys: docker, gpu, multimedia, languages, security, network, summary
    """
    capabilities = {
        "docker": check_docker(),
        "gpu": check_gpu(),
        "multimedia": check_multimedia_tools(),
        "languages": check_programming_languages(),
        "security": check_security_tools(),
        "network": check_network_access()
    }

    # Generate human-readable summary
    summary_lines = []

    # Docker summary
    if capabilities["docker"]["available"]:
        summary_lines.append(f"✓ Docker: {capabilities['docker']['version']}")
        if capabilities["docker"]["compose"]:
            summary_lines.append("  - Docker Compose available")
    else:
        summary_lines.append("✗ Docker: NOT AVAILABLE (Docker builds/tests will fail)")

    # GPU summary
    if capabilities["gpu"]["nvidia"]:
        summary_lines.append(f"✓ NVIDIA GPU: {len(capabilities['gpu']['devices'])} device(s)")
        if capabilities["gpu"]["cuda_version"]:
            summary_lines.append(f"  - {capabilities['gpu']['cuda_version']}")
    elif capabilities["gpu"]["amd"]:
        summary_lines.append("✓ AMD GPU detected")
    elif capabilities["gpu"]["apple_silicon"]:
        summary_lines.append("✓ Apple Silicon GPU detected")
    else:
        summary_lines.append("✗ No GPU detected (GPU tests will be skipped)")

    # Network summary
    if capabilities["network"]["internet"]:
        summary_lines.append("✓ Network: Internet access available")
    else:
        summary_lines.append("✗ Network: NO INTERNET (downloads/clones will fail)")

    # Languages summary
    available_langs = [lang for lang, avail in capabilities["languages"].items() if avail]
    summary_lines.append(f"✓ Languages: {', '.join(available_langs)}")

    capabilities["summary"] = "\n".join(summary_lines)

    return capabilities


def generate_planner_context(capabilities: Dict) -> str:
    """
    Generate context string for Planner agent about environment limitations.

    Args:
        capabilities: Output from get_environment_capabilities()

    Returns:
        Formatted string for inclusion in Planner's system prompt
    """
    context_lines = [
        "ENVIRONMENT CAPABILITIES & CONSTRAINTS:",
        "=" * 60,
        ""
    ]

    # Critical constraints
    constraints = []

    if not capabilities["docker"]["available"]:
        constraints.append(
            "⚠ Docker NOT available: Do not propose Docker builds, container tests, "
            "or Dockerfile validation. Suggest static analysis of Dockerfiles only."
        )

    if not any(capabilities["gpu"].values()):
        constraints.append(
            "⚠ No GPU detected: Do not propose GPU-dependent tests (TensorFlow GPU, "
            "CUDA kernels, GPU rendering). CPU-only tests recommended."
        )

    if not capabilities["network"]["internet"]:
        constraints.append(
            "⚠ No network access: Do not propose tests requiring downloads, git clone, "
            "pip install, npm install, or external API calls. Use pre-existing files only."
        )

    if constraints:
        context_lines.append("CRITICAL CONSTRAINTS:")
        context_lines.extend(constraints)
        context_lines.append("")

    # Available capabilities
    context_lines.append("AVAILABLE CAPABILITIES:")

    if capabilities["docker"]["available"]:
        context_lines.append(f"✓ Docker: {capabilities['docker']['version']}")
        if capabilities["docker"]["compose"]:
            context_lines.append("  - Docker Compose: Can test multi-container setups")
        if capabilities["docker"]["buildx"]:
            context_lines.append("  - Buildx: Can test multi-platform builds")

    if capabilities["gpu"]["nvidia"]:
        context_lines.append(f"✓ NVIDIA GPU: {len(capabilities['gpu']['devices'])} device(s)")
        context_lines.append(f"  - Can test: CUDA code, TensorFlow GPU, PyTorch GPU, GPU rendering")

    if capabilities["network"]["internet"]:
        context_lines.append("✓ Network: Can download dependencies, clone repos, test APIs")

    # Available languages
    available = [k for k, v in capabilities["languages"].items() if v]
    if available:
        context_lines.append(f"✓ Languages: {', '.join(available)}")

    # Security tools
    sec_tools = [k for k, v in capabilities["security"].items() if v]
    if sec_tools:
        context_lines.append(f"✓ Security tools: {', '.join(sec_tools)}")

    context_lines.append("")
    context_lines.append("RECOMMENDATION: Choose tests that match available capabilities.")
    context_lines.append("=" * 60)

    return "\n".join(context_lines)


if __name__ == "__main__":
    # CLI: Print environment report
    import sys

    print("Scanning environment capabilities...\n")

    caps = get_environment_capabilities()

    # Print summary
    print(caps["summary"])
    print()

    # Print planner context
    print(generate_planner_context(caps))
    print()

    # Save to JSON
    output_file = Path("environment_capabilities.json")
    with output_file.open('w') as f:
        json.dump(caps, f, indent=2)

    print(f"Full report saved to: {output_file}")

    sys.exit(0)
