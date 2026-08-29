import numpy as np
import logging
from faster_whisper import WhisperModel
from backend.config import WHISPER_MODEL_SIZE, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE

logger = logging.getLogger(__name__)

# Common hallucination phrases emitted by Whisper on quiet audio / background noise
HALLUCINATIONS = {
    "you", "you.", "thank you", "thank you.", "thank you for watching",
    "thank you for watching.", "thanks for watching", "thanks for watching.",
    "subtitles by...", "bye", "bye.", "amara.org", "so", "thank you very much.",
    "subtitles by amara.org", "listening", "unclear", "[music]", "(music)"
}


class WhisperSpeechToText:
    def __init__(
        self,
        model_size: str = WHISPER_MODEL_SIZE,
        device: str = WHISPER_DEVICE,
        compute_type: str = WHISPER_COMPUTE_TYPE,
    ):
        self.model: WhisperModel | None = None
        self._load(model_size, device, compute_type)

    def _load(self, model_size: str, device: str, compute_type: str) -> None:
        """Loads the Whisper model on CPU using int8 quantization."""
        attempts = [(device, compute_type)]
        if device != "cpu":
            attempts.append(("cpu", "int8"))
        for dev, ct in attempts:
            try:
                m = WhisperModel(model_size, device=dev, compute_type=ct)
                # Warm-up inference check
                list(m.transcribe(np.zeros(16000, dtype=np.float32), beam_size=1)[0])
                self.model = m
                logger.info(f"Whisper STT successfully loaded on {dev} ({ct})")
                return
            except Exception as e:
                logger.warning(f"Whisper load/warmup failed on {dev}/{ct}: {e}")
        self.model = None

    def transcribe(self, audio_data: np.ndarray) -> str:
        """Transcribes a float32 numpy array (16 kHz, mono). Returns transcript string."""
        if self.model is None or len(audio_data) == 0:
            return ""

        # Energy gate — if RMS audio level is under 0.008 (0.8%), treat as noise/silence
        rms = np.sqrt(np.mean(audio_data ** 2))
        if rms < 0.008:
            return ""

        try:
            segments, _ = self.model.transcribe(
                audio_data,
                beam_size=1,
                language="en",
                condition_on_previous_text=False,
                no_speech_threshold=0.6,
                log_prob_threshold=-1.0,
                compression_ratio_threshold=2.4,
                vad_filter=False,  # VAD already pre-segmented this
            )

            valid_texts = []
            for s in segments:
                text_clean = s.text.strip()
                # Filter out no-speech segments, low-confidence segments, or hallucinated phrases
                if s.no_speech_prob > 0.5 or s.avg_logprob < -1.0:
                    continue
                if text_clean.lower() in HALLUCINATIONS:
                    continue
                valid_texts.append(text_clean)

            return " ".join(valid_texts).strip()
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return ""
