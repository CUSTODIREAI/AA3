# DeepFaceLab Docker Images (CUDA 11.8, RTX 4090)

This project produces two images:
- Base: CUDA 11.8 + cuDNN + Python 3.10 + TensorFlow GPU 2.13.1 and common ML deps
- DFL: Above plus DeepFaceLab code (no pretrained models)

Host requirements:
- NVIDIA GPU (Ada/RTX 4090 supported)
- NVIDIA driver >= 520.61.05 (recommend 535/545+)
- Docker Engine + Docker Compose v2
- nvidia-container-toolkit installed and configured

Build images:
- ./docker/build_dfl_images.sh
  - Args are set at top of script (image namespace, tags, DFL_REF)
  - Produces tarballs and SHA-256 in docker/images/

Validate on GPU:
- ./docker/test_dfl_rtx4090.sh
  - Checks: nvidia-smi, TensorFlow GPU visibility, ONNX Runtime GPU device, DFL CLI help

Run DeepFaceLab:
- Interactive shell: docker run --rm -it --gpus all -v $(pwd)/workspace:/workspace custudire/dfl:dfl-cuda11.8-tf2.13.1 bash
- DFL help: docker run --rm --gpus all -v $(pwd)/workspace:/workspace custudire/dfl:dfl-cuda11.8-tf2.13.1 help

Docker Compose:
- docker compose -f docker/dfl-compose.yaml up --build

Notes:
- Pretrained models are excluded from the image by design. Place models under workspace/ and bind-mount.
- If needed, enable NVENC in ffmpeg by ensuring host driver + container capabilities include video (already set); Ubuntu ffmpeg supports nvenc on many installs.
- To pin DeepFaceLab to a specific commit, set DFL_REF in build script or pass --build-arg DFL_REF=<commit> to the dfl image build.
- Environment flags set by default: TF_FORCE_GPU_ALLOW_GROWTH=true, TF_GPU_ALLOCATOR=cuda_malloc_async.
