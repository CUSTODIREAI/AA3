DFL Training Workflow (Extract → Train → Merge)

Setup
- Prepare data directories under `./workspace`:
  - `data_src/` (source face video/images)
  - `data_dst/` (destination video/images)
  - `model/` (training checkpoints)
  - `merged/` (merge outputs)
- Start a container with GPU and caches mounted:
  - Example: `docker run -it --rm --gpus all --ipc=host --shm-size=8g -v "$PWD/workspace:/workspace" dfl:tf2.12.1 bash`

Extract
- Detector choice:
  - `s3fd` (best quality; requires PyTorch installed in image)
  - `mtcnn` or other detectors (lighter, may be slower/less accurate)
- Example: `dfl extract --input-dir /workspace/data_src --output-dir /workspace/data_src/aligned --detector s3fd`

Train
- SAEHD is a common model; adjust parameters per dataset.
- Example: `dfl train --training-data-src-dir /workspace/data_src/aligned --training-data-dst-dir /workspace/data_dst/aligned --model-dir /workspace/model --model SAEHD --iterations 1000`

Merge
- Example: `dfl merge --input-dir /workspace/data_dst --output-dir /workspace/merged --model-dir /workspace/model`

Tips
- Keep `TF_FORCE_GPU_ALLOW_GROWTH=true` to avoid OOM on start.
- Increase `--shm-size` if OpenCV/decoding hits shared memory limits.
- Disable XLA unless benchmarking; some models regress with XLA on Ada.
- Ensure stable pins; avoid installing standalone `keras` (use TF bundled Keras).
