#!/usr/bin/env bash
set -euo pipefail

export TF_FORCE_GPU_ALLOW_GROWTH=${TF_FORCE_GPU_ALLOW_GROWTH:-1}
export TF_ENABLE_ONEDNN_OPTS=${TF_ENABLE_ONEDNN_OPTS:-0}

# Ensure workspace dirs exist
mkdir -p /workspace/{data_src,data_dst,model,aligned,output,weights}

cat <<'BANNER'
================ DeepFaceLab Container =================
- DFL dir: $DFL_DIR
- Workspace: /workspace
- GPU growth: $TF_FORCE_GPU_ALLOW_GROWTH
- OneDNN opts: $TF_ENABLE_ONEDNN_OPTS
Commands:
  dfl-shell            -> interactive bash
  dfl-tf-gpu-check     -> python /opt/tests/test_tf_gpu.py
  dfl-help             -> try to show DFL help (fork-dependent)
=======================================================
BANNER

case "${1:-}" in
  dfl-shell)
    shift; exec bash "$@" ;;
  dfl-tf-gpu-check)
    shift; exec python /opt/tests/test_tf_gpu.py "$@" ;;
  dfl-help)
    shift; 
    if [ -f "$DFL_DIR/main.py" ]; then exec python "$DFL_DIR/main.py" help "$@"; else echo "No main.py in DFL dir ($DFL_DIR)."; exec bash; fi ;;
  *)
    exec "$@" ;;

esac
