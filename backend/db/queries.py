from typing import List, Optional
import json
from backend.db import database

async def create_conversation(language: str, topic: Optional[str] = None, proficiency: Optional[str] = None, user_name: Optional[str] = None) -> int:
    """Creates a new conversation and returns its ID."""
    query = "INSERT INTO conversations (language, topic, proficiency, user_name) VALUES (?, ?, ?, ?);"
    return await database.execute_write(query, (language, topic, proficiency, user_name))

async def get_conversation(conversation_id: int) -> Optional[dict]:
    """Retrieves a conversation by its ID."""
    query = "SELECT * FROM conversations WHERE id = ?;"
    return await database.execute_read_one(query, (conversation_id,))

async def get_conversation_messages(conversation_id: int, limit: int = 0) -> List[dict]:
    """Retrieves messages for a specific conversation in chronological order.
    If limit > 0, returns only the last N messages (for LLM context windowing).
    """
    if limit > 0:
        query = """SELECT * FROM (
            SELECT * FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?
        ) sub ORDER BY id ASC;"""
        return await database.execute_read_all(query, (conversation_id, limit))
    else:
        query = "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC;"
        return await database.execute_read_all(query, (conversation_id,))

async def add_message(conversation_id: int, role: str, text: str, feedback: Optional[str] = None) -> int:
    """Adds a new message to the database."""
    query = "INSERT INTO messages (conversation_id, role, text, feedback) VALUES (?, ?, ?, ?);"
    return await database.execute_write(query, (conversation_id, role, text, feedback))

async def update_message_feedback(message_id: int, feedback_json: str) -> None:
    """Updates the feedback JSON for a message."""
    query = "UPDATE messages SET feedback = ? WHERE id = ?;"
    await database.execute_write(query, (feedback_json, message_id))

async def list_conversations(limit: int = 20) -> List[dict]:
    """Retrieves the latest conversations."""
    query = "SELECT * FROM conversations ORDER BY id DESC LIMIT ?;"
    return await database.execute_read_all(query, (limit,))

async def clear_all_conversations() -> None:
    """Deletes all messages and conversations."""
    await database.execute_write("DELETE FROM messages;")
    await database.execute_write("DELETE FROM conversations;")
