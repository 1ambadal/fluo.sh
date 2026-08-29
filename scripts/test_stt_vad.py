#!/usr/bin/env python3
import sys
from pathlib import Path
import numpy as np

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.vad.silero_vad import VoiceActivityDetector
from backend.stt.whisper_engine import WhisperSpeechToText

def main():
    print("Initializing Voice Activity Detector (Silero VAD)...")
    try:
        vad = VoiceActivityDetector()
        print("✓ VoiceActivityDetector initialized successfully!")
    except Exception as e:
        print(f"✗ Failed to initialize VoiceActivityDetector: {e}")
        sys.exit(1)
        
    print("\nInitializing Whisper Speech-to-Text (faster-whisper)...")
    try:
        # Note: This will download the model weights (e.g. small) from HuggingFace on first run
        stt = WhisperSpeechToText()
        if stt.model is not None:
            print("✓ WhisperSpeechToText initialized successfully!")
            
            # Let's run a quick mock transcription of silence
            print("Running mock transcription on silence...")
            dummy_audio = np.zeros(16000 * 2, dtype=np.float32) # 2 seconds of silence
            text = stt.transcribe(dummy_audio)
            print(f"Transcription result (should be empty for silence): '{text}'")
        else:
            print("✗ WhisperSpeechToText initialized in fallback mock mode.")
    except Exception as e:
        print(f"✗ Failed to initialize WhisperSpeechToText: {e}")
        sys.exit(1)
        
    print("\n🎉 VAD and STT engines loaded and ready!")

if __name__ == "__main__":
    main()
