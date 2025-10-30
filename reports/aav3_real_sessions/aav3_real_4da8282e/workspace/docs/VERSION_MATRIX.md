# Version Matrix and Compatibility Notes

Chosen Matrix
- CUDA: 11.8.0 (driver: R520+; common 535/550)
- cuDNN: 8.x (bundled in TF 2.13 Linux wheels)
- TensorFlow: 2.13.1 (merged CPU/GPU wheels)
- Python: 3.10 (Ubuntu 22.04 default)

Rationale
- TF 2.13 on CUDA 11.8 is widely stable on Ada (RTX 4090).
- Python 3.10 balances ecosystem support and TF compatibility.

Pins to Avoid Breakage
- numpy==1.23.5, opencv-python==4.8.1.78, scikit-image==0.22.0, h5py==3.8.0, scipy==1.10.1, tqdm==4.66.1.

Caveats
- Upstream DeepFaceLab is TF1.x; use a TF2-compatible fork for training.
- Mixed precision: enable cautiously; NaNs possible without proper scaling.
- FFmpeg NVENC depends on build flags; performance varies.
