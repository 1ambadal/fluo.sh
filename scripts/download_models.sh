#!/bin/bash
set -e

# Base directory
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODELS_DIR="$BASE_DIR/models"
mkdir -p "$MODELS_DIR"

echo "Downloading models to $MODELS_DIR..."

# 1. Download Silero VAD ONNX Model
VAD_URL="https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx"
VAD_PATH="$MODELS_DIR/silero_vad.onnx"
if [ ! -f "$VAD_PATH" ]; then
    echo "Downloading Silero VAD..."
    curl -L "$VAD_URL" -o "$VAD_PATH"
else
    echo "Silero VAD already exists."
fi

# 2. Download Kokoro-82M ONNX Model (v1.0)
KOKORO_MODEL_URL="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
KOKORO_MODEL_PATH="$MODELS_DIR/kokoro-v1.0.onnx"
if [ ! -f "$KOKORO_MODEL_PATH" ]; then
    echo "Downloading Kokoro-82M ONNX model (v1.0)..."
    curl -L "$KOKORO_MODEL_URL" -o "$KOKORO_MODEL_PATH"
else
    echo "Kokoro-82M ONNX model already exists."
fi

# 3. Download Kokoro-82M Voices (v1.0)
KOKORO_VOICES_URL="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
KOKORO_VOICES_PATH="$MODELS_DIR/voices-v1.0.bin"
if [ ! -f "$KOKORO_VOICES_PATH" ]; then
    echo "Downloading Kokoro-82M voice pack (v1.0)..."
    curl -L "$KOKORO_VOICES_URL" -o "$KOKORO_VOICES_PATH"
else
    echo "Kokoro-82M voice pack already exists."
fi

echo "All models downloaded successfully!"
