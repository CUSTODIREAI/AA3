# syntax=docker/dockerfile:1.4

ARG CUDA_BASE_IMAGE=nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04
FROM ${BASE_IMAGE:-dfl-base:cuda11.8-tf2.12.1-py3.10} AS dfl

ARG DEBIAN_FRONTEND=noninteractive
ARG DFL_REPO=https://github.com/iperov/DeepFaceLab.git
ARG DFL_COMMIT=
ARG INSTALL_TORCH=0

USER root
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

USER dfl
WORKDIR /opt

# Clone DeepFaceLab (pin to commit if provided)
RUN git clone --depth 1 ${DFL_REPO} DeepFaceLab && \
    if [ -n "$DFL_COMMIT" ]; then cd DeepFaceLab && git fetch --depth 1 origin $DFL_COMMIT && git checkout $DFL_COMMIT; fi

# Optional: install PyTorch for S3FD detector support (cu118 wheels)
SHELL ["/bin/bash", "-lc"]
RUN if [[ "${INSTALL_TORCH}" == "1" ]]; then \
      pip install --extra-index-url https://download.pytorch.org/whl/cu118 \
        torch==2.0.1+cu118 torchvision==0.15.2+cu118; \
    fi

# Install additional DFL-level requirements (kept minimal to avoid conflicts)
COPY docker/requirements-dfl.txt /tmp/requirements-dfl.txt
COPY docker/constraints.txt /tmp/constraints.txt
RUN pip install -c /tmp/constraints.txt -r /tmp/requirements-dfl.txt

# Provide simple CLI wrappers
COPY docker/bin/dfl /usr/local/bin/dfl
COPY docker/bin/dfl-gpu-check /usr/local/bin/dfl-gpu-check
COPY docker/bin/python-gpu-check.py /usr/local/bin/python-gpu-check.py
RUN chmod +x /usr/local/bin/dfl /usr/local/bin/dfl-gpu-check

# Prepare workspace
RUN mkdir -p /workspace && chown -R dfl:dfl /workspace
WORKDIR /workspace

# Runtime envs
ENV TF_FORCE_GPU_ALLOW_GROWTH=true \
    TF_GPU_ALLOCATOR=cuda_malloc_async \
    NVIDIA_TF32_OVERRIDE=0 \
    PYTHONUNBUFFERED=1 \
    XDG_CACHE_HOME=/workspace/.cache \
    TORCH_HOME=/workspace/.cache/torch

# OCI labels
LABEL org.opencontainers.image.title="DeepFaceLab (CUDA 11.8 + TF 2.12.1)" \
      org.opencontainers.image.description="DFL runtime layered over TF/CUDA base. Repo=${DFL_REPO} Commit=${DFL_COMMIT}" \
      org.opencontainers.image.vendor="Custodire" \
      org.opencontainers.image.version="dfl-tf2.12.1" \
      org.opencontainers.image.source="${DFL_REPO}" \
      org.opencontainers.image.created="$(date -u +%Y-%m-%d)"

ENTRYPOINT ["/usr/local/bin/dfl"]
CMD ["--help"]
