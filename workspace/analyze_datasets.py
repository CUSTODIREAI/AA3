#!/usr/bin/env python3
import os
import re
import json
import sys
import math
import datetime
from collections import defaultdict, Counter
from pathlib import Path

VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.mpg', '.mpeg', '.m4v'}

DATASET_DIRS_RAW = [
    r"X:\\dataset_3",
    r"X:\\dataset2",
    r"X:\\DEEPFAKE_DATASETS",
]

STAGING_DIR = Path("staging/dataset_analysis")
STAGING_DIR.mkdir(parents=True, exist_ok=True)

REPORT_JSON = STAGING_DIR / "report.json"
REAL_SOURCES_JSONL = STAGING_DIR / "real_sources.jsonl"
DIVERSITY_BALANCE_JSON = STAGING_DIR / "diversity_balance.json"
VERDICT_MD = STAGING_DIR / "verdict.md"

KEYWORDS = {
    'indoor': {"indoor", "office", "room", "studio", "kitchen", "livingroom", "conference"},
    'outdoor': {"outdoor", "street", "park", "beach", "field", "plaza", "square", "forest", "road"},
    'selfie': {"selfie", "frontcam", "front_cam", "handheld", "vlog"},
    'interview': {"interview", "podcast", "talkshow", "talk_show", "sitdown"},
    'talking_head': {"talkinghead", "talking_head", "news", "anchor"},
    'low': {"lowlight", "low_light", "dark", "night"},
    'bright': {"sunny", "bright", "overexposed"},
    'neutral': {"neutral", "normal", "daylight"},
    'hq': {"4k", "uhd", "2160p", "1440p", "1080p", "fullhd"},
    'mq': {"720p", "hd"},
    'lq': {"480p", "360p", "240p", "sd"},
    'fake': {"deepfake", "fake", "swap", "faceswap", "dfdc"},
    'real': {"real", "authentic", "genuine"},
}

RESO_RE = re.compile(r"(?P<w>\d{3,5})[xX](?P<h>\d{3,5})")
P_RE = re.compile(r"(?P<p>\d{3,4})p\b")


def resolve_dataset_path(p: str) -> Path:
    p_str = p
    # First try as-is
    as_is = Path(p_str)
    if as_is.exists():
        return as_is
    # Map Windows drive to /mnt/<drive-letter-lower>
    if len(p_str) >= 2 and p_str[1] == ':':
        drive = p_str[0].lower()
        rest = p_str[2:].replace('\\', '/')
        candidate = Path(f"/mnt/{drive}/{rest.lstrip('/')}")
        if candidate.exists():
            return candidate
    # Try lowercase/uppercase permutations of drive
    if p_str.startswith(('X:', 'x:')):
        candidate = Path("/mnt/x/") / p_str[2:].replace('\\', '/').lstrip('/')
        if candidate.exists():
            return candidate
    if p_str.startswith(('W:', 'w:')):
        candidate = Path("/mnt/w/") / p_str[2:].replace('\\', '/').lstrip('/')
        if candidate.exists():
            return candidate
    return as_is  # may not exist; handled later


