# syntax=docker/dockerfile:1.6
ARG BASE_IMAGE="dfl-base:latest"
FROM ${BASE_IMAGE}

SHELL ["/bin/bash", "-lc"]

ENV DFL_REPO="https://github.com/iperov/DeepFaceLab.git" \
    DFL_REF="master" \
    DFL_DIR="/opt/DeepFaceLab" \
    PYTHONUNBUFFERED=1 \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

# Ensure git is present (if base changes in the future)
USER root
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Clone DFL at selectable ref without relying on local context
RUN set -eux; \
    git clone --depth=1 "${DFL_REPO}" "${DFL_DIR}"; \
    cd "${DFL_DIR}"; \
    # If a specific ref is desired, attempt to checkout (noop for master)
    if [[ "${DFL_REF}" != "master" ]]; then \
      git fetch --depth=1 origin "${DFL_REF}" || true; \
      git checkout "${DFL_REF}" || true; \
    fi

# Strip potential large/pretrained assets if present (no-op if paths absent)
RUN set -eux; \
    if [ -d "${DFL_DIR}/_internal" ]; then \
      find "${DFL_DIR}/_internal" \
        -type f \( -name "*.dat" -o -name "*.pb" -o -name "*.onnx" -o -name "*.pth" \) \
        -print -exec rm -f {} \; || true; \
    fi

# Conditionally install DFL-provided requirements if they exist
RUN set -eux; \
    if [ -f "${DFL_DIR}/requirements-cuda.txt" ]; then \
      pip install --no-cache-dir -r "${DFL_DIR}/requirements-cuda.txt"; \
    elif [ -f "${DFL_DIR}/requirements.txt" ]; then \
      pip install --no-cache-dir -r "${DFL_DIR}/requirements.txt"; \
    else \
      echo "No requirements file found in DFL repo. Using base deps."; \
    fi

# Restore non-root defaults and developer-friendly environment
USER appuser
WORKDIR /workspace
ENV PYTHONPATH="${DFL_DIR}:$PYTHONPATH"
ENTRYPOINT ["/bin/bash"]
