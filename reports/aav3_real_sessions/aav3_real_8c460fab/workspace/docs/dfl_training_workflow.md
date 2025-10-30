# DeepFaceLab Training Workflow (Dockerized)

Prereqs:
- Prepare input data under workspace/: source/ (face A), target/ (face B), and an empty models/ for training artifacts.

Typical steps:
1) Extract faces
   - docker run --rm -it --gpus all -v $(pwd)/workspace:/workspace custudire/dfl:dfl-cuda11.8-tf2.13.1 \
     extract --input-dir /workspace/source --output-dir /workspace/source_aligned --detector s3fd --max-faces 1 --manual-fix False

2) Train model
   - docker run --rm -it --gpus all -v $(pwd)/workspace:/workspace custudire/dfl:dfl-cuda11.8-tf2.13.1 \
     train --model-dir /workspace/models/SAEHD --training-data-src-dir /workspace/source_aligned --training-data-dst-dir /workspace/target_aligned \
     --gpu 0 --write-image-summary False --write-preview-history False

3) Merge/convert
   - docker run --rm -it --gpus all -v $(pwd)/workspace:/workspace custudire/dfl:dfl-cuda11.8-tf2.13.1 \
     merge --input-dir /workspace/target --output-dir /workspace/output --model-dir /workspace/models/SAEHD

Tips:
- Use --manual-fix True for challenging datasets.
- Monitor VRAM; if OOM occurs, lower batch size or enable allow_growth (already enabled).
- Prefer onnxruntime-gpu backends for detectors when available to speed up extract.
- Keep data and models on a persistent mounted volume (workspace/).

Caveats:
- Command names/flags may vary slightly across DFL revisions. Run `help` to see available actions and options.
- Some optional dependencies (e.g., dlib) are not included to keep the image light; add as needed.
