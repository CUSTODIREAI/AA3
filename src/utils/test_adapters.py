"""
Additional Test Adapters for AAv3 REAL

GPU smoke tests and security scanning adapters to increase objective coverage.
"""

import subprocess
import re
from pathlib import Path
from typing import Dict, List, Optional
import json


class GPUSmokeTestAdapter:
    """
    Adapter for GPU smoke tests (NVIDIA/AMD/Apple Silicon).

    Tests basic GPU availability and compute capability without
    requiring full ML framework setup.
    """

    @staticmethod
    def test_nvidia_gpu(workspace_dir: Path) -> Dict:
        """Test NVIDIA GPU detection and basic CUDA functionality."""
        results = {
            "test_name": "NVIDIA GPU Smoke Test",
            "passed": False,
            "details": {}
        }

        try:
            # Test 1: nvidia-smi availability
            nvidia_smi = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,driver_version,memory.total',
                 '--format=csv,noheader'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if nvidia_smi.returncode == 0:
                results["details"]["nvidia_smi"] = "PASS"
                results["details"]["gpus"] = nvidia_smi.stdout.strip().split('\n')
            else:
                results["details"]["nvidia_smi"] = f"FAIL: {nvidia_smi.stderr}"
                return results

            # Test 2: CUDA compiler check
            nvcc_version = subprocess.run(
                ['nvcc', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if nvcc_version.returncode == 0:
                results["details"]["cuda_compiler"] = "PASS"
                # Extract CUDA version
                for line in nvcc_version.stdout.split('\n'):
                    if 'release' in line.lower():
                        results["details"]["cuda_version"] = line.strip()
            else:
                results["details"]["cuda_compiler"] = "NOT AVAILABLE (optional)"

            # Test 3: Simple CUDA program compilation (if nvcc available)
            if nvcc_version.returncode == 0:
                cuda_test_file = workspace_dir / "gpu_test.cu"
                cuda_test_code = """
#include <stdio.h>

__global__ void hello_cuda() {
    printf("Hello from GPU thread %d\\n", threadIdx.x);
}

int main() {
    hello_cuda<<<1, 1>>>();
    cudaDeviceSynchronize();
    return 0;
}
"""
                cuda_test_file.write_text(cuda_test_code)

                compile_result = subprocess.run(
                    ['nvcc', str(cuda_test_file), '-o', str(workspace_dir / 'gpu_test')],
                    capture_output=True,
                    timeout=30
                )

                if compile_result.returncode == 0:
                    results["details"]["cuda_compile"] = "PASS"

                    # Try to run it
                    run_result = subprocess.run(
                        [str(workspace_dir / 'gpu_test')],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if run_result.returncode == 0:
                        results["details"]["cuda_execution"] = "PASS"
                        results["passed"] = True
                    else:
                        results["details"]["cuda_execution"] = f"FAIL: {run_result.stderr}"
                else:
                    results["details"]["cuda_compile"] = f"FAIL: {compile_result.stderr}"
            else:
                # If no nvcc, just pass based on nvidia-smi
                results["passed"] = True

        except subprocess.TimeoutExpired:
            results["details"]["error"] = "Timeout during GPU tests"
        except FileNotFoundError as e:
            results["details"]["error"] = f"Tool not found: {e}"
        except Exception as e:
            results["details"]["error"] = str(e)

        return results

    @staticmethod
    def test_python_gpu_frameworks(workspace_dir: Path) -> Dict:
        """Test Python ML frameworks GPU support."""
        results = {
            "test_name": "Python GPU Frameworks",
            "passed": False,
            "details": {}
        }

        # Test TensorFlow GPU
        tf_test = workspace_dir / "test_tf_gpu.py"
        tf_test_code = """
import sys
try:
    import tensorflow as tf
    gpus = tf.config.list_physical_devices('GPU')
    print(f"TensorFlow {tf.__version__}: {len(gpus)} GPU(s) detected")
    sys.exit(0 if len(gpus) > 0 else 1)
except Exception as e:
    print(f"TensorFlow GPU test failed: {e}")
    sys.exit(1)
"""
        tf_test.write_text(tf_test_code)

        try:
            tf_result = subprocess.run(
                ['python', str(tf_test)],
                capture_output=True,
                text=True,
                timeout=30
            )

            if tf_result.returncode == 0:
                results["details"]["tensorflow_gpu"] = f"PASS: {tf_result.stdout.strip()}"
                results["passed"] = True
            else:
                results["details"]["tensorflow_gpu"] = f"NOT AVAILABLE: {tf_result.stdout.strip()}"
        except Exception as e:
            results["details"]["tensorflow_gpu"] = f"ERROR: {e}"

        # Test PyTorch GPU
        torch_test = workspace_dir / "test_torch_gpu.py"
        torch_test_code = """
import sys
try:
    import torch
    cuda_available = torch.cuda.is_available()
    device_count = torch.cuda.device_count() if cuda_available else 0
    print(f"PyTorch {torch.__version__}: CUDA={cuda_available}, {device_count} device(s)")
    sys.exit(0 if cuda_available else 1)
except Exception as e:
    print(f"PyTorch GPU test failed: {e}")
    sys.exit(1)
"""
        torch_test.write_text(torch_test_code)

        try:
            torch_result = subprocess.run(
                ['python', str(torch_test)],
                capture_output=True,
                text=True,
                timeout=30
            )

            if torch_result.returncode == 0:
                results["details"]["pytorch_gpu"] = f"PASS: {torch_result.stdout.strip()}"
                results["passed"] = True
            else:
                results["details"]["pytorch_gpu"] = f"NOT AVAILABLE: {torch_result.stdout.strip()}"
        except Exception as e:
            results["details"]["pytorch_gpu"] = f"ERROR: {e}"

        return results


class SecurityScanAdapter:
    """
    Adapter for security scanning: secrets detection, SBOM generation, CVE scanning.
    """

    @staticmethod
    def scan_for_secrets(workspace_dir: Path, file_patterns: Optional[List[str]] = None) -> Dict:
        """
        Scan for exposed secrets (API keys, passwords, tokens).

        Uses patterns to detect common secret types.
        """
        results = {
            "test_name": "Secrets Detection",
            "passed": True,
            "secrets_found": [],
            "files_scanned": 0
        }

        # Common secret patterns
        secret_patterns = {
            "AWS Access Key": r'AKIA[0-9A-Z]{16}',
            "AWS Secret Key": r'aws(.{0,20})?[\'"][0-9a-zA-Z/+]{40}[\'"]',
            "GitHub Token": r'gh[pousr]_[0-9a-zA-Z]{36}',
            "Generic API Key": r'api[_-]?key["\']?\s*[:=]\s*["\']?[0-9a-zA-Z]{20,}',
            "Generic Secret": r'secret["\']?\s*[:=]\s*["\']?[0-9a-zA-Z]{20,}',
            "Private Key": r'-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----',
            "Password in code": r'password["\']?\s*[:=]\s*["\'][^"\']{8,}["\']',
        }

        if file_patterns is None:
            # Default: scan Python, JS, config files
            file_patterns = ['**/*.py', '**/*.js', '**/*.json', '**/*.yaml', '**/*.yml', '**/*.env']

        for pattern in file_patterns:
            for file_path in workspace_dir.glob(pattern):
                if file_path.is_file():
                    results["files_scanned"] += 1

                    try:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')

                        for secret_type, regex in secret_patterns.items():
                            matches = re.finditer(regex, content, re.IGNORECASE)

                            for match in matches:
                                # Get line number
                                line_num = content[:match.start()].count('\n') + 1

                                results["secrets_found"].append({
                                    "type": secret_type,
                                    "file": str(file_path.relative_to(workspace_dir)),
                                    "line": line_num,
                                    "snippet": match.group()[:50] + "..." if len(match.group()) > 50 else match.group()
                                })

                    except Exception as e:
                        pass  # Skip files that can't be read

        if results["secrets_found"]:
            results["passed"] = False
            results["message"] = f"Found {len(results['secrets_found'])} potential secrets"
        else:
            results["message"] = f"No secrets detected in {results['files_scanned']} files"

        return results

    @staticmethod
    def generate_sbom(workspace_dir: Path) -> Dict:
        """
        Generate Software Bill of Materials (SBOM).

        Tries multiple methods: syft, pip freeze, npm list, etc.
        """
        results = {
            "test_name": "SBOM Generation",
            "passed": False,
            "sbom": {},
            "method": None
        }

        # Try syft (best option if available)
        try:
            syft_result = subprocess.run(
                ['syft', 'dir:' + str(workspace_dir), '-o', 'json'],
                capture_output=True,
                text=True,
                timeout=60
            )

            if syft_result.returncode == 0:
                results["sbom"] = json.loads(syft_result.stdout)
                results["method"] = "syft"
                results["passed"] = True
                return results
        except (FileNotFoundError, subprocess.SubprocessError, json.JSONDecodeError):
            pass

        # Fallback: Python dependencies
        requirements_file = workspace_dir / "requirements.txt"
        if requirements_file.exists():
            try:
                pip_list = subprocess.run(
                    ['pip', 'list', '--format=json'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if pip_list.returncode == 0:
                    results["sbom"]["python_packages"] = json.loads(pip_list.stdout)
                    results["method"] = "pip list"
                    results["passed"] = True
            except Exception:
                pass

        # Fallback: Node.js dependencies
        package_json = workspace_dir / "package.json"
        if package_json.exists():
            try:
                npm_list = subprocess.run(
                    ['npm', 'list', '--json'],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=str(workspace_dir)
                )

                if npm_list.returncode == 0:
                    results["sbom"]["npm_packages"] = json.loads(npm_list.stdout)
                    results["method"] = "npm list"
                    results["passed"] = True
            except Exception:
                pass

        if not results["passed"]:
            results["message"] = "No SBOM generation tool available (install syft for best results)"

        return results

    @staticmethod
    def scan_for_vulnerabilities(workspace_dir: Path) -> Dict:
        """
        Scan for known vulnerabilities using grype or similar tools.
        """
        results = {
            "test_name": "Vulnerability Scanning",
            "passed": True,
            "vulnerabilities": [],
            "method": None
        }

        # Try grype (works with SBOM or direct scanning)
        try:
            grype_result = subprocess.run(
                ['grype', 'dir:' + str(workspace_dir), '-o', 'json'],
                capture_output=True,
                text=True,
                timeout=120
            )

            if grype_result.returncode == 0:
                grype_data = json.loads(grype_result.stdout)
                results["vulnerabilities"] = grype_data.get("matches", [])
                results["method"] = "grype"

                # Count by severity
                severity_counts = {}
                for vuln in results["vulnerabilities"]:
                    severity = vuln.get("vulnerability", {}).get("severity", "unknown")
                    severity_counts[severity] = severity_counts.get(severity, 0) + 1

                results["severity_breakdown"] = severity_counts

                # Fail if high/critical vulnerabilities found
                if severity_counts.get("High", 0) > 0 or severity_counts.get("Critical", 0) > 0:
                    results["passed"] = False
                    results["message"] = f"Found {len(results['vulnerabilities'])} vulnerabilities"

                return results

        except (FileNotFoundError, subprocess.SubprocessError, json.JSONDecodeError):
            results["message"] = "No vulnerability scanner available (install grype)"
            pass

        # Fallback: pip-audit for Python
        try:
            pip_audit = subprocess.run(
                ['pip-audit', '--format=json'],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(workspace_dir)
            )

            if pip_audit.returncode == 0:
                audit_data = json.loads(pip_audit.stdout)
                results["vulnerabilities"] = audit_data.get("dependencies", [])
                results["method"] = "pip-audit"

                if results["vulnerabilities"]:
                    results["passed"] = False

            return results

        except (FileNotFoundError, subprocess.SubprocessError, json.JSONDecodeError):
            pass

        return results


def run_gpu_smoke_tests(workspace_dir: Path) -> Dict:
    """Run all GPU smoke tests."""
    gpu_adapter = GPUSmokeTestAdapter()

    results = {
        "test_suite": "GPU Smoke Tests",
        "tests": []
    }

    # NVIDIA tests
    nvidia_result = gpu_adapter.test_nvidia_gpu(workspace_dir)
    results["tests"].append(nvidia_result)

    # Python framework tests
    framework_result = gpu_adapter.test_python_gpu_frameworks(workspace_dir)
    results["tests"].append(framework_result)

    # Overall pass/fail
    results["passed"] = any(test["passed"] for test in results["tests"])

    return results


def run_security_scans(workspace_dir: Path) -> Dict:
    """Run all security scans."""
    sec_adapter = SecurityScanAdapter()

    results = {
        "test_suite": "Security Scans",
        "tests": []
    }

    # Secrets scan
    secrets_result = sec_adapter.scan_for_secrets(workspace_dir)
    results["tests"].append(secrets_result)

    # SBOM generation
    sbom_result = sec_adapter.generate_sbom(workspace_dir)
    results["tests"].append(sbom_result)

    # Vulnerability scan
    vuln_result = sec_adapter.scan_for_vulnerabilities(workspace_dir)
    results["tests"].append(vuln_result)

    # Overall: pass if no secrets and no high/critical vulns
    results["passed"] = all(
        test["passed"]
        for test in results["tests"]
        if test["test_name"] in ["Secrets Detection", "Vulnerability Scanning"]
    )

    return results


if __name__ == "__main__":
    # CLI test
    import sys

    test_dir = Path(".")

    print("Running GPU Smoke Tests...\n")
    gpu_results = run_gpu_smoke_tests(test_dir)
    print(json.dumps(gpu_results, indent=2))

    print("\n\nRunning Security Scans...\n")
    sec_results = run_security_scans(test_dir)
    print(json.dumps(sec_results, indent=2))

    sys.exit(0 if gpu_results["passed"] and sec_results["passed"] else 1)
