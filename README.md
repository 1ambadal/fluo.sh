# Fluo

**Speak. Get corrected. Get fluent.**

An open-source, voice-first AI language learning app. Fluō listens, replies in natural streamed speech, and quietly surfaces grammar corrections alongside the conversation — without ever breaking the flow of talking.

No lessons. No flashcards. Just conversation.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.2.0-61DAFB.svg?style=flat&logo=react&logoColor=black)](https://react.dev)

---

## How it works

1. **Tap to talk.** Silero VAD listens continuously and detects the moment you stop speaking — no manual stop, no fixed timers.
2. **Kai replies, live.** The moment you finish a thought, transcription, LLM response, and voice synthesis all stream concurrently — you hear Kai start replying almost immediately, not after a full round-trip.
3. **Corrections, without interruption.** A second, parallel model quietly grades what you said — grammar, agreement, word choice — and surfaces a compact inline diff (what you said vs. what a native speaker would say) right under your message. Kai never corrects you mid-conversation; that would kill the flow.

---

## Architecture

Two things happen in parallel on every turn: the conversation keeps moving, and your grammar gets graded — independently, so neither one waits on the other.

\`\`\`mermaid
sequenceDiagram
    autonumber
    actor User as Student
    participant FE as React Frontend
    participant BE as FastAPI WebSocket
    participant VAD as Silero VAD (ONNX)
    participant STT as Whisper Engine
    participant LLM as LLM (Chat & Feedback)
    participant TTS as Kokoro TTS Engine

    User->>FE: Speaks into microphone
    FE->>BE: Streams audio chunks (WebSocket)
    BE->>VAD: Evaluates speech boundaries
    Note over BE,VAD: Detects end of speech
    BE->>STT: Transcribes buffered audio
    STT-->>BE: Returns text
    BE->>FE: Sends transcription

    par Conversational reply
        BE->>LLM: Requests reply (Pass 1)
        LLM-->>BE: Streams tokens
        BE->>TTS: Synthesizes speech per sentence
        TTS-->>BE: Streams PCM audio
        BE->>FE: Streams audio playback
        FE-->>User: Plays reply, gapless
    and Grammar feedback
        BE->>LLM: Requests analysis (Pass 2)
        LLM-->>BE: Structured JSON — mistakes + fix
        BE->>FE: Pushes feedback payload
    end
\`\`\`

---

## Stack

| Layer | Choice | Why |
|---|---|---|
| VAD | Silero VAD (ONNX) | Tiny, fast, accurate speech-boundary detection — runs locally on CPU |
| STT | faster-whisper (CTranslate2) | Near state-of-the-art transcription accuracy, runs locally on GPU |
| TTS | kokoro-onnx | Small footprint, natural-sounding local voice synthesis |
| LLM | Pluggable — Anthropic, OpenAI, DeepSeek, or local Ollama | Swap providers via `.env`, no code changes |
| Backend | FastAPI + WebSockets + SQLite | Simple, fast, no unnecessary infra |
| Frontend | React + Vite | Standard, fast dev loop |

STT, TTS, and VAD run entirely on your machine. Only the two LLM calls (conversation + feedback) leave your device, and only if you're using a hosted provider — point `LLM_PROVIDER` at a local Ollama model to keep everything on-device.

## Quick Start (Docker)

\`\`\`bash
cp .env.example .env
\`\`\`

Edit `.env` with your LLM provider of choice:
\`\`\`env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-5
ANTHROPIC_API_KEY=your_key_here
\`\`\`

Or run fully local with Ollama:
\`\`\`env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b-instruct-q4_K_M
\`\`\`

Then:
\`\`\`bash
docker compose up -d --build
\`\`\`

Open **http://localhost:5173**.

---

## Local Development (without Docker)

**Backend**
\`\`\`bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r ../requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
\`\`\`

**Frontend**
\`\`\`bash
cd frontend
npm install
npm run dev
\`\`\`
The frontend dev server proxies API/WebSocket calls to `http://localhost:8000` automatically.

---

## Hardware notes

Comfortable on an 8GB VRAM GPU:
- `faster-whisper` (`large-v3-turbo`, int8) — ~4-5GB VRAM
- `kokoro-onnx` — runs fine on CPU, near-zero GPU cost
- If self-hosting the LLM too, `llama3.1:8b` (Q4_K_M) fits in the remaining headroom, though hosted API models (Claude, GPT, DeepSeek) give noticeably better conversational and grammar-feedback quality than any local 7-8B model today.

---

## Directory Layout

\`\`\`
.
├── backend/
│   ├── db/          # SQLite schema & queries
│   ├── llm/          # Conversation + feedback prompts, provider client
│   ├── stt/          # Whisper wrapper
│   ├── tts/          # Kokoro wrapper
│   ├── vad/          # Silero VAD wrapper
│   └── ws/           # WebSocket orchestration
├── frontend/
│   └── src/
│       ├── audio/       # Gapless audio queue player
│       ├── components/  # UI components
│       ├── hooks/       # WebSocket lifecycle
│       └── App.jsx
├── docker-compose.yml
└── README.md
\`\`\`

---

## Privacy

- Speech recognition, voice activity detection, and voice synthesis all run locally — none of it touches a network call.
- Only your transcribed text is sent to an LLM provider, and only if you're using a hosted one (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, etc.) — point `LLM_PROVIDER=ollama` to keep everything fully on-device.
- No telemetry, no analytics, no third-party tracking.
- `.env` and `data/` are gitignored — your keys and conversation history never leave your machine unintentionally.

## License

MIT — free to use, modify, and redistribute.