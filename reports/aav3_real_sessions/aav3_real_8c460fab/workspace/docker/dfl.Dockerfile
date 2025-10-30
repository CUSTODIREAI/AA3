ARG BASE_IMAGE=custodire/dfl:base-cuda11.8-tf2.13.1
FROM ${BASE_IMAGE}

USER root

LABEL org.opencontainers.image.title="DeepFaceLab (CUDA 11.8, TF 2.13.1)" \
      org.opencontainers.image.description="DeepFaceLab runtime on CUDA 11.8/TF 2.13.1 for RTX 4090. Excludes pretrained models." \
      org.opencontainers.image.vendor="Custodire" \
      org.opencontainers.image.licenses="GPL-3.0" \
      org.opencontainers.image.source="https://github.com/iperov/DeepFaceLab"

# Build arg for DFL ref (branch/tag/commit). Default to master.
ARG DFL_REF=master
ENV DFL_DIR=/opt/dfl/DeepFaceLab

# Clone DFL at specified ref and strip large/non-redistributable dirs
RUN set -eux; \
    apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*; \
    mkdir -p /opt/dfl; \
    git clone https://github.com/iperov/DeepFaceLab.git "$DFL_DIR"; \
    cd "$DFL_DIR"; \
    # Checkout to branch/tag/commit provided in DFL_REF
    if git rev-parse --verify --quiet "$DFL_REF" >/dev/null; then \
      git checkout -q "$DFL_REF"; \
    else \
      git fetch --depth=1 origin "$DFL_REF" && git checkout -q FETCH_HEAD || echo "DFL_REF not directly resolvable, staying on default"; \
    fi; \
    # Record exact commit
    git rev-parse HEAD > /opt/dfl/DFL_COMMIT; \
    # Remove non-essential and large assets (pretrained/workspace) from image
    rm -rf .git pretrained workspace || true

# Copy entrypoint wrapper
COPY --chown=dfl:dfl entrypoint.dfl.sh /usr/local/bin/dfl
RUN chmod +x /usr/local/bin/dfl

# Ensure ownership of /opt/dfl and workspace
RUN chown -R dfl:dfl /opt/dfl /workspace

USER dfl
WORKDIR /workspace

ENV DFL_HOME=/opt/dfl \
    DFL_DIR=/opt/dfl/DeepFaceLab

ENTRYPOINT ["/usr/local/bin/dfl"]
# Show DFL help if no args
CMD ["help"]
