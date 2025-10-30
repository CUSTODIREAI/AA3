# Custodire DeepFaceLab Docker (CUDA 11.8 / TF 2.13 / Py3.10)

Overview
- Two-image design: base (CUDA+TF) and DFL layer.
- Pinned versions: CUDA 11.8, cuDNN 8, TF 2.13.1, Python 3.10.
- Non-root user, workspace at /workspace, GPU memory growth enabled.

Build
1) Base image:
   ./scripts/build_base.sh
2) DFL image (override to TF2-capable fork recommended):
   DFL_REPO=https://github.com/<fork>/DeepFaceLab.git \
   DFL_COMMIT=<commit_sha> \
   ./scripts/build_dfl.sh

Test GPU
- Base: ./scripts/test_gpu.sh
- DFL smoke: ./scripts/test_dfl_smoke.sh

Run
- docker compose up -d
- docker compose exec dfl dfl-tf-gpu-check
- docker compose exec dfl dfl-shell

Notes
- Upstream iperov/DeepFaceLab targets TF1.x; for RTX 4090 + TF2, use a maintained fork compatible with TF 2.13/CUDA 11.8.
- Mixed precision is not enabled by default. Enable only if the fork documents correct loss-scaling.
- ffmpeg is installed from Ubuntu repos; NVENC availability depends on host driver/runtime and distro build flags.

Custodire Ingest
- Export images and metadata:
  ./scripts/export_images.sh
- This writes image tars and JSON into staging/; use ingest.promote on metadata/ingest_items.jsonl.
