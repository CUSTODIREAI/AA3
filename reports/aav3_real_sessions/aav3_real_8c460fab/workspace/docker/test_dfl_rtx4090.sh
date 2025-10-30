#!/usr/bin/env bash
set -euo pipefail

IMAGE="custodire/dfl:dfl-cuda11.8-tf2.13.1"
WORKDIR_HOST="$(cd "$(dirname "$0")"/.. && pwd)/workspace"
mkdir -p "$WORKDIR_HOST"

run() {
  echo ">>> $*"
  eval "$@"
}

echo "Running RTX 4090 validation tests against $IMAGE"

# Basic nvidia-smi check
run docker run --rm --gpus all "$IMAGE" nvidia-smi || { echo "nvidia-smi failed"; exit 1; }

# TensorFlow GPU presence
run docker run --rm --gpus all -e TF_CPP_MIN_LOG_LEVEL=1 "$IMAGE" \
  python - <<'PY'
import tensorflow as tf
from pprint import pprint
print('TF version:', tf.__version__)
gpus = tf.config.list_physical_devices('GPU')
print('GPUs:'); pprint(gpus)
assert gpus, 'No GPUs visible to TensorFlow'
PY

# ONNX Runtime device must be GPU (CUDA)
run docker run --rm --gpus all "$IMAGE" \
  python - <<'PY'
import onnxruntime as ort
print('onnxruntime:', ort.__version__)
print('device:', ort.get_device())
assert ort.get_device().lower().startswith('gpu'), 'ONNX Runtime not using GPU'
PY

# DFL CLI help should print
run docker run --rm --gpus all -v "$WORKDIR_HOST":/workspace "$IMAGE" help

echo "All smoke tests passed."
