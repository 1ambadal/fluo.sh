import sqlite3
import asyncio
import threading
from pathlib import Path
from backend.config import DATABASE_PATH

# Persistent connection with thread-safe access for single-user app
_connection: sqlite3.Connection = None
_lock = threading.Lock()

def get_connection() -> sqlite3.Connection:
    """Returns a persistent SQLite connection (thread-safe via lock)."""
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA foreign_keys = ON;")
        _connection.execute("PRAGMA journal_mode = WAL;")  # Better concurrent read/write
    return _connection

def init_db():
    """Initializes the database using the schema.sql file and applies migrations."""
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found at {schema_path}")
        
    with open(schema_path, "r") as f:
        schema_sql = f.read()
        
    conn = get_connection()
    with _lock:
        conn.executescript(schema_sql)
        
        # Check if 'proficiency' column exists in 'conversations' table
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(conversations);")
        columns = [row["name"] for row in cursor.fetchall()]
        if "proficiency" not in columns:
            cursor.execute("ALTER TABLE conversations ADD COLUMN proficiency TEXT;")
        if "user_name" not in columns:
            cursor.execute("ALTER TABLE conversations ADD COLUMN user_name TEXT;")
            
        conn.commit()

async def async_init_db():
    """Asynchronously initializes the database."""
    await asyncio.to_thread(init_db)

async def execute_write(query: str, params: tuple = ()) -> int:
    """Executes a write query (INSERT, UPDATE, DELETE) and returns the lastrowid."""
    def _write():
        conn = get_connection()
        with _lock:
            try:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor.lastrowid
            except Exception as e:
                conn.rollback()
                raise e
    return await asyncio.to_thread(_write)

async def execute_read_all(query: str, params: tuple = ()) -> list:
    """Executes a read query and returns all matching rows as dictionaries."""
    def _read():
        conn = get_connection()
        with _lock:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    return await asyncio.to_thread(_read)

async def execute_read_one(query: str, params: tuple = ()) -> dict:
    """Executes a read query and returns the first matching row or None."""
    def _read():
        conn = get_connection()
        with _lock:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
    return await asyncio.to_thread(_read)
