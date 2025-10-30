# Task 02: Write Base Dockerfile

Write the base Dockerfile for RTX 4090 with CUDA 11.8.

## Exact Content

Copy this EXACTLY to `/workspace/docker/dfl-base.Dockerfile`:

```dockerfile
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Install Python 3.10
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3-pip \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.10 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

# Upgrade pip
RUN python -m pip install --upgrade pip

# Install TensorFlow GPU 2.11
RUN pip install tensorflow==2.11.0

# Install ML libraries
RUN pip install \
    numpy==1.23.5 \
    opencv-python==4.7.0.72 \
    scipy==1.10.1 \
    scikit-image==0.20.0

# Create workspace
RUN mkdir -p /workspace
WORKDIR /workspace

CMD ["/bin/bash"]
```

## Command

```bash
cat > /workspace/docker/dfl-base.Dockerfile << 'DOCKERFILE_EOF'
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Install Python 3.10
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3-pip \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.10 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

# Upgrade pip
RUN python -m pip install --upgrade pip

# Install TensorFlow GPU 2.11
RUN pip install tensorflow==2.11.0

# Install ML libraries
RUN pip install \
    numpy==1.23.5 \
    opencv-python==4.7.0.72 \
    scipy==1.10.1 \
    scikit-image==0.20.0

# Create workspace
RUN mkdir -p /workspace
WORKDIR /workspace

CMD ["/bin/bash"]
DOCKERFILE_EOF

cat /workspace/docker/dfl-base.Dockerfile
```

## Done Signal

```bash
echo "DONE: Base Dockerfile created"
```
