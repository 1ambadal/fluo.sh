import base64
import json
import logging
import asyncio
from fastapi import WebSocket, WebSocketDisconnect

from backend.db import queries
from backend.llm.client import LLMClient
from backend.llm.conversation_prompt import get_conversation_prompt
from backend.llm.feedback_prompt import get_feedback_prompt
from backend.vad.silero_vad import VoiceActivityDetector
from backend.stt.whisper_engine import WhisperSpeechToText
from backend.tts.kokoro_engine import KokoroTTSEngine, SentenceSplitter

logger = logging.getLogger(__name__)

# Engine singletons — set once at startup via init_ws_engines()
llm_client: LLMClient | None = None
whisper_stt: WhisperSpeechToText | None = None
tts_engine: KokoroTTSEngine | None = None


def init_ws_engines(llm: LLMClient, stt: WhisperSpeechToText, tts: KokoroTTSEngine) -> None:
    global llm_client, whisper_stt, tts_engine
    llm_client, whisper_stt, tts_engine = llm, stt, tts


async def handle_websocket_connection(websocket: WebSocket, conversation_id: int) -> None:
    """
    Manages a real-time WebSocket session:
    binary frames → VAD → STT → parallel (LLM+TTS | feedback)
    text frames   → direct text → parallel (LLM+TTS | feedback)
    """
    await websocket.accept()

    # Load conversation once; keep language/topic/proficiency for the whole session
    try:
        conv = await queries.get_conversation(conversation_id)
        if not conv:
            await websocket.send_json({"type": "error", "message": "Conversation not found"})
            await websocket.close()
            return
    except Exception as e:
        logger.error(f"DB error loading conversation {conversation_id}: {e}")
        await websocket.send_json({"type": "error", "message": "Database error"})
        await websocket.close()
        return

    language   = conv["language"]
    topic      = conv.get("topic")
    proficiency = conv.get("proficiency")
    user_name   = conv.get("user_name")

    # Pre-build prompts once per session — they don't change mid-conversation
    conv_prompt = get_conversation_prompt(language, topic, proficiency, user_name)
    feed_prompt = get_feedback_prompt(language)

    # Per-connection VAD instance (holds its own state machine + audio buffer)
    try:
        vad = VoiceActivityDetector()
    except Exception as e:
        logger.error(f"VAD init failed: {e}")
        await websocket.send_json({"type": "error", "message": "VAD initialisation failed"})
        await websocket.close()
        return

    try:
        while True:
            message = await websocket.receive()

            if "bytes" in message:
                speech = vad.process_audio(message["bytes"])
                if speech is not None:
                    await _handle_speech(websocket, conversation_id, language, conv_prompt, feed_prompt, speech)

            elif "text" in message:
                try:
                    data = json.loads(message["text"])
                    msg_type = data.get("type")

                    if msg_type == "text_message":
                        user_text = data.get("text", "").strip()
                        if user_text:
                            await _run_pipeline(websocket, conversation_id, language, conv_prompt, feed_prompt, user_text)
                    elif msg_type == "initiate":
                        await _run_initiation_pipeline(websocket, conversation_id, language, conv_prompt)
                    elif msg_type == "ping":
                        await websocket.send_json({"type": "pong"})
                except Exception as e:
                    logger.error(f"Bad text message: {e}")
                    await websocket.send_json({"type": "error", "message": "Invalid message format"})

    except (WebSocketDisconnect, RuntimeError):
        pass  # Normal — client navigated away, refreshed, or closed connection
    except Exception as e:
        logger.error(f"WebSocket error (conv {conversation_id}): {e}")
    finally:
        vad.reset()


async def _handle_speech(
    websocket: WebSocket,
    conversation_id: int,
    language: str,
    conv_prompt: str,
    feed_prompt: str,
    audio_data,
) -> None:
    """STT transcription → pipeline."""
    await websocket.send_json({"type": "processing_speech"})
    user_text = await asyncio.to_thread(whisper_stt.transcribe, audio_data)

    if not user_text:
        await websocket.send_json({"type": "transcription", "text": ""})
        return

    await websocket.send_json({"type": "transcription", "text": user_text})
    await _run_pipeline(websocket, conversation_id, language, conv_prompt, feed_prompt, user_text)


