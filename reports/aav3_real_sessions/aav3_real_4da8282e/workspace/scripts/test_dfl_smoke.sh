#!/usr/bin/env bash
set -euo pipefail

# Non-invasive smoke test: verify DFL repo presence and Python import in container
IMAGE=${1:-"custodire/dfl:tf2.13-py3.10"}

docker run --rm --gpus all -e NVIDIA_VISIBLE_DEVICES=all -e TF_FORCE_GPU_ALLOW_GROWTH=1 \
  -v "$(pwd)/workspace:/workspace" \
  "${IMAGE}" bash -lc '
  set -e
  echo "DFL dir:" $DFL_DIR
  test -d "$DFL_DIR" || (echo "DFL dir missing" && exit 1)
  python - <<PY
import os, sys, json
print(json.dumps({"pwd": os.getcwd(), "dfl_dir": os.getenv("DFL_DIR")}))
PY
  '
