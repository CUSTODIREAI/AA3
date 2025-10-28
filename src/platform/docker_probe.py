import subprocess, os
def probe_mount_style() -> str:
    # Returns 'posix' | 'windows' | 'wslposix'
    pref = os.getenv('PREFERRED_MOUNT_STYLE')
    if pref in ('posix','windows','wslposix'):
        return pref
    # Try simple docker info
    try:
        out = subprocess.check_output(['docker','info','-f','{{.OperatingSystem}}'], text=True, timeout=3).lower()
        if 'windows' in out:
            return 'windows'
        return 'posix'
    except Exception:
        return 'posix'
