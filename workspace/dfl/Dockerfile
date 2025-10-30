FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Install Python 3.10 and dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3-pip \
    git \
    wget \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.10 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

# Upgrade pip
RUN python -m pip install --upgrade pip

# Install TensorFlow GPU 2.15 (RTX 4090 compatible)
RUN pip install tensorflow==2.15.0

# Install ML dependencies
RUN pip install \
    numpy==1.23.5 \
    opencv-python==4.8.1.78 \
    scipy==1.11.3 \
    scikit-image==0.22.0 \
    tqdm \
    h5py

# Clone DeepFaceLab
RUN git clone https://github.com/iperov/DeepFaceLab.git /dfl

WORKDIR /dfl

# Test GPU access on build
RUN python -c "import tensorflow as tf; print('TensorFlow version:', tf.__version__); print('GPUs available:', len(tf.config.list_physical_devices('GPU')))"

CMD ["/bin/bash"]
