#!/bin/sh
# entrypoint.sh — runs once before the server starts.
# Downloads the Whisper model into the HF cache volume if not already present.

set -e

CACHE_DIR="${HF_HOME:-/app/.cache/huggingface}/hub"

# Check if model is already cached in the volume
if [ ! -d "${CACHE_DIR}" ] || [ -z "$(find "${CACHE_DIR}" -mindepth 1 -maxdepth 1 -type d -name 'models--*' 2>/dev/null)" ]; then
    echo "[entrypoint] Whisper model not found in cache. Resolving and downloading..."
    python -c "
import os
from huggingface_hub import snapshot_download

model_size = os.getenv('WHISPER_MODEL_SIZE', 'small.en')

if '/' in model_size:
    repo_id = model_size
else:
    try:
        from faster_whisper.utils import _MODELS
        repo_id = _MODELS.get(model_size, f'Systran/faster-whisper-{model_size}')
    except Exception:
        repo_id = f'Systran/faster-whisper-{model_size}'

print(f'[entrypoint] Resolved model repo to: {repo_id}')
snapshot_download(repo_id=repo_id)
print('[entrypoint] Download complete.')
"
else
    echo "[entrypoint] Whisper model cache found. Skipping download."
fi

exec uvicorn backend.main:app --host 0.0.0.0 --port 8000

