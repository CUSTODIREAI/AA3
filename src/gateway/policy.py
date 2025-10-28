from pathlib import Path
import yaml, json, re
import os

class Policy:
    def __init__(self, path='configs/policy.yaml'):
        # Determine project root (where configs/ dir exists)
        if Path(path).exists():
            self.project_root = Path.cwd()
        else:
            # Try to find project root by looking for configs dir
            cwd = Path.cwd()
            while cwd != cwd.parent:
                if (cwd / 'configs' / 'policy.yaml').exists():
                    self.project_root = cwd
                    path = cwd / path
                    break
                cwd = cwd.parent
            else:
                self.project_root = Path.cwd()

        self.cfg = yaml.safe_load(Path(path).read_text(encoding='utf-8'))

    def within_roots(self, p: Path, roots:list[str]) -> bool:
        pr = p.resolve()
        for r in roots:
            # Resolve root relative to project root
            if Path(r).is_absolute():
                rp = Path(r).resolve()
            else:
                rp = (self.project_root / r).resolve()
            try:
                pr.relative_to(rp)
                return True
            except Exception:
                continue
        return False

    def is_protected(self, p: Path) -> bool:
        roots = self.cfg.get('constraints', {}).get('protected_ro_roots', [])
        return self.within_roots(p, roots)

    def is_writable(self, p: Path) -> bool:
        roots = self.cfg.get('constraints', {}).get('write_roots', [])
        return self.within_roots(p, roots)

    def allow_action_type(self, t: str) -> bool:
        return any(a.get('type') == t for a in self.cfg.get('actions', []))

    def job_id_ok(self, job_id: str) -> bool:
        a = next((x for x in self.cfg['actions'] if x['type']=='job.stop'), None)
        if not a: return False
        return re.match(a['job_id_regex'], job_id) is not None
