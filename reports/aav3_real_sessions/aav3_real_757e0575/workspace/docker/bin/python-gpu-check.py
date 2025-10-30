import os
import sys

try:
    import tensorflow as tf
except Exception as e:
    print("Failed to import TensorFlow:", e)
    sys.exit(1)

print("TF:", tf.__version__)
print("CUDA visible devices:", os.environ.get("CUDA_VISIBLE_DEVICES", "<not set>"))
print("GPUs:", tf.config.list_physical_devices('GPU'))
try:
    logical = tf.config.list_logical_devices('GPU')
    print("Logical GPUs:", logical)
except Exception as e:
    print("Error listing logical GPUs:", e)
