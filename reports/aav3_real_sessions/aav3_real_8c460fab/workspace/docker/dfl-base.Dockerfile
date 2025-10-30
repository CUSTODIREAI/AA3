FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

ARG DEBIAN_FRONTEND=noninteractive

LABEL org.opencontainers.image.title="DeepFaceLab Base (CUDA 11.8, TF 2.13.1)" \
      org.opencontainers.image.description="Base runtime with CUDA 11.8 + cuDNN, Python 3.10, TensorFlow 2.13.1 GPU, and common ML deps for DeepFaceLab on RTX 4090" \
      org.opencontainers.image.vendor="Custodire" \
      org.opencontainers.image.licenses="GPL-3.0 AND Apache-2.0 AND BSD-3-Clause AND MIT" \
      org.opencontainers.image.source="https://github.com/iperov/DeepFaceLab"

# System dependencies and NVIDIA compatibility package
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    python3-pip \
    git \
    ffmpeg \
    wget \
    ca-certificates \
    pkg-config \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    cuda-compat-11-8 \
    && rm -rf /var/lib/apt/lists/*

# Create and prepare venv
ENV VENV_PATH=/opt/venv
RUN python3 -m venv "$VENV_PATH" \
    && "$VENV_PATH/bin/pip" install --upgrade pip setuptools wheel

# Python dependencies pinned for CUDA 11.8 / TF 2.13.1
# Numpy pin avoids ABI issues and matches TF 2.13 constraints.
ENV PIP_NO_CACHE_DIR=1
RUN "$VENV_PATH/bin/pip" install \
    numpy==1.24.3 \
    tensorflow==2.13.1 \
    tensorflow-addons==0.23.0 \
    onnxruntime-gpu==1.16.3 \
    onnx==1.14.1 \
    opencv-python-headless==4.8.1.78 \
    scikit-image==0.21.0 \
    scikit-learn==1.3.2 \
    numexpr==2.8.7 \
    h5py==3.8.0 \
    matplotlib==3.7.3 \
    pandas==2.0.3 \
    tqdm==4.66.1 \
    psutil==5.9.5 \
    albumentations==1.3.1 \
    insightface>=0.7.3,<0.8 \
    facexlib==0.3.0

# Non-root user and workspace
RUN groupadd -g 1000 dfl && useradd -m -u 1000 -g 1000 -s /bin/bash dfl \
    && mkdir -p /workspace \
    && chown -R dfl:dfl /workspace

# Environment configuration for TF on Ada (4090)
ENV PATH="$VENV_PATH/bin:$PATH" \
    TF_CPP_MIN_LOG_LEVEL=1 \
    TF_FORCE_GPU_ALLOW_GROWTH=true \
    TF_GPU_ALLOCATOR=cuda_malloc_async \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility,video

WORKDIR /workspace
USER dfl

# Print GPU availability at container start if run interactively
CMD ["python", "-c", "import tensorflow as tf; print('GPUs:', tf.config.list_physical_devices('GPU'))"]
