#!/usr/bin/env bash
set -euo pipefail

# Configurable vars
IMAGE_NS="custodire/dfl"
BASE_TAG="base-cuda11.8-tf2.13.1"
DFL_TAG="dfl-cuda11.8-tf2.13.1"
DFL_REF="master"   # override with commit/tag as needed
OUT_DIR="$(dirname "$0")/images"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$OUT_DIR"

echo "Building base image: ${IMAGE_NS}:${BASE_TAG}"
docker build \
  -f "$SCRIPT_DIR/dfl-base.Dockerfile" \
  -t "${IMAGE_NS}:${BASE_TAG}" \
  "$SCRIPT_DIR"

echo "Building DFL image: ${IMAGE_NS}:${DFL_TAG} (DFL_REF=${DFL_REF})"
docker build \
  -f "$SCRIPT_DIR/dfl.Dockerfile" \
  --build-arg BASE_IMAGE="${IMAGE_NS}:${BASE_TAG}" \
  --build-arg DFL_REF="${DFL_REF}" \
  -t "${IMAGE_NS}:${DFL_TAG}" \
  "$SCRIPT_DIR"

# Export images to tarballs
DATE_TAG="$(date +%Y%m%d-%H%M%S)"
BASE_TAR="${OUT_DIR}/${IMAGE_NS//\//_}-${BASE_TAG}-${DATE_TAG}.tar"
DFL_TAR="${OUT_DIR}/${IMAGE_NS//\//_}-${DFL_TAG}-${DATE_TAG}.tar"

echo "Saving images to tarballs..."
docker save -o "$BASE_TAR" "${IMAGE_NS}:${BASE_TAG}"
docker save -o "$DFL_TAR" "${IMAGE_NS}:${DFL_TAG}"

echo "Computing SHA-256 checksums..."
( cd "$OUT_DIR" && sha256sum "$(basename "$BASE_TAR")" > "$(basename "$BASE_TAR").sha256" )
( cd "$OUT_DIR" && sha256sum "$(basename "$DFL_TAR")" > "$(basename "$DFL_TAR").sha256" )

echo "Done. Artifacts:"
echo "  $BASE_TAR"
echo "  $BASE_TAR.sha256"
echo "  $DFL_TAR"
echo "  $DFL_TAR.sha256"

# Optionally append to evidence ledger if present
LEDGER="$(dirname "$SCRIPT_DIR")/evidence/ledger.jsonl"
RECORDER="$(dirname "$SCRIPT_DIR")/evidence/record_image_metadata.sh"
if [ -x "$RECORDER" ]; then
  "$RECORDER" "${IMAGE_NS}:${BASE_TAG}" "$BASE_TAR" || true
  "$RECORDER" "${IMAGE_NS}:${DFL_TAG}" "$DFL_TAR" || true
fi
