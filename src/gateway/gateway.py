from pathlib import Path
import json, shutil, hashlib, time, os
from .policy import Policy

MANIFEST = Path('dataset/.manifests/dataset_manifest.jsonl')

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1<<20), b''):
            h.update(chunk)
    return h.hexdigest()

def append_manifest(rec: dict):
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')

def ingest_promote(items: list[dict], policy: Policy, plan_id: str='unknown', actor: str='executor'):
    results = []
    for it in items:
        src = Path(it['src']).resolve()
        if not src.exists():
            results.append({'src':str(src),'ok':False,'error':'missing src'}); continue
        if not policy.is_writable(src):
            # must come from staging or workspace per policy; enforce
            results.append({'src':str(src),'ok':False,'error':'src not under writable roots'}); continue
        rel = it.get('relative_dst') or src.name
        # destination under dated prefix
        ts = time.strftime('%Y/%m/%d', time.gmtime())
        dst = Path('dataset') / ts / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            results.append({'src':str(src),'ok':False,'error':'dst exists'}); continue
        # copy, then hash
        shutil.copy2(src, dst)
        digest = sha256_file(dst)
        rec = {
            'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'src': str(src),
            'dst': str(dst),
            'sha256': digest,
            'bytes': dst.stat().st_size,
            'actor': actor,
            'plan_id': plan_id,
            'tags': it.get('tags', {}),
        }
        append_manifest(rec)
        results.append({'src':str(src),'dst':str(dst),'ok':True,'sha256':digest})
    return results
