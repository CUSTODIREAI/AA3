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

def ingest_promote_glob(src_dir: str, pattern: str, relative_dst_prefix: str, tags: dict, policy: Policy, plan_id: str='unknown', actor: str='executor'):
    """
    Promote files matching glob pattern to immutable dataset.

    Args:
        src_dir: Source directory (e.g., "staging")
        pattern: Glob pattern (e.g., "**/*" for all files)
        relative_dst_prefix: Prefix for destination paths (e.g., "direct/session-123/")
        tags: Tags to attach to all promoted files
        policy: Policy instance for validation
        plan_id: Plan ID for audit trail
        actor: Actor name for audit trail

    Returns:
        List of results (one per file promoted)
    """
    src_path = Path(src_dir)
    if not src_path.exists():
        return [{'ok': False, 'error': f'src_dir not found: {src_dir}'}]

    # Find all matching files
    matched_files = list(src_path.glob(pattern))
    matched_files = [f for f in matched_files if f.is_file()]

    if not matched_files:
        return [{'ok': False, 'error': f'no files matched pattern: {pattern}'}]

    # Convert to items list for ingest_promote
    items = []
    for file_path in matched_files:
        # Calculate relative path from src_dir
        try:
            rel_to_src = file_path.relative_to(src_path)
        except ValueError:
            continue

        # Build destination path with prefix
        relative_dst = str(Path(relative_dst_prefix) / rel_to_src).replace('\\', '/')

        items.append({
            'src': str(file_path),
            'relative_dst': relative_dst,
            'tags': tags
        })

    # Promote all items
    return ingest_promote(items, policy, plan_id, actor)