async def _run_pipeline(
    websocket: WebSocket,
    conversation_id: int,
    language: str,
    conv_prompt: str,
    feed_prompt: str,
    user_text: str,
) -> None:
    """
    Dual-pass pipeline (runs both passes concurrently):
    Pass 1 — streaming LLM reply → sentence-chunked TTS → audio sent to client
    Pass 2 — grammar/feedback JSON → saved to DB → sent to client
    """
    user_msg_id = await queries.add_message(conversation_id, "user", user_text)

    db_messages = await queries.get_conversation_messages(conversation_id, limit=20)
    llm_history = [{"role": m["role"], "content": m["text"]} for m in db_messages]

    async def _reply_pass() -> None:
        await websocket.send_json({"type": "reply_start"})

        reply_text = ""
        splitter = SentenceSplitter()
        tts_queue: asyncio.Queue = asyncio.Queue()

        async def _tts_worker() -> None:
            while (sentence := await tts_queue.get()) is not None:
                await _synthesise_and_send(websocket, sentence, language)
                tts_queue.task_done()

        worker = asyncio.create_task(_tts_worker())

        async for chunk in llm_client.stream_reply(conv_prompt, llm_history):
            reply_text += chunk
            await websocket.send_json({"type": "reply_chunk", "text": chunk})
            for sentence in splitter.append(chunk):
                await tts_queue.put(sentence)

        if tail := splitter.flush():
            await tts_queue.put(tail)

        await tts_queue.put(None)  # poison pill
        await worker

        msg_id = await queries.add_message(conversation_id, "assistant", reply_text)
        await websocket.send_json({"type": "reply_end", "message_id": msg_id})

    async def _feedback_pass() -> None:
        feedback = await llm_client.generate_feedback(feed_prompt, user_text)
        await queries.update_message_feedback(user_msg_id, json.dumps(feedback))
        await websocket.send_json({
            "type": "feedback",
            "user_message_id": user_msg_id,
            "feedback": feedback,
        })

    try:
        await asyncio.gather(
            asyncio.create_task(_reply_pass()),
            asyncio.create_task(_feedback_pass()),
        )
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})


async def _run_initiation_pipeline(
    websocket: WebSocket,
    conversation_id: int,
    language: str,
    conv_prompt: str,
) -> None:
    """
    Generates fluo's opening greeting/question for the topic when starting a session.
    """
    db_messages = await queries.get_conversation_messages(conversation_id, limit=20)
    llm_history = [{"role": m["role"], "content": m["text"]} for m in db_messages]

    llm_history.append({
        "role": "user",
        "content": "[System: Initiate the conversation with a warm, engaging opening sentence or question about our chosen topic.]"
    })

    await websocket.send_json({"type": "reply_start"})

    reply_text = ""
    splitter = SentenceSplitter()
    tts_queue: asyncio.Queue = asyncio.Queue()

    async def _tts_worker() -> None:
        while (sentence := await tts_queue.get()) is not None:
            await _synthesise_and_send(websocket, sentence, language)
            tts_queue.task_done()

    worker = asyncio.create_task(_tts_worker())

    async for chunk in llm_client.stream_reply(conv_prompt, llm_history):
        reply_text += chunk
        await websocket.send_json({"type": "reply_chunk", "text": chunk})
        for sentence in splitter.append(chunk):
            await tts_queue.put(sentence)

    if tail := splitter.flush():
        await tts_queue.put(tail)

    await tts_queue.put(None)
    await worker

    msg_id = await queries.add_message(conversation_id, "assistant", reply_text)
    await websocket.send_json({"type": "reply_end", "message_id": msg_id})


async def _synthesise_and_send(websocket: WebSocket, text: str, language: str) -> None:
    """Runs Kokoro in a thread and streams the resulting PCM audio to the client."""
    audio_bytes, sr = await asyncio.to_thread(tts_engine.generate_speech, text, language)
    if audio_bytes:
        await websocket.send_json({
            "type": "audio_chunk",
            "audio": base64.b64encode(audio_bytes).decode(),
            "text": text,
            "sample_rate": sr,
        })
