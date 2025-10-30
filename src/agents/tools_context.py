"""
Available Tools Context Generator

Reads configs/policy.yaml and constructs an "Available Tools" section
to inject into agent prompts, making capabilities visible at every turn.
"""

import yaml
from pathlib import Path


def build_tools_context(policy_path="configs/policy.yaml") -> str:
    """
    Parse policy.yaml and generate a short, human-readable tools listing.

    Returns:
        String to inject into agent prompts showing available action types
    """
    policy_file = Path(policy_path)
    if not policy_file.exists():
        return "**Available tools:** (policy file not found)"

    with open(policy_file, 'r', encoding='utf-8') as f:
        policy = yaml.safe_load(f)

    actions = policy.get('actions', [])

    # Build tool descriptions with focus on passthrough and key capabilities
    tool_lines = [
        "**Available tools (preferred for this task):**\n",
        "* `agent.passthrough_shell` — **PREFERRED**: Run real commands in GPU sandbox (curl/wget for web lookups, docker build for images, GPU tests). Use this for web fetches, builds, and tests instead of writing scripts.",
    ]

    # Add other key actions
    for action in actions:
        action_type = action.get('type', '')

        if action_type == 'fs.write':
            tool_lines.append("* `fs.write` — Write files to staging/ or workspace/ (use only when files need to be promoted, not for scripts that should be executed)")
        elif action_type == 'ingest.promote':
            tool_lines.append("* `ingest.promote` — Append-only publish to immutable dataset/ with SHA-256 hash")
        elif action_type == 'container.run':
            tool_lines.append("* `container.run` — Run Docker containers with --gpus support")
        elif action_type == 'docker.build':
            tool_lines.append("* `docker.build` — Build Docker images (or use agent.passthrough_shell with docker build)")
        elif action_type == 'git.clone':
            tool_lines.append("* `git.clone` — Clone git repositories")
        elif action_type == 'download.ytdlp':
            tool_lines.append("* `download.ytdlp` — Download videos with yt-dlp")

    # Add critical guidance
    tool_lines.extend([
        "",
        "**Key guidance:**",
        "- For tasks mentioning 'web', 'latest', 'versions': Use `agent.passthrough_shell` with curl/wget to fetch current data",
        "- For tasks mentioning 'docker', 'build', 'image': Use `agent.passthrough_shell` to run docker build NOW (don't just write scripts)",
        "- For tasks mentioning 'GPU', 'test', 'cuda': Use `agent.passthrough_shell` to run nvidia-smi and verification tests",
        "- Do NOT write scripts that contain docker build / curl / tests without also EXECUTING them via agent.passthrough_shell",
        ""
    ])

    return "\n".join(tool_lines)


def get_task_required_tools(task_text: str) -> list[str]:
    """
    Analyze task text and return list of tools that should be used.

    Args:
        task_text: The task description text

    Returns:
        List of action type names that task should use
    """
    import re

    required = []
    text_lower = task_text.lower()

    # Web/version lookups
    if re.search(r'\b(web|latest|version|current|fetch|api)\b', text_lower):
        required.append('agent.passthrough_shell')  # for curl/wget

    # Docker builds
    if re.search(r'\b(docker|build|image|container)\b', text_lower):
        required.append('agent.passthrough_shell')  # for docker build

    # GPU/testing
    if re.search(r'\b(gpu|cuda|test|verify|check)\b', text_lower):
        required.append('agent.passthrough_shell')  # for tests

    return list(set(required))  # dedupe


if __name__ == "__main__":
    # Test the context generation
    print(build_tools_context())
    print("\n--- Testing task analysis ---")
    test_task = "Build RTX 4090 Docker images. Get latest CUDA version. Test GPU access."
    print(f"Task: {test_task}")
    print(f"Required tools: {get_task_required_tools(test_task)}")
