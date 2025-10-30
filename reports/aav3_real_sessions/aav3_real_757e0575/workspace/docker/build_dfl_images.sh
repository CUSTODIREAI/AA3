#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$ROOT_DIR"

# Load pins
if [[ -f docker/VERSIONS.env ]]; then
  set -a
  source docker/VERSIONS.env
  set +a
fi

BASE_TAG=${IMAGE_TAG_BASE:-dfl-base:cuda11.8-tf2.12.1-py3.10}
DFL_TAG=${IMAGE_TAG_DFL:-dfl:tf2.12.1}

# Build base image
DOCKER_BUILDKIT=1 docker build \
  -f docker/dfl-base.Dockerfile \
  --build-arg CUDA_BASE_IMAGE="${CUDA_BASE_IMAGE:-nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04}" \
  --build-arg PYTHON_MINOR="${PYTHON_MINOR:-3.10}" \
  --build-arg TENSORFLOW_VERSION="${TENSORFLOW_VERSION:-2.12.1}" \
  --build-arg CUDNN_MAJOR_MINOR="${CUDNN_MAJOR_MINOR:-8.6}" \
  -t "$BASE_TAG" .

# Build DFL image
DOCKER_BUILDKIT=1 docker build \
  -f docker/dfl.Dockerfile \
  --build-arg BASE_IMAGE="$BASE_TAG" \
  --build-arg DFL_REPO="${DFL_REPO:-https://github.com/iperov/DeepFaceLab.git}" \
  --build-arg DFL_COMMIT="${DFL_COMMIT:-}" \
  --build-arg INSTALL_TORCH="${INSTALL_TORCH:-0}" \
  -t "$DFL_TAG" .

# Save images and compute SHA-256
IMAGES_DIR=docker/images
mkdir -p "$IMAGES_DIR"

BASE_TAR="$IMAGES_DIR/$(echo "$BASE_TAG" | tr ':/' '__').tar"
DFL_TAR="$IMAGES_DIR/$(echo "$DFL_TAG" | tr ':/' '__').tar"

docker save -o "$BASE_TAR" "$BASE_TAG"
sha256sum "$BASE_TAR" | tee "$BASE_TAR.sha256"

docker save -o "$DFL_TAR" "$DFL_TAG"
sha256sum "$DFL_TAR" | tee "$DFL_TAR.sha256"

echo "Built and saved: $BASE_TAG -> $BASE_TAR"
echo "Built and saved: $DFL_TAG -> $DFL_TAR"
