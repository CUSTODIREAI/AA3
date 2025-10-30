#!/usr/bin/env bash
set -euo pipefail

# Builds the DFL image from the base
REGISTRY="custodire"
TAG_BASE="cuda11.8-tf2.13-py3.10"
IMAGE_BASE="${REGISTRY}/dfl-base:${TAG_BASE}"
IMAGE_DFL="${REGISTRY}/dfl:tf2.13-py3.10"

# Override to a TF2-capable fork/commit known-good for Ada
DFL_REPO=${DFL_REPO:-"https://github.com/iperov/DeepFaceLab.git"}
DFL_COMMIT=${DFL_COMMIT:-"b7f8249a8b2c0a1f23b8f7bc3e3e8c6f0c28d6b1"}

BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
VCS_REF=${VCS_REF:-$(git rev-parse --short HEAD 2>/dev/null || echo "nogit")}

DOCKER_BUILDKIT=1 docker buildx build \
  --build-arg REGISTRY="${REGISTRY}" \
  --build-arg BASE_IMAGE_TAG="${TAG_BASE}" \
  --build-arg DFL_REPO="${DFL_REPO}" \
  --build-arg DFL_COMMIT="${DFL_COMMIT}" \
  --build-arg BUILD_DATE="${BUILD_DATE}" \
  --build-arg VCS_REF="${VCS_REF}" \
  -f docker/Dockerfile.dfl \
  -t "${IMAGE_DFL}" \
  .

echo "Built ${IMAGE_DFL} (DFL_REPO=${DFL_REPO} commit=${DFL_COMMIT})"
