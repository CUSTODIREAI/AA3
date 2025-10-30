#!/usr/bin/env python3
import os
import re
import json
import sys
from collections import defaultdict, Counter
from pathlib import Path

VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.mpg', '.mpeg', '.m4v'}

DATASET_DIR = r"X:\dataset2\INTELLIGENT_ENTERPRISE_INSTITUTE"

STAGING_DIR = Path("staging/small_test")
STAGING_DIR.mkdir(parents=True, exist_ok=True)

REPORT_JSON = STAGING_DIR / "report.json"

def resolve_dataset_path(p: str) -> Path:
    p_str = p
    as_is = Path(p_str)
    if as_is.exists():
        return as_is
    if len(p_str) >= 2 and p_str[1] == ':':
        drive = p_str[0].lower()
        rest = p_str[2:].replace('\\', '/')
        candidate = Path(f"/mnt/{drive}/{rest.lstrip('/')}")
        if candidate.exists():
            return candidate
    return as_is

def find_sidecar_json(video_path: Path):
    candidates = []
    base = video_path.with_suffix('')
    cand1 = base.with_suffix('.json')
    if cand1.exists():
        candidates.append(cand1)
    folder = video_path.parent
    for j in folder.glob('*.json'):
        if j == cand1:
            continue
        if j.stem.lower() == base.name.lower():
            candidates.append(j)
    for j in candidates:
        try:
            with open(j, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            continue
    return None

def parse_duration(meta):
    if not isinstance(meta, dict):
        return None
    dur = meta.get('duration') or meta.get('sec') or meta.get('length')
    if dur is None:
        return None
    try:
        return float(dur)
    except Exception:
        return None

def scan_dataset():
    resolved_root = resolve_dataset_path(DATASET_DIR)
    if not resolved_root.exists():
        print(f"Dataset not found: {DATASET_DIR}")
        return []
    
    records = []
    for dirpath, dirnames, filenames in os.walk(resolved_root):
        pdir = Path(dirpath)
        for fn in filenames:
            if Path(fn).suffix.lower() in VIDEO_EXTS:
                vp = pdir / fn
                meta = find_sidecar_json(vp)
                dur = parse_duration(meta)
                
                # Get resolution from metadata
                w = h = None
                if isinstance(meta, dict):
                    w = meta.get('width') or meta.get('w')
                    h = meta.get('height') or meta.get('h')
                    if isinstance(w, str) and w.isdigit():
                        w = int(w)
                    if isinstance(h, str) and h.isdigit():
                        h = int(h)
                
                rec = {
                    'path': str(vp),
                    'has_metadata': meta is not None,
                    'width': w,
                    'height': h,
                    'duration_sec': dur,
                }
                records.append(rec)
    return records

def summarize(records):
    total = len(records)
    with_meta = sum(1 for r in records if r['has_metadata'])
    
    def is_suitable(r):
        dur_ok = (r['duration_sec'] or 0) >= 10
        h = max([x for x in [r['width'], r['height']] if isinstance(x, int)] + [0])
        res_ok = h >= 720 if h else False
        return dur_ok and res_ok
    
    suitable_count = sum(1 for r in records if is_suitable(r))
    
    return {
        'total': total,
        'with_metadata': with_meta,
        'suitable_count': suitable_count,
    }

def main():
    records = scan_dataset()
    summary = summarize(records)
    
    with open(REPORT_JSON, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Scanned {summary['total']} videos")
    print(f"With metadata: {summary['with_metadata']}")
    print(f"Suitable (>=10s, >=720p): {summary['suitable_count']}")
    print(f"Wrote: {REPORT_JSON}")

if __name__ == '__main__':
    main()
