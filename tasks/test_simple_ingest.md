# Task: Simple Test Ingest

## Goal
Test the multi-agent deliberation system with a minimal task: create 3 test files in staging and promote them to the dataset with proper tagging.

## Success Criteria
- Create 3 text files in `staging/test/` with different content
- Each file should have unique metadata (different tags)
- Promote all files to `dataset/` via `ingest.promote` (append-only)
- Files must be tagged with:
  - `test_id`: unique identifier
  - `content_type`: type of test data
  - `phase`: "deliberation_test"

## Constraints
- Tools-only (use gateway actions from configs/policy.yaml)
- No privileged Docker
- Dataset is append-only via `ingest.promote`
- Files must land in `staging/test/` first, then promote
- Total size: <1KB per file (keep it tiny)

## Expected Output
After execution:
- `staging/test/test_001.txt` → `dataset/YYYY/MM/DD/test/test_001.txt`
- `staging/test/test_002.txt` → `dataset/YYYY/MM/DD/test/test_002.txt`
- `staging/test/test_003.txt` → `dataset/YYYY/MM/DD/test/test_003.txt`
- Manifest entries in `dataset/.manifests/dataset_manifest.jsonl`
- Ledger shows successful execution
