#!/usr/bin/env bash
set -euo pipefail

REGISTRY="custodire"
TAG_BASE="cuda11.8-tf2.13-py3.10"
IMAGE_BASE="${REGISTRY}/dfl-base:${TAG_BASE}"
IMAGE_DFL="${REGISTRY}/dfl:tf2.13-py3.10"

OUTDIR="staging/docker/images"
METADIR="staging/metadata"
mkdir -p "${OUTDIR}" "${METADIR}"

save_and_hash() {
  local image="$1"; local name="$2";
  local tar="${OUTDIR}/${name}.tar"
  echo "Saving ${image} -> ${tar}"
  docker image save -o "${tar}" "${image}"
  local sha
  sha=$(sha256sum "${tar}" | awk '{print $1}')
  local bytes
  bytes=$(stat -c%s "${tar}")
  echo "${sha}  ${tar}" > "${tar}.sha256"
  jq -n --arg name "${name}" --arg image "${image}" --arg sha "${sha}" --arg path "${tar}" --argjson bytes ${bytes} '{name:$name,image:$image,sha256:$sha,bytes:$bytes,path:$path}' \
    > "${METADIR}/${name}.image.json"
  # Prepare ingest item
  jq -nc --arg src "${tar}" --arg rel "docker/images/${name}.tar" \
    --arg t1 "docker" --arg t2 "image" --arg t3 "dfl" --arg t4 "${TAG_BASE}" \
    '{src:$src,relative_dst:$rel,tags:[$t1,$t2,$t3,$t4]}' >> "${METADIR}/ingest_items.jsonl"
}

save_and_hash "${IMAGE_BASE}" "dfl-base-${TAG_BASE}"
save_and_hash "${IMAGE_DFL}" "dfl-tf2.13-py3.10"

echo "Artifacts and metadata in staging/. For ingest, use ingest.promote on metadata/ingest_items.jsonl."
