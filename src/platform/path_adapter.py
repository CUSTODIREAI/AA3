from __future__ import annotations
import os, subprocess, sys
from pathlib import Path

def is_wsl() -> bool:
    try:
        txt = Path('/proc/version').read_text()
        return 'microsoft' in txt.lower()
    except Exception:
        return False

def is_windows() -> bool:
    return os.name == 'nt' or sys.platform.startswith('win')

def abspath(p: str|Path) -> Path:
    return Path(p).expanduser().resolve()

def to_wsl_path(win_path: str) -> str:
    try:
        out = subprocess.check_output(['wslpath','-a',win_path], text=True).strip()
        return out
    except Exception:
        drive = win_path[0].lower()
        rest = win_path[2:].replace('\\','/').replace('\','/')
        return f'/mnt/{drive}/{rest.lstrip("/")}'

def docker_mount_host_path(host_path: str|Path) -> str:
    p = abspath(host_path)
    if is_wsl():
        return p.as_posix()
    if is_windows():
        return str(p)
    return p.as_posix()
