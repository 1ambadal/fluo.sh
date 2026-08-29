import os
import re
import warnings
import numpy as np
from kokoro_onnx import Kokoro
from backend.config import KOKORO_MODEL_PATH, KOKORO_VOICES_PATH, KOKORO_VOICE_DEFAULT

# language name → Kokoro lang code
_LANG_CODE: dict[str, str] = {
    "english": "en-us",
}

# language name → preferred voice
# af_bella / af_heart / af_nicole are generally the most natural-sounding
# American English voices in the current Kokoro voice pack.
_LANG_VOICE: dict[str, str] = {
    "english": "af_bella",
}

# Slightly under 1.0 tends to sound less clipped/robotic than the default.
_DEFAULT_SPEED = 0.95

# Sentence boundary: punctuation followed by whitespace, quote, or end of string.
_SENTENCE_END = re.compile(r'[^.!?。！？\n]+[.!?。！？\n]+(?:\s+|["\']|$)')


class KokoroTTSEngine:
    def __init__(
        self,
        model_path: str = KOKORO_MODEL_PATH,
        voices_path: str = KOKORO_VOICES_PATH,
    ):
        self.kokoro: Kokoro | None = None
        self._available_voices: set[str] = set()

        if not os.path.exists(model_path):
            raise RuntimeError(f"Kokoro model not found: {model_path}")
        if not os.path.exists(voices_path):
            raise RuntimeError(f"Kokoro voices not found: {voices_path}")

        try:
            self.kokoro = Kokoro(model_path, voices_path)
            self._available_voices = set(self.kokoro.get_voices())
        except Exception as e:
            raise RuntimeError(f"Kokoro init failed: {e}") from e

        # Fail loud instead of silently falling back to the wrong voice.
        if KOKORO_VOICE_DEFAULT not in self._available_voices:
            raise RuntimeError(
                f"KOKORO_VOICE_DEFAULT='{KOKORO_VOICE_DEFAULT}' not in loaded voice pack. "
                f"Available voices: {sorted(self._available_voices)}"
            )

        missing = {
            lang: v for lang, v in _LANG_VOICE.items()
            if v not in self._available_voices
        }
        if missing:
            warnings.warn(
                f"Kokoro voices not found for: {missing} — will fall back to "
                f"KOKORO_VOICE_DEFAULT='{KOKORO_VOICE_DEFAULT}'"
            )

    def generate_speech(
        self,
        text: str,
        language: str = "english",
        voice: str | None = None,
        speed: float = _DEFAULT_SPEED,
    ) -> tuple[bytes, int]:
        """
        Synthesizes speech for the given text and language.
        Returns (pcm_16bit_bytes, sample_rate). Returns (b"", 24000) on empty input.
        """
        if not text.strip():
            return b"", 24000

        lang_key = language.lower().strip()
        lang_code = _LANG_CODE.get(lang_key, "en-us")

        selected_voice = voice or _LANG_VOICE.get(lang_key, KOKORO_VOICE_DEFAULT)
        if selected_voice not in self._available_voices:
            warnings.warn(
                f"Voice '{selected_voice}' not available, falling back to "
                f"'{KOKORO_VOICE_DEFAULT}'"
            )
            selected_voice = KOKORO_VOICE_DEFAULT

        samples, sample_rate = self.kokoro.create(
            text.strip(), voice=selected_voice, speed=speed, lang=lang_code
        )
        np.clip(samples, -1.0, 1.0, out=samples)
        pcm = (samples * 32767).astype(np.int16)
        return pcm.tobytes(), sample_rate


class SentenceSplitter:
    """
    Accumulates streamed LLM text and yields complete sentences as they form.
    Handles Latin (.!?) and CJK (。！？) punctuation.
    Does NOT split on common abbreviations (Dr., e.g., etc.).

    batch_size controls how many sentences are grouped per yield — batching
    2 sentences per TTS call (instead of 1) improves prosody continuity and
    reduces the choppy/flat sound of synthesizing very short fragments in
    isolation, at a small latency cost.
    """

    def __init__(self, batch_size: int = 2):
        self.buffer = ""
        self._pending: list[str] = []
        self.batch_size = batch_size

    def append(self, text: str) -> list[str]:
        """Add a streamed chunk; returns any newly completed sentence batches."""
        self.buffer += text
        batches: list[str] = []
        while match := _SENTENCE_END.search(self.buffer):
            self._pending.append(match.group(0).strip())
            self.buffer = self.buffer[match.end():]
            if len(self._pending) >= self.batch_size:
                batches.append(" ".join(self._pending))
                self._pending = []
        return batches

    def flush(self) -> str | None:
        """Return (and clear) any remaining buffered/pending text as a final chunk."""
        remaining_parts = self._pending + ([self.buffer.strip()] if self.buffer.strip() else [])
        self._pending = []
        self.buffer = ""
        combined = " ".join(p for p in remaining_parts if p).strip()
        return combined or None