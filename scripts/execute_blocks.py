#!/usr/bin/env python3
"""
Execute-Block Parser - Deterministic Command Execution

Parses task files for:
- EXECUTE: blocks (explicit commands)
- SUCCESS_CRITERIA: blocks (verification)

No LLM interpretation - runs commands exactly as written.
"""
from __future__ import annotations
from pathlib import Path
import re

EXECUTE_RE = re.compile(r'(?im)^\s*EXECUTE:\s*\n(?P<body>.*?)(?:^\s*(SUCCESS_CRITERIA:|\Z))', re.S|re.M)
SUCCESS_RE = re.compile(r'(?im)^\s*SUCCESS_CRITERIA:\s*\n(?P<body>.*)', re.S|re.M)

def _strip_codefences(text: str) -> str:
    """Remove triple-fence wrappers if present"""
    text = re.sub(r'(?s)```.*?\n(.*?)```', r'\1', text)
    return text.strip()

def parse_task(path: str|Path) -> dict:
    """
    Parse task file for EXECUTE and SUCCESS_CRITERIA blocks.

    Returns:
        {
            "commands": ["cmd1", "cmd2", ...],
            "criteria": [
                {"type": "file", "path": "/workspace/test.txt"},
                {"type": "command", "cmd": "docker images | grep test"},
                {"type": "grep", "pattern": "CUDA", "path": "/workspace/gpu.txt"}
            ]
        }
    """
    raw = Path(path).read_text(encoding="utf-8")
    exm = EXECUTE_RE.search(raw)
    scm = SUCCESS_RE.search(raw)

    if not exm:
        raise ValueError("No EXECUTE: block found. Add:\n\nEXECUTE:\n<one-bash-command-per-line>")

    execute = _strip_codefences(exm.group("body"))
    success = _strip_codefences(scm.group("body")) if scm else ""

    # Build command list, preserving heredocs (<<'EOF' ... EOF on their own lines)
    cmds = []
    buf = []
    in_heredoc = False
    end_token = None

    for line in execute.splitlines():
        if in_heredoc:
            buf.append(line)
            if line.strip() == end_token:
                cmds.append("\n".join(buf))
                buf, in_heredoc, end_token = [], False, None
            continue

        if "<<'" in line or '<<"' in line or "<< " in line:
            # Detect heredoc terminator token at end of line
            m = re.search(r"<<\s*'?\"?(\w+)'?\"?\s*$", line)
            end_token = (m.group(1) if m else "EOF")
            buf = [line]
            in_heredoc = True
        elif line.strip():
            cmds.append(line.strip())

    # Parse success criteria
    # Supported forms:
    # - File exists: /path
    # - command: <bash returns 0>
    # - grep: <regex> in /path
    criteria = []
    for line in (success.splitlines() if success else []):
        s = line.strip()
        if not s or s.startswith("#"):
            continue

        if s.lower().startswith("file exists:"):
            criteria.append({"type": "file", "path": s.split(":", 1)[1].strip()})
        elif s.lower().startswith("command:"):
            criteria.append({"type": "command", "cmd": s.split(":", 1)[1].strip()})
        elif s.lower().startswith("grep:"):
            m = re.match(r"grep:\s*(.+?)\s+in\s+(.+)$", s, re.I)
            if m:
                criteria.append({
                    "type": "grep",
                    "pattern": m.group(1).strip(),
                    "path": m.group(2).strip()
                })

    return {"commands": cmds, "criteria": criteria}


if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        print("Usage: python execute_blocks.py <task_file>")
        sys.exit(1)

    parsed = parse_task(sys.argv[1])
    print(json.dumps(parsed, indent=2))
