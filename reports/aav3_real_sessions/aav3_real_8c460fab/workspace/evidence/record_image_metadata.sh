#!/usr/bin/env bash
set -euo pipefail

# Usage: record_image_metadata.sh <image:tag> <path/to/image.tar>
IMAGE_TAG="${1:-}"
TAR_PATH="${2:-}"
LEDGER_FILE="$(cd "$(dirname "$0")" && pwd)/ledger.jsonl"

if [ -z "$IMAGE_TAG" ] || [ -z "$TAR_PATH" ]; then
  echo "Usage: $0 <image:tag> <path/to/image.tar>" >&2
  exit 2
fi

if [ ! -f "$TAR_PATH" ]; then
  echo "Artifact not found: $TAR_PATH" >&2
  exit 3
fi

SHA256=$(sha256sum "$TAR_PATH" | awk '{print $1}')
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Try to read labels from local image if present
TITLE=$(docker image inspect "$IMAGE_TAG" -f '{{ index .Config.Labels "org.opencontainers.image.title"}}' 2>/dev/null || true)
VENDOR=$(docker image inspect "$IMAGE_TAG" -f '{{ index .Config.Labels "org.opencontainers.image.vendor"}}' 2>/dev/null || true)

jq -nc \
  --arg ts "$TS" \
  --arg image "$IMAGE_TAG" \
  --arg art "$TAR_PATH" \
  --arg sha "$SHA256" \
  --arg title "$TITLE" \
  --arg vendor "$VENDOR" \
  '{timestamp:$ts, image:$image, artifact_path:$art, sha256:$sha, labels:{"oc.title":$title, "oc.vendor":$vendor}}' \
  >> "$LEDGER_FILE"

echo "Recorded to $LEDGER_FILE"
