# DeepFaceLab Docker Build - RTX 4090 Compatible

Build working DeepFaceLab Docker image for RTX 4090 with CUDA 11.8 and TensorFlow 2.15.

EXECUTE:
mkdir -p /workspace/dfl
cat > /workspace/dfl/Dockerfile <<'EOF'
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
EOF
docker build -t dfl:rtx4090 -f /workspace/dfl/Dockerfile /workspace 2>&1 | tee /workspace/dfl/build.log
docker run --gpus all dfl:rtx4090 python -c "import tensorflow as tf; print('TensorFlow:', tf.__version__); gpus = tf.config.list_physical_devices('GPU'); print('GPUs detected:', len(gpus)); [print(f'  - {gpu.name}') for gpu in gpus]" 2>&1 | tee /workspace/dfl/gpu_test.log
docker run --gpus all dfl:rtx4090 nvidia-smi 2>&1 | tee /workspace/dfl/nvidia_smi.log

SUCCESS_CRITERIA:
File exists: /workspace/dfl/Dockerfile
File exists: /workspace/dfl/build.log
File exists: /workspace/dfl/gpu_test.log
command: docker images | grep "dfl.*rtx4090"
grep: Successfully built in /workspace/dfl/build.log
grep: TensorFlow: 2.15 in /workspace/dfl/gpu_test.log
grep: CUDA Version in /workspace/dfl/nvidia_smi.log
