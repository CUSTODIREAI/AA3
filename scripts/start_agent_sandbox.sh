#!/usr/bin/env bash
# start_agent_sandbox.sh - One-liner to start/verify agent-sandbox container
#
# Usage:
#   bash scripts/start_agent_sandbox.sh

set -euo pipefail

echo "=== Agent Sandbox Setup ==="

# Check if container is already running
if docker ps --format '{{.Names}}' | grep -q '^agent-sandbox$'; then
    echo "✅ agent-sandbox container is already running"
else
    echo "Starting agent-sandbox container..."

    # Check if container exists but is stopped
    if docker ps -a --format '{{.Names}}' | grep -q '^agent-sandbox$'; then
        echo "Removing stopped agent-sandbox container..."
        docker rm agent-sandbox
    fi

    # Determine base image (try custodire/dev:latest, fallback to ubuntu:22.04)
    BASE_IMAGE="${AGENT_SANDBOX_IMAGE:-ubuntu:22.04}"

    # Start new container with proper mounts
    docker run -d \
        --name agent-sandbox \
        --gpus all \
        -v "$(pwd)/dataset:/dataset:ro" \
        -v "$(pwd)/evidence:/evidence:ro" \
        -v "$(pwd)/staging-final:/staging-final:ro" \
        -v "$(pwd)/workspace:/workspace" \
        -v "$(pwd)/staging:/staging" \
        -v "$(pwd)/cache:/cache" \
        -v "/var/run/docker.sock:/var/run/docker.sock" \
        "$BASE_IMAGE" \
        sleep infinity

    echo "✅ agent-sandbox container started"
fi

echo ""
echo "=== Verification ==="

# Test RO mounts (should fail)
echo -n "Testing dataset RO mount... "
if docker exec agent-sandbox touch /dataset/.test 2>&1 | grep -q "Read-only file system"; then
    echo "✅ Read-only (correct)"
else
    echo "❌ NOT read-only (WRONG!)"
    exit 1
fi

echo -n "Testing evidence RO mount... "
if docker exec agent-sandbox touch /evidence/.test 2>&1 | grep -q "Read-only file system"; then
    echo "✅ Read-only (correct)"
else
    echo "❌ NOT read-only (WRONG!)"
    exit 1
fi

# Test RW mounts (should succeed)
echo -n "Testing workspace RW mount... "
if docker exec agent-sandbox bash -c "touch /workspace/.test && rm /workspace/.test" &>/dev/null; then
    echo "✅ Read-write (correct)"
else
    echo "❌ NOT writable (WRONG!)"
    exit 1
fi

echo -n "Testing staging RW mount... "
if docker exec agent-sandbox bash -c "touch /staging/.test && rm /staging/.test" &>/dev/null; then
    echo "✅ Read-write (correct)"
else
    echo "❌ NOT writable (WRONG!)"
    exit 1
fi

# Test GPU access
echo -n "Testing GPU access... "
if docker exec agent-sandbox nvidia-smi &>/dev/null; then
    GPU_NAME=$(docker exec agent-sandbox nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
    echo "✅ GPU detected: $GPU_NAME"
else
    echo "⚠️  No GPU detected (nvidia-smi not available)"
    echo "   If you have an NVIDIA GPU, ensure nvidia-container-runtime is installed"
fi

echo ""
echo "=== Summary ==="
echo "Container: agent-sandbox"
echo "Status: Running"
echo "Mounts:"
echo "  - /dataset (RO) ← $(pwd)/dataset"
echo "  - /evidence (RO) ← $(pwd)/evidence"
echo "  - /staging-final (RO) ← $(pwd)/staging-final"
echo "  - /workspace (RW) ← $(pwd)/workspace"
echo "  - /staging (RW) ← $(pwd)/staging"
echo "  - /cache (RW) ← $(pwd)/cache"
echo ""
echo "Ready for Direct-Action mode!"
echo ""
echo "Run: python scripts/direct_run.py tasks/your_task.md"
