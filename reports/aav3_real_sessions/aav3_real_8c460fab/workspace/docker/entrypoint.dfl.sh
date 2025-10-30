#!/usr/bin/env bash
set -euo pipefail

# Activate venv if available
if [ -d "/opt/venv" ]; then
  # shellcheck source=/dev/null
  source /opt/venv/bin/activate
fi

# NVIDIA / TF runtime preferences
export TF_CPP_MIN_LOG_LEVEL="1"
export TF_FORCE_GPU_ALLOW_GROWTH="true"
export TF_GPU_ALLOCATOR="cuda_malloc_async"
export NVIDIA_VISIBLE_DEVICES="${NVIDIA_VISIBLE_DEVICES:-all}"
export NVIDIA_DRIVER_CAPABILITIES="${NVIDIA_DRIVER_CAPABILITIES:-compute,utility,video}"

DFL_MAIN="/opt/dfl/DeepFaceLab/main.py"

if [ ! -f "$DFL_MAIN" ]; then
  echo "DeepFaceLab main not found at $DFL_MAIN" >&2
  exit 1
fi

if [ $# -eq 0 ] || [ "$1" = "help" ]; then
  exec python -u "$DFL_MAIN" help
else
  exec python -u "$DFL_MAIN" "$@"
fi
