import json
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.db import queries
from backend.db.database import async_init_db
from backend.llm.client import LLMClient
from backend.llm.conversation_prompt import get_conversation_prompt
from backend.llm.feedback_prompt import get_feedback_prompt
from backend.stt.whisper_engine import WhisperSpeechToText
from backend.tts.kokoro_engine import KokoroTTSEngine
from backend.ws import handler

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("phonemizer").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Database
    await async_init_db()

    # LLM
    try:
        llm = LLMClient()
    except Exception as e:
        logger.error(f"LLM init failed, falling back to mock: {e}")
        llm = LLMClient(provider="mock")

    # STT + TTS
    stt = WhisperSpeechToText()
    tts = KokoroTTSEngine()

    handler.init_ws_engines(llm, stt, tts)
    yield


app = FastAPI(title="AI Language Learner API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Models ------------------------------------------------------------------

class ConversationCreate(BaseModel):
    language: str
    topic: str | None = None
    proficiency: str | None = None  # beginner | intermediate | advanced
    user_name: str | None = None


class MessageCreate(BaseModel):
    text: str


# --- Routes ------------------------------------------------------------------

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.post("/api/conversations", status_code=status.HTTP_201_CREATED)
async def create_conversation(data: ConversationCreate):
    try:
        conv_id = await queries.create_conversation(data.language, data.topic, data.proficiency, data.user_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"id": conv_id, "language": data.language, "topic": data.topic, "proficiency": data.proficiency, "user_name": data.user_name}


@app.get("/api/conversations")
async def list_conversations():
    try:
        return await queries.list_conversations()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/conversations")
async def clear_all_conversations():
    try:
        await queries.clear_all_conversations()
        return {"status": "ok", "message": "All conversations cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: int):
    try:
        conv = await queries.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        messages = await queries.get_conversation_messages(conversation_id)
        for msg in messages:
            if msg.get("feedback"):
                try:
                    msg["feedback"] = json.loads(msg["feedback"])
                except Exception:
                    pass

        return {"conversation": conv, "messages": messages}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/conversations/{conversation_id}/messages")
async def post_message(conversation_id: int, msg_data: MessageCreate):
    """HTTP fallback for non-WebSocket clients. Runs the full dual-pass LLM pipeline."""
    try:
        conv = await queries.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        language    = conv["language"]
        topic       = conv.get("topic")
        proficiency = conv.get("proficiency")

        user_msg_id = await queries.add_message(conversation_id, "user", msg_data.text)

        db_messages = await queries.get_conversation_messages(conversation_id)
        llm_history = [{"role": m["role"], "content": m["text"]} for m in db_messages]

        conv_prompt = get_conversation_prompt(language, topic, proficiency)
        feed_prompt = get_feedback_prompt(language)

        async def _reply():
            return "".join([chunk async for chunk in handler.llm_client.stream_reply(conv_prompt, llm_history)])

        async def _feedback():
            return await handler.llm_client.generate_feedback(feed_prompt, msg_data.text)

        reply_text, feedback = await asyncio.gather(_reply(), _feedback())

        assistant_msg_id = await queries.add_message(conversation_id, "assistant", reply_text)
        await queries.update_message_feedback(user_msg_id, json.dumps(feedback))

        return {
            "user_message_id": user_msg_id,
            "assistant_message_id": assistant_msg_id,
            "reply": reply_text,
            "feedback": feedback,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/conversation/{conversation_id}")
async def websocket_route(websocket: WebSocket, conversation_id: int):
    await handler.handle_websocket_connection(websocket, conversation_id)
