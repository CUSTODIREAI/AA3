from pathlib import Path
import yaml, json, re

class Policy:
    def __init__(self, path='configs/policy.yaml'):
        self.cfg = yaml.safe_load(Path(path).read_text(encoding='utf-8'))

    def within_roots(self, p: Path, roots:list[str]) -> bool:
        pr = p.resolve()
        for r in roots:
            rp = Path(r).resolve()
            try:
                pr.relative_to(rp)
                return True
            except Exception:
                continue
        return False

    def is_protected(self, p: Path) -> bool:
        return self.within_roots(p, self.cfg.get('protected_ro_roots', []))

    def is_writable(self, p: Path) -> bool:
        return self.within_roots(p, self.cfg.get('write_roots', []))

    def allow_action_type(self, t: str) -> bool:
        return any(a.get('type') == t for a in self.cfg.get('actions', []))

    def job_id_ok(self, job_id: str) -> bool:
        a = next((x for x in self.cfg['actions'] if x['type']=='job.stop'), None)
        if not a: return False
        return re.match(a['job_id_regex'], job_id) is not None
