# Step 1: Create DFL Base Dockerfile

Create a Dockerfile for the DeepFaceLab base image targeting RTX 4090 GPUs.

## Task

1. Create directory `docker/` in /workspace if it doesn't exist
2. Create `docker/dfl-base.Dockerfile` with:
   - Base: `nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04`
   - Install Python 3.10
   - Install TensorFlow 2.11+ with GPU support
   - Install common ML libraries (numpy, opencv-python, etc.)
3. Save the file to /workspace/docker/dfl-base.Dockerfile

## Requirements

- RTX 4090 requires CUDA 11.8+ (Ada Lovelace architecture)
- Python 3.10 is best for DeepFaceLab
- TensorFlow 2.11+ for CUDA 11.8 compatibility

## Output

Single Dockerfile ready for building the base image.

When done, copy the file to /staging/ for dataset promotion.
