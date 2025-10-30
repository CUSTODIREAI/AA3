#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$ROOT_DIR"

if [[ -f docker/VERSIONS.env ]]; then
  set -a
  source docker/VERSIONS.env
  set +a
fi

BASE_TAG=${IMAGE_TAG_BASE:-dfl-base:cuda11.8-tf2.12.1-py3.10}
DFL_TAG=${IMAGE_TAG_DFL:-dfl:tf2.12.1}

# 1) Sanity: nvidia-smi + TF GPU visibility in base image
echo "[Base] Checking GPU visibility..."
docker run --rm --gpus all "$BASE_TAG" bash -lc 'nvidia-smi; python -u - <<"PY"
import tensorflow as tf
print("TF:", tf.__version__)
print("GPUs:", tf.config.list_physical_devices("GPU"))
PY'

# 2) DFL image GPU check
echo "[DFL] Checking GPU visibility..."
docker run --rm --gpus all "$DFL_TAG" dfl-gpu-check

# 3) Quick DFL help to confirm entrypoint works
echo "[DFL] Printing DFL help..."
docker run --rm --gpus all "$DFL_TAG" --help || true

# 4) Optional: E2E smoke (requires mounted data)
# Example (uncomment and set real paths):
# docker run --rm -it --gpus all --ipc=host --shm-size=8g \
#   -v "$PWD/workspace:/workspace" \
#   "$DFL_TAG" extract --input-dir /workspace/data_src --output-dir /workspace/data_src/aligned --detector s3fd

echo "Validation complete."
