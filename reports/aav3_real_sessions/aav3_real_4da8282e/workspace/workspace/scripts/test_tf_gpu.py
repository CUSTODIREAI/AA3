#!/usr/bin/env python3
import json
import os

result = {
    "ok": False,
    "tf_version": None,
    "num_gpus": 0,
    "devices": [],
    "compute_device_used": None,
    "error": None,
}

try:
    import tensorflow as tf
    result["tf_version"] = tf.__version__

    gpus = tf.config.list_physical_devices("GPU")
    result["num_gpus"] = len(gpus)

    # Try to enable memory growth per GPU (if any)
    for gpu in gpus:
        try:
            tf.config.experimental.set_memory_growth(gpu, True)
        except Exception:
            pass

    # Enumerate logical devices
    result["devices"] = [
        {"name": d.name, "device_type": d.device_type} for d in tf.config.list_logical_devices()
    ]

    # Perform a tiny matmul on GPU if available, else CPU
    use_gpu = len(gpus) > 0
    device = "/GPU:0" if use_gpu else "/CPU:0"
    with tf.device(device):
        a = tf.random.uniform((512, 512))
        b = tf.random.uniform((512, 512))
        c = tf.matmul(a, b)
        # Force compute and capture a small scalar to ensure execution
        _ = float(tf.reduce_sum(c[:1]).numpy())

    result["compute_device_used"] = "GPU" if use_gpu else "CPU"
    result["ok"] = True
except Exception as e:
    result["ok"] = False
    result["error"] = repr(e)

print(json.dumps(result))
