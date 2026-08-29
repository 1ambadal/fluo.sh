import os
import logging
import numpy as np
from typing import Optional
from faster_whisper.vad import get_vad_model
from backend.config import VAD_MODEL_PATH

logger = logging.getLogger(__name__)

_FRAME_SIZE = 512           # samples per frame (32 ms @ 16 kHz)
_BYTES_PER_FRAME = _FRAME_SIZE * 2  # 16-bit PCM → 1024 bytes
_CONTEXT_SIZE = 64         # samples for context window


class VoiceActivityDetector:
    """
    Streaming Voice Activity Detector powered by Silero VAD (v6).
    Processes incoming 16 kHz 16-bit mono PCM bytes in real-time.
    Triggers speech START / END events and returns complete speech segments.
    """

    def __init__(
        self,
        model_path: str = VAD_MODEL_PATH,
        threshold: float = 0.5,
        sampling_rate: int = 16000,
        min_silence_duration_ms: int = 700,
        min_speech_duration_ms: int = 250,
    ):
        self.threshold = threshold
        self.sampling_rate = sampling_rate
        self.min_silence_chunks = max(1, int((min_silence_duration_ms / 1000) * sampling_rate / _FRAME_SIZE))
        self.min_speech_chunks = max(1, int((min_speech_duration_ms / 1000) * sampling_rate / _FRAME_SIZE))

        # Use faster_whisper's bundled Silero VAD ONNX model session
        self.vad_model = get_vad_model()

        self.reset()

    def reset(self) -> None:
        """Resets recurrent states, buffers, and detection counters."""
        self.h = np.zeros((1, 1, 128), dtype=np.float32)
        self.c = np.zeros((1, 1, 128), dtype=np.float32)
        self.last_context = np.zeros((1, _CONTEXT_SIZE), dtype=np.float32)
        self.raw_buffer = bytearray()
        self.accumulated_speech = []
        self.is_speaking = False
        self.speech_chunks_count = 0
        self.silence_chunks_count = 0

    def process_audio(self, chunk_bytes: bytes) -> Optional[np.ndarray]:
        """
        Processes a chunk of 16-bit, 16 kHz mono PCM bytes.
        Returns the complete speech segment as a float32 array when silence is
        detected after speech, otherwise returns None.
        """
        self.raw_buffer.extend(chunk_bytes)
        while len(self.raw_buffer) >= _BYTES_PER_FRAME:
            frame_bytes = self.raw_buffer[:_BYTES_PER_FRAME]
            del self.raw_buffer[:_BYTES_PER_FRAME]

            frame = np.frombuffer(frame_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            frame_2d = frame[np.newaxis, :]
            chunk_with_context = np.concatenate([self.last_context, frame_2d], axis=1)

            out, self.h, self.c = self.vad_model.session.run(
                None, {"input": chunk_with_context, "h": self.h, "c": self.c}
            )
            prob = float(out.flat[0])
            self.last_context = frame_2d[:, -_CONTEXT_SIZE:]

            if prob >= self.threshold:
                self.silence_chunks_count = 0
                self.speech_chunks_count += 1
                if not self.is_speaking and self.speech_chunks_count >= self.min_speech_chunks:
                    self.is_speaking = True
                    self.accumulated_speech.clear()
                    logger.info(f"[VAD] Speech START detected (prob={prob:.3f})")
                if self.is_speaking:
                    self.accumulated_speech.append(frame)
            else:
                self.speech_chunks_count = 0
                if self.is_speaking:
                    self.silence_chunks_count += 1
                    self.accumulated_speech.append(frame)
                    if self.silence_chunks_count >= self.min_silence_chunks:
                        full_speech = np.concatenate(self.accumulated_speech)
                        speech_rms = np.sqrt(np.mean(full_speech ** 2)) if len(full_speech) > 0 else 0.0
                        self.reset()

                        # Ignore quiet background noise segment
                        if speech_rms < 0.008:
                            logger.info(f"[VAD] Discarded low-energy segment (RMS={speech_rms:.4f})")
                            return None

                        logger.info(f"[VAD] Speech END — {len(full_speech)/16000:.2f}s captured (RMS={speech_rms:.4f}), sending to STT")
                        return full_speech

        return None
