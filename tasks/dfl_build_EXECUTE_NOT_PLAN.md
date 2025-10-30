# Build DFL Docker Image - EXECUTE, DON'T JUST PLAN

## CRITICAL: This is EXECUTION mode, not planning mode

**DO NOT** write plans, READMEs, or documentation.
**DO** actually build working Docker images.

## Task

Build ONE working Docker image for DeepFaceLab on RTX 4090.

### Steps (EXECUTE THESE)

1. Create `/workspace/dfl/Dockerfile`:
```dockerfile
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04
RUN apt-get update && apt-get install -y python3.10 python3-pip git
RUN pip3 install tensorflow==2.15.0
RUN git clone https://github.com/iperov/DeepFaceLab.git /dfl
WORKDIR /dfl
CMD ["python3", "main.py"]
```

2. Build the image:
```bash
cd /workspace/dfl && docker build -t dfl:rtx4090 .
```

3. Test GPU access:
```bash
docker run --rm --gpus all dfl:rtx4090 python3 -c "import tensorflow as tf; print('GPUs:', tf.config.list_physical_devices('GPU'))"
```

4. Save build log to `/workspace/dfl_build.log`

## Success Criteria

- Image built successfully
- GPU test shows at least 1 GPU
- Build log saved

## IMPORTANT

**Writing a plan is FAILURE.**
**Building an image is SUCCESS.**

Only signal DONE when Docker image exists and passes GPU test.
