DeepFaceLab CUDA/TensorFlow Images

Overview
- Base image: CUDA 11.8 + cuDNN 8.6 + Python 3.10 + TensorFlow 2.12.1 + pinned scientific stack.
- DFL image: Adds DeepFaceLab repo checkout, minimal extra deps, and CLI wrappers.
- Validated on Ada GPUs (RTX 4090) with `--gpus=all` and recommended envs.

Build
- Edit `docker/VERSIONS.env` if needed (pins, repo/commit, tags).
- Build and save images: `bash docker/build_dfl_images.sh`.
- Outputs: `docker/images/*.tar` and `.sha256` checksums.

Run
- Base GPU check: `docker run --rm --gpus all dfl-base:cuda11.8-tf2.12.1-py3.10 python -u /usr/local/bin/python-gpu-check.py` (or the default CMD).
- DFL GPU check: `docker run --rm --gpus all dfl:tf2.12.1 dfl-gpu-check`.
- Compose: `docker compose -f docker/dfl-compose.yaml --env-file docker/VERSIONS.env up`.

DeepFaceLab CLI
- Entrypoint wraps `/opt/DeepFaceLab/main.py`: `dfl --help`.
- Common actions:
  - Extract: `dfl extract --input-dir /workspace/data_src --output-dir /workspace/data_src/aligned --detector s3fd`.
  - Train: `dfl train --training-data-src-dir /workspace/data_src/aligned --training-data-dst-dir /workspace/data_dst/aligned --model-dir /workspace/model --model SAEHD --iterations 1000`.
  - Merge: `dfl merge --input-dir /workspace/data_dst --output-dir /workspace/merged --model-dir /workspace/model`.

GPU/Runtime Notes
- Host driver: NVIDIA ≥ 525 recommended (CUDA 11.8 requires ≥ 520.61.05).
- Recommended container flags: `--gpus all --ipc=host --shm-size=8g`.
- TF envs: `TF_FORCE_GPU_ALLOW_GROWTH=true`, `TF_GPU_ALLOCATOR=cuda_malloc_async`, `NVIDIA_TF32_OVERRIDE=0`.
- Cache mounts: persist detectors/models by mounting `~/.cache` equivalents (`XDG_CACHE_HOME`, `TORCH_HOME`).

OCI Labels and Provenance
- Labels include CUDA, cuDNN, Python, TensorFlow versions, source repo and build date.
- `docker/build_dfl_images.sh` saves image tars and writes SHA-256 sums for Custodire ingestion.

Caveats
- Upstream `iperov/DeepFaceLab` targets TF1.x; for Linux/TF2 use a TF2-compatible fork and pin a commit.
- S3FD detector uses PyTorch; enable with `INSTALL_TORCH=1` during `dfl` image build.
- Avoid mixing system OpenCV; use `opencv-python-headless` to prevent GL issues.
