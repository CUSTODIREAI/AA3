"""
Task Preprocessor - Smart Capability Hints

Automatically augments task briefs with capability hints based on keywords,
pushing agents toward the right tools for the job.
"""

import re


def augment_task_brief(task_text: str) -> str:
    """
    Add capability hints to task text based on keywords.

    Args:
        task_text: Original task description

    Returns:
        Augmented task text with hints appended
    """
    hints = []

    # Detect keywords and add corresponding hints
    text_lower = task_text.lower()

    # Web/latest/versions → curl/wget hints
    if re.search(r'\b(web|latest|version|current|fetch|api|search)\b', text_lower):
        hints.append(
            "- **Web lookups**: Use `agent.passthrough_shell` to run `curl` or `wget` "
            "and save JSON/text to `/workspace/versions.json` or similar. "
            "Do **not** hardcode versions from knowledge cutoff."
        )

    # Docker/build/image → docker build hints
    if re.search(r'\b(docker|build|image|container)\b', text_lower):
        hints.append(
            "- **Docker builds**: Use `agent.passthrough_shell` to run `docker build` commands **NOW**. "
            "Do **not** only write build scripts without executing them. "
            "Save build logs to `/workspace/build.log`."
        )

    # GPU/CUDA/test → verification hints
    if re.search(r'\b(gpu|cuda|test|verify|check|nvidia)\b', text_lower):
        hints.append(
            "- **GPU/Testing**: Use `agent.passthrough_shell` to run `nvidia-smi`, "
            "`python -c \"import tensorflow; print(tensorflow.config.list_physical_devices('GPU'))\"`,"
            " and other verification commands. "
            "Do **not** only write test scripts - execute them and capture output."
        )

    # Training/model → long-running hints
    if re.search(r'\b(train|model|epoch|batch)\b', text_lower):
        hints.append(
            "- **Training**: Use `agent.passthrough_shell` with appropriate `timeout_sec` parameter "
            "for long-running training jobs."
        )

    # If no hints, return original
    if not hints:
        return task_text

    # Append hints section
    hints_section = "\n\n---\n\n## 🔧 Capability Hints (Auto-Generated)\n\n"
    hints_section += "\n\n".join(hints)
    hints_section += "\n\n**Remember**: Prefer execution via `agent.passthrough_shell` over writing scripts that you don't execute."

    return task_text + hints_section


def preprocess_task_file(task_path: str, output_path: str = None) -> str:
    """
    Read task file, augment with hints, optionally save augmented version.

    Args:
        task_path: Path to original task file
        output_path: Optional path to save augmented task (if None, returns string only)

    Returns:
        Augmented task text
    """
    from pathlib import Path

    task_file = Path(task_path)
    if not task_file.exists():
        raise FileNotFoundError(f"Task file not found: {task_path}")

    with open(task_file, 'r', encoding='utf-8') as f:
        original_text = f.read()

    augmented_text = augment_task_brief(original_text)

    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(augmented_text)

    return augmented_text


if __name__ == "__main__":
    # Test the preprocessor
    test_task = """# Build RTX 4090 Docker Images

## Objective

Build production-ready Docker images for DeepFaceLab on RTX 4090.

## Requirements

- Get latest CUDA version
- Build Docker images
- Test GPU access
"""

    print("=== Original Task ===")
    print(test_task)
    print("\n=== Augmented Task ===")
    print(augment_task_brief(test_task))
