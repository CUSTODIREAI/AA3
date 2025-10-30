Fix quality issues in action execution.

FAILING ACTION:
{
  "id": "A2",
  "type": "exec.container_cmd",
  "params": {
    "image": "custodire/dev:latest",
    "cmd": [
      "python",
      "staging/small_test/scan_dataset.py"
    ],
    "mounts": [
      {
        "host": "staging",
        "container": "/workspace/staging"
      },
      {
        "host": "X:\\dataset2",
        "container": "/dataset2",
        "mode": "ro"
      }
    ]
  }
}

QUALITY ISSUES DETECTED:
- Unusually short output from script execution

OBSERVATION:
{
  "action_type": "exec.container_cmd",
  "result_ok": true,
  "stdout_preview": "",
  "stderr_preview": "",
  "script_code": "#!/usr/bin/env python3\nimport os\nimport re\nimport json\nimport sys\nfrom collections import defaultdict, Counter\nfrom pathlib import Path\n\nVIDEO_EXTS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.mpg', '.mpeg', '.m4v'}\n\nDATASET_DIR = r\"X:\\dataset2\\INTELLIGENT_ENTERPRISE_INSTITUTE\"\n\nSTAGING_DIR = Path(\"staging/small_test\")\nSTAGING_DIR.mkdir(parents=True, exist_ok=True)\n\nREPORT_JSON = STAGING_DIR / \"report.json\"\n\ndef resolve_dataset_path(p: str) -> Path:\n    p_str = p\n    as_is = Path(p_str)\n    if as_is.exists():\n        return as_is\n    if len(p_str) >= 2 and p_str[1] == ':':\n        drive = p_str[0].lower()\n        rest = p_str[2:].replace('\\\\', '/')\n        candidate = Path(f\"/mnt/{drive}/{rest.lstrip('/')}\")\n        if candidate.exists():\n            return candidate\n    return as_is\n\ndef find_sidecar_json(video_path: Path):\n    candidates = []\n    base = video_path.with_suffix('')\n    cand1 = base.with_suffix('.json')\n    if cand1.exists():\n        candidates.append(cand1)\n    folder = video_path.parent\n    for j in folder.glob('*.json'):\n        if j == cand1:\n            continue\n        if j.stem.lower() == base.name.lower():\n            candidates.append(j)\n    for j in candidates:\n        try:\n            with open(j, 'r', encoding='utf-8') as f:\n                data = json.load(f)\n            if isinstance(data, dict):\n                return data\n        except Exception:\n            continue\n    return None\n\ndef parse_duration(meta):\n    if not isinstance(meta, dict):\n        return None\n    dur = meta.get('duration') or meta.get('sec') or meta.get('length')\n    if dur is None:\n        return None\n    try:\n        return float(dur)\n    except Exception:\n        return None\n\ndef scan_dataset():\n    resolved_root = resolve_dataset_path(DATASET_DIR)\n    if not resolved_root.exists():\n        print(f\"Dataset not found: {DATASET_DIR}\")\n        return []\n    \n    records = []\n    for dirpath, dirnames, filenames in os.walk(resolved_root):\n        pdir = Path(dirpath)\n        for fn in filenames:\n            if Path(fn).suffix.lower() in VIDEO_EXTS:\n                vp = pdir / fn\n                meta = find_sidecar_json(vp)\n                dur = parse_duration(meta)\n                \n                # Get resolution from metadata\n                w = h = None\n                if isinstance(meta, dict):\n                    w = meta.get('width') or meta.get('w')\n                    h = meta.get('height') or meta.get('h')\n                    if isinstance(w, str) and w.isdigit():\n                        w = int(w)\n                    if isinstance(h, str) and h.isdigit():\n                        h = int(h)\n                \n                rec = {\n                    'path': str(vp),\n                    'has_metadata': meta is not None,\n                    'width': w,\n                    'height': h,\n                    'duration_sec': dur,\n                }\n                records.append(rec)\n    return records\n\ndef summarize(records):\n    total = le"
}

TASK:
Create a plan to fix the issues. The fix may involve:
- Correcting file paths or patterns (e.g., .info.json vs .json)
- Modifying scripts that process data
- Adjusting action parameters

Use fs.replace to modify scripts in workspace/ or staging/.
End with the corrected version of the failing action to retry.
