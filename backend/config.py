import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Database configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "app.db"))

# LLM Configuration (DeepSeek / Mock)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek")  # deepseek or mock
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

# STT Configuration (faster-whisper)
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "medium.en")  # e.g. medium.en, small.en, base.en
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")  # cpu or cuda
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")  # float32, float16, int8

# TTS Configuration (Kokoro-82M)
KOKORO_MODEL_PATH = os.getenv("KOKORO_MODEL_PATH", str(BASE_DIR / "models" / "kokoro-v1.0.onnx"))
KOKORO_VOICES_PATH = os.getenv("KOKORO_VOICES_PATH", str(BASE_DIR / "models" / "voices-v1.0.bin"))
KOKORO_VOICE_DEFAULT = os.getenv("KOKORO_VOICE_DEFAULT", "af_bella")  # default voice

# VAD Configuration (Silero VAD)
VAD_MODEL_PATH = os.getenv("VAD_MODEL_PATH", str(BASE_DIR / "models" / "silero_vad.onnx"))

# Create data and models directories if they don't exist
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
os.makedirs(BASE_DIR / "models", exist_ok=True)
