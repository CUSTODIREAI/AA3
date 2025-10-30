#!/usr/bin/env bash
set -euo pipefail

# Builds the CUDA+TF base image
REGISTRY="custodire"
TAG_BASE="cuda11.8-tf2.13-py3.10"
IMAGE_BASE="${REGISTRY}/dfl-base:${TAG_BASE}"
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
VCS_REF=${VCS_REF:-$(git rev-parse --short HEAD 2>/dev/null || echo "nogit")}

DOCKER_BUILDKIT=1 docker buildx build \
  --pull \
  --build-arg BASE_IMAGE=nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04 \
  --build-arg BUILD_DATE="${BUILD_DATE}" \
  --build-arg VCS_REF="${VCS_REF}" \
  -f docker/Dockerfile.base \
  -t "${IMAGE_BASE}" \
  .

echo "Built ${IMAGE_BASE}"
