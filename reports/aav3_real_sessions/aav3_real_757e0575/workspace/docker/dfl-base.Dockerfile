# syntax=docker/dockerfile:1.4

# Builder stage: prefetch wheels for deterministic install and layer caching
FROM ${CUDA_BASE_IMAGE:-nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04} AS wheels

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip python3-venv python3-dev \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and constraints
WORKDIR /tmp
COPY docker/requirements-base.txt /tmp/requirements-base.txt
COPY docker/constraints.txt /tmp/constraints.txt

RUN python3 -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    pip install --upgrade pip setuptools wheel && \
    pip download --dest /opt/wheels -c /tmp/constraints.txt -r /tmp/requirements-base.txt

# Runtime stage: minimal CUDA + cuDNN + Python + pinned scientific stack
FROM ${CUDA_BASE_IMAGE:-nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04} AS runtime

ARG DEBIAN_FRONTEND=noninteractive
ARG PYTHON_MINOR=3.10
ARG TENSORFLOW_VERSION=2.12.1
ARG CUDNN_MAJOR_MINOR=8.6

# System deps for building wheels and media processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip python3-venv python3-dev \
    build-essential git \
    ffmpeg \
    libsm6 libxext6 libxrender1 libglib2.0-0 \
    libgl1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python venv and install from pre-fetched wheels
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY --from=wheels /opt/wheels /opt/wheels
COPY docker/requirements-base.txt /tmp/requirements-base.txt
COPY docker/constraints.txt /tmp/constraints.txt

RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-index --find-links=/opt/wheels -c /tmp/constraints.txt -r /tmp/requirements-base.txt

# Non-root user and workspace
RUN groupadd -g 1000 dfl && \
    useradd -m -u 1000 -g 1000 -s /bin/bash dfl && \
    mkdir -p /workspace && chown -R dfl:dfl /workspace

USER dfl
WORKDIR /workspace

# Sensible TF runtime defaults for stability
ENV TF_FORCE_GPU_ALLOW_GROWTH=true \
    TF_GPU_ALLOCATOR=cuda_malloc_async \
    NVIDIA_TF32_OVERRIDE=0 \
    XLA_FLAGS="" \
    PYTHONUNBUFFERED=1

# OCI metadata labels
LABEL org.opencontainers.image.title="DeepFaceLab Base (CUDA 11.8 + TF ${TENSORFLOW_VERSION})" \
      org.opencontainers.image.description="Minimal CUDA 11.8 + cuDNN ${CUDNN_MAJOR_MINOR} + Python ${PYTHON_MINOR} + TensorFlow ${TENSORFLOW_VERSION} base for DFL" \
      org.opencontainers.image.vendor="Custodire" \
      org.opencontainers.image.version="tf-${TENSORFLOW_VERSION}" \
      org.opencontainers.image.licenses="Proprietary/Upstream OSS" \
      org.opencontainers.image.base.name="${CUDA_BASE_IMAGE:-nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04}" \
      org.opencontainers.image.created="$(date -u +%Y-%m-%d)"

CMD ["python", "-c", "import tensorflow as tf; print('TF', tf.__version__); print('GPU:', tf.config.list_physical_devices('GPU'))"]
