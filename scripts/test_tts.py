#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.tts.kokoro_engine import KokoroTTSEngine, SentenceSplitter

def test_sentence_splitter():
    print("Testing SentenceSplitter...")
    splitter = SentenceSplitter()
    
    chunks = [
        "¡Hola! ¿Cómo ",
        "estás? Yo estoy ",
        "muy bien. Hoy vamos ",
        "a hablar sobre comida. ¿Qué ",
        "te gusta comer?"
    ]
    
    all_sentences = []
    for chunk in chunks:
        sentences = splitter.append(chunk)
        if sentences:
            print(f"  Appended chunk: '{chunk}' -> Formed sentences: {sentences}")
            all_sentences.extend(sentences)
        else:
            print(f"  Appended chunk: '{chunk}' -> No complete sentence yet")
            
    final = splitter.flush()
    if final:
        print(f"  Flushed remainder: '{final}'")
        all_sentences.append(final)
        
    print(f"Total extracted sentences: {all_sentences}")
    assert len(all_sentences) == 5, f"Expected 5 sentences, got {len(all_sentences)}"
    print("✓ SentenceSplitter test passed!")

def test_tts_engine():
    print("\nInitializing Kokoro TTS Engine...")
    try:
        tts = KokoroTTSEngine()
        if tts.kokoro is None:
            print("✗ Kokoro engine failed to initialize (model files missing or init error).")
            sys.exit(1)
            
        print("✓ KokoroTTSEngine initialized successfully!")
        
        # Test Spanish speech generation
        test_text = "¡Hola! ¿Cómo estás hoy? Espero que estés listo para hablar en español."
        print(f"Generating Spanish voice for: '{test_text}'")
        audio_bytes, sr = tts.generate_speech(test_text, "Spanish")
        
        print(f"Result: {len(audio_bytes)} bytes generated, sample rate: {sr} Hz")
        assert len(audio_bytes) > 0, "No audio bytes generated!"
        assert sr == 24000, f"Expected 24000 Hz, got {sr}"
        print("✓ KokoroTTS Spanish voice generation passed!")
        
    except Exception as e:
        print(f"✗ Failed to run TTS engine tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_sentence_splitter()
    test_tts_engine()
