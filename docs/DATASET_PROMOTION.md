# Append‑Only Dataset Promotion

## Why
We want agents to **create** and **download** freely, but we keep the canonical dataset **immutable** except for **append**.
This prevents accidents, model skew via silent edits, and preserves legal/audit posture.

## Flow
1. Agent creates/downloads items into **`staging/`** (or builds with PunkBox under `/workspace` then writes to `staging/`).
2. Agent calls **`ingest.promote`** with a list of candidate files and metadata.
3. Gateway validates and performs **copy** (not move) from `staging/` → `dataset/YYYY/MM/DD/…`:
   - Computes **SHA‑256** and **size**.
   - Verifies **ext allowlist** (e.g., .mp4, .wav, .json, .png).
   - Refuses if destination exists (no overwrite).
   - Writes an append‑only manifest entry `dataset/.manifests/dataset_manifest.jsonl`:
     ```json
     {"ts":"2025-10-28T18:30:00Z","src":"staging/abc.mp4","dst":"dataset/2025/10/28/abc.mp4",
      "sha256":"…","bytes":1234,"actor":"executor","plan_id":"…"}
     ```
4. Optional **post‑promote**: move the staged originals to `staging-archive/` or leave in place.

## Guarantees
- **No deletes** in `dataset/`. No overwrites. All changes are new files + manifest lines.
- Every dataset file is **content‑addressable** via its SHA‑256 recorded in the manifest.
- Easy to WORM: sync `dataset/` + `dataset/.manifests/` to S3 Object Lock or other immutable storage.

## Promotion API (plan action)
```
{
  "id":"P1",
  "type":"ingest.promote",
  "items":[
    {"src":"staging/new/clip_0001.mp4","relative_dst":"session42/clip_0001.mp4","tags":{"lang":"fr","archetype":"UGC_9x16_1080"}}
  ]
}
```
- Gateway expands to `dataset/YYYY/MM/DD/<relative_dst>` and writes manifest.
- If `relative_dst` omitted, the gateway uses `basename(src)`.