def find_sidecar_json(video_path: Path):
    candidates = []
    base = video_path.with_suffix('')
    cand1 = base.with_suffix('.json')
    if cand1.exists():
        candidates.append(cand1)
    # Any metadata.json in same folder
    folder = video_path.parent
    meta1 = folder / 'metadata.json'
    if meta1.exists():
        candidates.append(meta1)
    # Any json with same stem ignoring case
    for j in folder.glob('*.json'):
        if j == cand1 or j == meta1:
            continue
        if j.stem.lower() == base.name.lower():
            candidates.append(j)
    # Return first loadable json dict that refers to this file or generic
    for j in candidates:
        try:
            with open(j, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # If it's a list, try to find entry referring to file
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        fp = str(item.get('file') or item.get('path') or '').lower()
                        if video_path.name.lower() in fp:
                            return item
                return None
            elif isinstance(data, dict):
                # If dict with 'file' referencing, ensure match or accept as generic sidecar
                fp = str(data.get('file') or data.get('path') or '')
                if not fp or video_path.name.lower() in fp.lower() or j == cand1:
                    return data
        except Exception:
            continue
    return None


def parse_resolution(meta, path_tokens):
    w = h = None
    if isinstance(meta, dict):
        w = meta.get('width') or meta.get('w')
        h = meta.get('height') or meta.get('h')
        if isinstance(w, str) and w.isdigit():
            w = int(w)
        if isinstance(h, str) and h.isdigit():
            h = int(h)
        res = meta.get('resolution') or meta.get('reso')
        if isinstance(res, str):
            m = RESO_RE.search(res)
            if m:
                w = w or int(m.group('w'))
                h = h or int(m.group('h'))
            else:
                m2 = P_RE.search(res)
                if m2 and not h and not w:
                    p = int(m2.group('p'))
                    h = p
    # Look into tokens for patterns like 1920x1080 or 1080p
    joined = ' '.join(path_tokens)
    m = RESO_RE.search(joined)
    if m:
        w = w or int(m.group('w'))
        h = h or int(m.group('h'))
    else:
        m2 = P_RE.search(joined)
        if m2 and not h and not w:
            p = int(m2.group('p'))
            h = p
    return (int(w) if w else None, int(h) if h else None)


def parse_duration(meta):
    if not isinstance(meta, dict):
        return None
    dur = meta.get('duration') or meta.get('sec') or meta.get('length')
    if dur is None:
        return None
    try:
        return float(dur)
    except Exception:
        try:
            # maybe HH:MM:SS
            parts = str(dur).split(':')
            parts = [float(x) for x in parts]
            if len(parts) == 3:
                return parts[0]*3600 + parts[1]*60 + parts[2]
            if len(parts) == 2:
                return parts[0]*60 + parts[1]
        except Exception:
            return None
    return None


def token_set(path: Path, meta):
    tokens = []
    for part in path.parts:
        if part:
            tokens.extend(re.split(r"[^A-Za-z0-9]+", part.lower()))
    if isinstance(meta, dict):
        for k, v in meta.items():
            if isinstance(v, str):
                tokens.extend(re.split(r"[^A-Za-z0-9]+", v.lower()))
    return set([t for t in tokens if t])


def infer_label(meta, toks):
    # From metadata
    if isinstance(meta, dict):
        for key in ['label', 'type', 'class', 'target']:
            v = meta.get(key)
            if isinstance(v, str):
                lv = v.lower()
                if 'fake' in lv or 'deepfake' in lv or 'synthetic' in lv:
                    return 'fake'
                if 'real' in lv or 'authentic' in lv or 'genuine' in lv:
                    return 'real'
        for key in ['is_fake', 'is_deepfake']:
            v = meta.get(key)
            if isinstance(v, bool):
                return 'fake' if v else 'real'
    # From tokens
    if (KEYWORDS['fake'] & toks) and not (KEYWORDS['real'] & toks):
        return 'fake'
    if (KEYWORDS['real'] & toks) and not (KEYWORDS['fake'] & toks):
        return 'real'
    return 'unknown'


def infer_environment(meta, toks):
    if isinstance(meta, dict):
        for key in ['environment', 'env', 'location']:
            v = meta.get(key)
            if isinstance(v, str):
                lv = v.lower()
                if 'indoor' in lv:
                    return 'indoor'
                if 'outdoor' in lv:
                    return 'outdoor'
    if KEYWORDS['indoor'] & toks:
        return 'indoor'
    if KEYWORDS['outdoor'] & toks:
        return 'outdoor'
    return 'unknown'


def infer_shot_type(meta, toks):
    if isinstance(meta, dict):
        for key in ['shot_type', 'shot', 'camera', 'category']:
            v = meta.get(key)
            if isinstance(v, str):
                lv = v.lower()
                for st, kws in [('selfie', KEYWORDS['selfie']), ('interview', KEYWORDS['interview']), ('talking_head', KEYWORDS['talking_head'])]:
                    if any(k in lv for k in kws):
                        return st
                if 'selfie' in lv:
                    return 'selfie'
                if 'interview' in lv:
                    return 'interview'
                if 'talking' in lv or 'anchor' in lv or 'news' in lv:
                    return 'talking_head'
    for st, kws in [('selfie', KEYWORDS['selfie']), ('interview', KEYWORDS['interview']), ('talking_head', KEYWORDS['talking_head'])]:
        if kws & toks:
            return st
    return 'other'


def infer_lighting(meta, toks):
    if isinstance(meta, dict):
        for key in ['lighting', 'light']:
            v = meta.get(key)
            if isinstance(v, str):
                lv = v.lower()
                if 'low' in lv or 'dark' in lv or 'night' in lv:
                    return 'low'
                if 'bright' in lv or 'sunny' in lv:
                    return 'bright'
                if 'neutral' in lv or 'normal' in lv or 'day' in lv:
                    return 'neutral'
    if KEYWORDS['low'] & toks:
        return 'low'
    if KEYWORDS['bright'] & toks:
        return 'bright'
    if KEYWORDS['neutral'] & toks:
        return 'neutral'
    return 'neutral'  # default assumption


def infer_quality(meta, toks, res):
    if isinstance(meta, dict):
        for key in ['quality', 'qual']:
            v = meta.get(key)
            if isinstance(v, str):
                lv = v.lower()
                if 'hq' in lv or 'high' in lv:
                    return 'hq'
                if 'lq' in lv or 'low' in lv:
                    return 'lq'
                if 'mq' in lv or 'medium' in lv:
                    return 'mq'
    if res and (res[0] and res[1]):
        h = max(res[0], res[1])  # assume larger is height for heuristic
        if h >= 1080:
            return 'hq'
        if h >= 720:
            return 'mq'
        return 'lq'
    if KEYWORDS['hq'] & toks:
        return 'hq'
    if KEYWORDS['mq'] & toks:
        return 'mq'
    if KEYWORDS['lq'] & toks:
        return 'lq'
    return 'mq'


def detect_dataset_name(path: Path, resolved_roots):
    for root in resolved_roots:
        try:
            rel = path.relative_to(root)
            return root.name
        except Exception:
            continue
    # fallback to second-level parent
    return path.parts[1] if len(path.parts) > 1 else path.parts[0]


def scan_datasets():
    resolved_roots = []
    for p in DATASET_DIRS_RAW:
        rp = resolve_dataset_path(p)
        if rp.exists():
            resolved_roots.append(rp)
    records = []
    for root in resolved_roots:
        for dirpath, dirnames, filenames in os.walk(root):
            pdir = Path(dirpath)
            for fn in filenames:
                if Path(fn).suffix.lower() in VIDEO_EXTS:
                    vp = pdir / fn
                    meta = find_sidecar_json(vp)
                    toks = token_set(vp, meta)
                    res = parse_resolution(meta, [vp.name] + list(vp.parts))
                    dur = parse_duration(meta)
                    label = infer_label(meta, toks)
                    env = infer_environment(meta, toks)
                    shot = infer_shot_type(meta, toks)
                    light = infer_lighting(meta, toks)
                    qual = infer_quality(meta, toks, res)
                    dataset_name = detect_dataset_name(vp, resolved_roots)
                    rec = {
                        'path': str(vp),
                        'dataset': dataset_name,
                        'label': label,
                        'environment': env,
                        'shot_type': shot,
                        'lighting': light,
                        'quality': qual,
                        'width': res[0] if res else None,
                        'height': res[1] if res else None,
                        'duration_sec': dur,
                    }
                    records.append(rec)
    return records


def summarize(records):
    total = len(records)
    by_label = Counter(r['label'] for r in records)
    by_dataset = defaultdict(lambda: {'total': 0, 'labels': Counter(), 'environment': Counter(), 'shot_type': Counter(), 'lighting': Counter(), 'quality': Counter()})
    for r in records:
        ds = r['dataset']
        by_dataset[ds]['total'] += 1
        by_dataset[ds]['labels'][r['label']] += 1
        by_dataset[ds]['environment'][r['environment']] += 1
        by_dataset[ds]['shot_type'][r['shot_type']] += 1
        by_dataset[ds]['lighting'][r['lighting']] += 1
        by_dataset[ds]['quality'][r['quality']] += 1
    axes = {}
    def axis_stats(key):
        cnt = Counter(r[key] for r in records)
        total_local = sum(cnt.values()) or 1
        dist = {k: v/total_local for k, v in cnt.items()}
        over = [k for k, p in dist.items() if p >= 0.60]
        under = [k for k, p in dist.items() if p <= 0.10]
        return {'counts': dict(cnt), 'distribution': dist, 'overrepresented': over, 'underrepresented': under}
    for key in ['environment', 'shot_type', 'lighting', 'quality']:
        axes[key] = axis_stats(key)
    # Composite categories for reals only (suitable considered later)
    real_recs = [r for r in records if r['label'] == 'real']
    comp_counts = Counter()
    for r in real_recs:
        comp = f"{r['environment']}:{r['shot_type']}:{r['lighting']}"
        comp_counts[comp] += 1
    # Suitability: >=10s and >=720p on either dimension
    def is_suitable(r):
        dur_ok = (r['duration_sec'] or 0) >= 10
        h = max([x for x in [r['width'], r['height']] if isinstance(x, int)] + [0])
        res_ok = h >= 720 if h else False
        return dur_ok and res_ok
    suitable_reals = [r for r in real_recs if is_suitable(r)]
    return {
        'total': total,
        'by_label': dict(by_label),
        'by_dataset': {ds: {'total': v['total'], 'labels': dict(v['labels']), 'environment': dict(v['environment']), 'shot_type': dict(v['shot_type']), 'lighting': dict(v['lighting']), 'quality': dict(v['quality'])} for ds, v in by_dataset.items()},
        'axes': axes,
        'composite_counts_real': dict(comp_counts),
        'suitable_real_count': len(suitable_reals),
    }


def compute_sampling(records, summary):
    # Target on suitable real videos; fallback to all reals then all
    real_recs = [r for r in records if r['label'] == 'real']
    def is_suitable(r):
        dur_ok = (r['duration_sec'] or 0) >= 10
        h = max([x for x in [r['width'], r['height']] if isinstance(x, int)] + [0])
        res_ok = h >= 720 if h else False
        return dur_ok and res_ok
    suitable_reals = [r for r in real_recs if is_suitable(r)]
    pool = suitable_reals if suitable_reals else real_recs if real_recs else []
    total_available = len(pool)
    if total_available == 0:
        return {
            'target_total_real': 0,
            'category_quota': {},
            'selected': [],
            'selected_counts': {},
            'notes': 'No real videos found in datasets.'
        }
    # Target: min(1000, max(200, 25% of available)), but cannot exceed available
    target = min(total_available, max(200, int(math.ceil(total_available * 0.25))), 1000)
    # Build composite categories
    comp_to_indices = defaultdict(list)
    for idx, r in enumerate(pool):
        comp = f"{r['environment']}:{r['shot_type']}:{r['lighting']}"
        comp_to_indices[comp].append(idx)
    categories = list(comp_to_indices.keys())
    k = len(categories)
    if k == 0:
        # All unknowns; treat as single category
        categories = ['unknown:other:neutral']
        comp_to_indices[categories[0]] = list(range(len(pool)))
        k = 1
    base_quota = max(1, target // k)
    quotas = {c: min(len(comp_to_indices[c]), base_quota) for c in categories}
    allocated = sum(quotas.values())
    # Distribute remainder favoring underrepresented axes per summary
    remainder = target - allocated
    # Rank categories by current availability ascending to favor scarce ones, but ensure we don't exceed availability
    avail_sorted = sorted(categories, key=lambda c: len(comp_to_indices[c]))
    i = 0
    while remainder > 0 and any(quotas[c] < len(comp_to_indices[c]) for c in categories):
        c = avail_sorted[i % len(avail_sorted)]
        if quotas[c] < len(comp_to_indices[c]):
            quotas[c] += 1
            remainder -= 1
        i += 1
        if i > 100000:  # safety
            break
    # Select concretely (deterministic: path sort within category)
    selected_indices = []
    for c in categories:
        idxs = comp_to_indices[c]
        idxs_sorted = sorted(idxs, key=lambda ix: pool[ix]['path'])
        selected_indices.extend(idxs_sorted[:quotas[c]])
    selected = [pool[ix] for ix in selected_indices]
    selected_counts = Counter()
    for r in selected:
        comp = f"{r['environment']}:{r['shot_type']}:{r['lighting']}"
        selected_counts[comp] += 1
    return {
        'target_total_real': target,
        'category_quota': quotas,
        'selected': selected,
        'selected_counts': dict(selected_counts),
        'notes': ''
    }


def write_outputs(records, summary, sampling):
    now_iso = datetime.datetime.utcnow().isoformat() + 'Z'
    report = {
        'generated_at': now_iso,
        'dataset_roots': DATASET_DIRS_RAW,
        'total_videos': summary['total'],
        'total_real': summary['by_label'].get('real', 0),
        'total_fake': summary['by_label'].get('fake', 0),
        'suitable_real_count': summary['suitable_real_count'],
        'by_dataset': summary['by_dataset'],
        'axes': summary['axes'],
        'composite_counts_real': summary['composite_counts_real'],
    }
    with open(REPORT_JSON, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    with open(REAL_SOURCES_JSONL, 'w', encoding='utf-8') as f:
        for r in sampling['selected']:
            rec = {
                'path': r['path'],
                'dataset': r['dataset'],
                'label': r['label'],
                'environment': r['environment'],
                'shot_type': r['shot_type'],
                'lighting': r['lighting'],
                'quality': r['quality'],
                'width': r['width'],
                'height': r['height'],
                'duration_sec': r['duration_sec'],
            }
            f.write(json.dumps(rec) + "\n")

    diversity = {
        'generated_at': now_iso,
        'target_total_real': sampling['target_total_real'],
        'quota_per_category': sampling['category_quota'],
        'selected_counts': sampling['selected_counts'],
        'axis_overrepresented': {ax: summary['axes'][ax]['overrepresented'] for ax in ['environment','shot_type','lighting','quality']},
        'axis_underrepresented': {ax: summary['axes'][ax]['underrepresented'] for ax in ['environment','shot_type','lighting','quality']},
    }
    with open(DIVERSITY_BALANCE_JSON, 'w', encoding='utf-8') as f:
        json.dump(diversity, f, indent=2)

    # Expected 10s clips from selected reals
    def clips_from_duration(d):
        if not d or d <= 0:
            return 1
        return max(1, int(d // 10))
    total_clips = sum(clips_from_duration(r.get('duration_sec')) for r in sampling['selected'])

    # Build verdict.md
    lines = []
    lines.append("# Dataset Analysis Verdict")
    lines.append("")
    lines.append("## Findings")
    lines.append(f"- Total videos across 3 datasets: {summary['total']}")
    lines.append(f"- Real videos suitable (≥10s, ≥720p): {summary['suitable_real_count']}")
    lines.append(f"- Fake videos: {summary['by_label'].get('fake', 0)}")
    lines.append("")
    lines.append("## Detected Biases")
    order = ['environment', 'shot_type', 'lighting', 'quality']
    for ax in order:
        counts = summary['axes'][ax]['counts']
        total_ax = sum(counts.values()) or 1
        parts = []
        for k, v in counts.items():
            parts.append(f"{k} {int(round(100*v/total_ax))}%")
        bias = []
        if summary['axes'][ax]['overrepresented']:
            bias.append(f"overrepresented: {', '.join(summary['axes'][ax]['overrepresented'])}")
        if summary['axes'][ax]['underrepresented']:
            bias.append(f"underrepresented: {', '.join(summary['axes'][ax]['underrepresented'])}")
        lines.append(f"1. {ax.capitalize()}: " + ", ".join(parts) + (f" (BIAS: {'; '.join(bias)})" if bias else ""))
    lines.append("")
    lines.append("## Recommended Sampling")
    lines.append(f"- Target: {sampling['target_total_real']} videos (balanced across axes)")
    lines.append("- Quotas:")
    for comp, q in sorted(sampling['category_quota'].items()):
        lines.append(f"  - {comp} → {q} videos")
    lines.append("")
    lines.append("## Expected Output")
    lines.append(f"- {len(sampling['selected'])} selected videos → ~{total_clips} 10-second clips")
    lines.append("- Feed to W:\\workspace_11_custodire_pipeline_v1.6")
    lines.append(f"- Generate 2 fakes per real clip → ~{total_clips * 2} fake clips")
    lines.append(f"- Final dataset: {total_clips} real + {total_clips * 2} fake = {total_clips * 3} clips for detector training")
    lines.append("")
    lines.append("## Pipeline Input Recommendation")
    lines.append(f"- Use real_sources.jsonl as manifest of real inputs")
    lines.append(f"- Selection criteria: composite quotas in diversity_balance.json")
    lines.append(f"- Diversity validation: compare axis distributions pre/post via report.json vs selected_counts")
    lines.append("")
    lines.append("## Fake Generation Strategy")
    lines.append("- Use multiple generators (e.g., faceswap, GAN-based, neural rendering) with proportions mirroring real composite quotas")
    lines.append("- Maintain per-category parity: for each real composite bin, synthesize fakes in same proportion")
    lines.append("- Vary identity pairs, compression levels (hq/mq/lq), and lighting to match real distributions")
    lines.append("")
    lines.append("## Identified Gaps")
    lines.append("- Missing diversity axes may include pose/extreme motion; consider sourcing more such clips if underrepresented")
    lines.append("- Remaining biases after sampling highlighted in axis_overrepresented; seek additional data for categories <10% where feasible")
    lines.append("")
    lines.append("## Verdict: FEASIBLE with sampling strategy applied")
    lines.append("Datasets contain sufficient diversity IF properly sampled; without sampling, training may skew towards dominant categories.")

    with open(VERDICT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines) + "\n")


def main():
    records = scan_datasets()
    summary = summarize(records)
    sampling = compute_sampling(records, summary)
    write_outputs(records, summary, sampling)
    print(f"Wrote: {REPORT_JSON}, {REAL_SOURCES_JSONL}, {DIVERSITY_BALANCE_JSON}, {VERDICT_MD}")

if __name__ == '__main__':
    main()
