#!/usr/bin/env bash
set -euo pipefail

IMAGE=${1:-"custodire/dfl-base:cuda11.8-tf2.13-py3.10"}

echo "Running nvidia-smi inside ${IMAGE}..."
docker run --rm --gpus all --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all -e TF_FORCE_GPU_ALLOW_GROWTH=1 \
  "${IMAGE}" bash -lc 'nvidia-smi || true; python /opt/tests/test_tf_gpu.py'
