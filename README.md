# Custodire AA System — PunkBox + Append-Only Ingest (Cross‑OS)

This pack enables agents to **build freely** inside a writable sandbox (**PunkBox**) and then **promote**
newly created media/code from `staging/` into the protected `dataset/` via a **gateway‑guarded, append‑only ingest**.

Key properties:
- **Tools‑only** execution (no raw shell in plans).
- **Cross‑OS** path adapter & Docker engine probe (WSL/PowerShell both work).
- **PunkBox** dev container: full freedom in `/workspace`, `/cache`, `/tmp` (create, install, delete allowed here).
- **Protected areas** mounted **read‑only** into containers: `/dataset`, `/evidence`, `/staging-final`.
- **Append‑only promotion**: `ingest.promote` copies from `staging/` → `dataset/` with SHA‑256, size, RFC‑3339 timestamps,
  and a manifest entry; never deletes/overwrites existing files.
- **No delete/prune** in protected areas. Optional soft‑delete (recycle bin) for mistakes in writable roots.

See `docs/DATASET_PROMOTION.md` for the exact ingestion protocol and `configs/policy.yaml` for rails.
