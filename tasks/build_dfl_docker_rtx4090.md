# Build RTX 4090 Compatible DeepFaceLab Docker Images

## Objective

Build production-ready Docker images for DeepFaceLab (DFL) that are compatible with RTX 4090 GPUs. These images will be used to generate synthetic deepfakes for hardening the Custodire deepfake detector against DFL-based attacks.

## IMPORTANT: Use Web Search for Latest Information

**ALWAYS use web search to get the latest versions and compatibility information:**
- Latest DeepFaceLab release version and repository URL
- Latest CUDA version compatible with RTX 4090 (Ada Lovelace architecture)
- Latest cuDNN version for the chosen CUDA version
- Latest TensorFlow GPU version compatible with CUDA/cuDNN
- Latest Python version recommended for DFL
- Any recent breaking changes or compatibility issues

Search queries to use:
- "DeepFaceLab latest release 2024"
- "RTX 4090 CUDA version compatibility 2024"
- "TensorFlow GPU CUDA 11.8 compatibility"
- "DeepFaceLab RTX 4090 Docker setup"

## Requirements

### GPU Compatibility
- **GPU**: NVIDIA RTX 4090
- **CUDA**: 11.8+ (RTX 4090 requires Ada Lovelace architecture support)
- **cuDNN**: Compatible version for CUDA 11.8+
- **Driver**: NVIDIA drivers 520+ (for RTX 4090 support)

### DeepFaceLab Requirements
- **Repository**: https://github.com/iperov/DeepFaceLab
- **Python**: 3.10 (DFL works best with 3.9-3.10)
- **TensorFlow**: 2.11+ with GPU support
- **Dependencies**: All DFL requirements including ffmpeg, opencv, etc.

### Docker Image Architecture
Build TWO images:

1. **Base Image** (`custodire/dfl-base:rtx4090`)
   - NVIDIA CUDA 11.8 base
   - cuDNN, Python 3.10, system dependencies
   - TensorFlow GPU 2.11+
   - Common ML libraries (numpy, opencv, etc.)
   - No DFL code (reusable base)

2. **DFL Image** (`custodire/dfl:rtx4090`)
   - Built FROM custodire/dfl-base:rtx4090
   - Complete DeepFaceLab installation
   - All DFL scripts and models
   - Workspace directory structure
   - Entry point for DFL commands

### Workspace Structure
```
/workspace/
├── data/              # Input videos and images
├── data_src/          # Source face data
├── data_dst/          # Destination face data
├── models/            # Trained DFL models
├── aligned/           # Aligned faces
└── output/            # Generated deepfakes
```

### Docker Build Requirements
- Use multi-stage builds to minimize image size
- Layer caching for faster rebuilds
- GPU access via `--gpus all` flag
- Volume mounts for persistent data
- Non-root user for security
- Clear documentation in Dockerfiles

### Testing Criteria
The final images must:
1. Successfully detect RTX 4090 GPU (`nvidia-smi` works)
2. Import TensorFlow GPU successfully
3. Run DFL extraction on sample video
4. Train a small model (1000 iterations)
5. Generate a test deepfake merge
6. Complete end-to-end workflow without errors

### Output Artifacts
1. **Dockerfiles**:
   - `docker/dfl-base.Dockerfile` - Base image
   - `docker/dfl.Dockerfile` - DFL image
   - `docker/dfl.dockerignore` - Build exclusions

2. **Build Scripts**:
   - `docker/build_dfl_images.sh` - Automated build script
   - `docker/test_dfl_rtx4090.sh` - Validation script

3. **Documentation**:
   - `docs/dfl_docker_images.md` - Usage guide
   - `docs/dfl_training_workflow.md` - DFL training guide

4. **Sample Compose**:
   - `docker/dfl-compose.yaml` - Docker Compose config

### Safety and Security
- Images must NOT include pretrained models or datasets (privacy)
- Use read-only mounts for dataset access
- All training data stays in mounted volumes
- GPU memory limits configurable
- No privileged mode (use `--gpus all` instead)

### Integration with Custodire
- Images should be tagged and tracked in Custodire ingest system
- Build metadata (CUDA version, DFL version, build date) in labels
- Images stored in `docker/images/` directory
- SHA-256 hashes recorded in evidence ledger

## Success Criteria

1. Base image builds successfully (~5GB)
2. DFL image builds successfully (~8GB)
3. RTX 4090 GPU detected in container
4. TensorFlow GPU import works
5. Can run DFL extraction on test video
6. Can train model for 100 iterations
7. Can generate test merge
8. All artifacts properly tagged and documented
9. Images follow Docker best practices
10. Complete end-to-end workflow documented

## Context

This is part of Custodire's adversarial hardening strategy. By building DFL Docker images, we can:
1. Generate synthetic training data for detector hardening
2. Test detection capabilities against state-of-the-art face swapping
3. Ensure reproducible deepfake generation environment
4. Maintain air-gapped synthetic data generation pipeline

## Notes

- RTX 4090 has 24GB VRAM - leverage this for larger batch sizes
- DFL can be memory-intensive during training
- Consider model quantization for inference optimization
- Document CUDA/cuDNN version combinations that work
- Test with both H.264 and HEVC video codecs
