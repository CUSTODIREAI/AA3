# syntax=docker/dockerfile:1.6
ARG CUDA_IMAGE="nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04"
FROM ${CUDA_IMAGE}

SHELL ["/bin/bash", "-lc"]

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility,video

# Core OS deps + Python 3.10
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv python3-dev \
        build-essential git ffmpeg \
        libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
        wget ca-certificates \
    && ln -sf /usr/bin/python3 /usr/bin/python \
    && python -m pip install --upgrade pip setuptools wheel \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
ARG USERNAME=appuser
ARG UID=1000
ARG GID=1000
RUN groupadd -g ${GID} ${USERNAME} \
    && useradd -m -u ${UID} -g ${GID} -s /bin/bash ${USERNAME}

WORKDIR /workspace
RUN chown -R ${USERNAME}:${USERNAME} /workspace

# Pinned Python stack compatible with CUDA 11.8 + TF 2.13
# Kept inline to avoid COPY-related resolver errors
RUN set -eux; \
    cat > /tmp/requirements.txt << 'EOF'\n# Core numeric/IO\nnumpy==1.26.4\nscipy==1.11.4\npillow==10.3.0\npsutil==5.9.8\ntqdm==4.66.4\ncolorama==0.4.6\n\n# Image/vision\nopencv-python-headless==4.8.1.78\nscikit-image==0.21.0\n\n# TensorFlow GPU (Linux pip includes GPU support)\ntensorflow==2.13.1\n# Addons version compatible with TF 2.13.x\ntensorflow-addons==0.21.0\n\n# Optional accelerators commonly used with DFL pipelines\nonnxruntime-gpu==1.16.3\nfacexlib==0.3.0\ninsightface==0.7.3\nEOF\n    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt

USER ${USERNAME}
CMD ["python", "-V"]
