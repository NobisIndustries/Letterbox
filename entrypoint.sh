#!/bin/sh
set -e

MODELS_DIR=/app/models
DOCRES_URL="https://huggingface.co/DaVinciCode/doctra-docres-main/resolve/main/docres.pkl"
MBD_URL="https://huggingface.co/DaVinciCode/doctra-docres-mbd/resolve/main/mbd.pkl"

mkdir -p "$MODELS_DIR"

if [ ! -f "$MODELS_DIR/docres.pkl" ]; then
    echo "[entrypoint] Downloading docres.pkl (~183MB)..."
    wget -q --show-progress -O "$MODELS_DIR/docres.pkl" "$DOCRES_URL"
else
    echo "[entrypoint] docres.pkl already present, skipping."
fi

if [ ! -f "$MODELS_DIR/mbd.pkl" ]; then
    echo "[entrypoint] Downloading mbd.pkl..."
    wget -q --show-progress -O "$MODELS_DIR/mbd.pkl" "$MBD_URL"
else
    echo "[entrypoint] mbd.pkl already present, skipping."
fi

exec uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1
