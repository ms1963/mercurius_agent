"""
5-Tier Cognitive Memory Engine for Mercurius with SQLite FTS5 Full-Text Search.
Layers: Working, Episodic, Semantic, Procedural, Core.
"""
from __future__ import annotations
import sqlite3, json, time, os
from typing import Any, Dict, List, Optional
from mercurius.core.types import ChatMessage, MessageRole

class MemoryManager:
    def __init__(self, db_path: str = "data/memory/mercury_memory.sqlite"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.working_memory: Dict[str, Any] = {}
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS episodic (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp REAL,
                    metadata_json TEXT
                )
            """)
            self.conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS episodic_fts USING fts5(
                    content,
                    session_id UNINDEXED,
                    tokenize='porter'
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS semantic_store (
                    id TEXT PRIMARY KEY,
                    key TEXT,
                    content TEXT,
                    category TEXT,
                    embedding_json TEXT,
                    created_at REAL
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS core_memory (
                    key TEXT PRIMARY KEY,
                    section TEXT,
                    value TEXT,
                    updated_at REAL
                )
            """)

    # --- Working Memory ---
    def set_working(self, key: str, value: Any):
        self.working_memory[key] = value

    def get_working(self, key: str, default: Any = None) -> Any:
        return self.working_memory.get(key, default)

    def clear_working(self):
        self.working_memory.clear()

    # --- Episodic Memory ---
    def save_chat_message(self, session_id: str, msg: ChatMessage):
        msg_id = f"msg_{time.time_ns()}"
        with self.conn:
            self.conn.execute(
                "INSERT INTO episodic VALUES (?, ?, ?, ?, ?, ?)",
                (msg_id, session_id, msg.role.value, msg.content, msg.timestamp, json.dumps(msg.metadata))
            )
            self.conn.execute(
                "INSERT INTO episodic_fts (content, session_id) VALUES (?, ?)",
                (msg.content, session_id)
            )

    def search_episodic(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        clean_q = "".join(c for c in query if c.isalnum() or c.isspace()).strip()
        if not clean_q:
            return []
        try:
            cursor.execute("""
                SELECT content, session_id, rank 
                FROM episodic_fts 
                WHERE episodic_fts MATCH ? 
                ORDER BY rank LIMIT ?
            """, (clean_q, limit))
            return [{"content": r[0], "session_id": r[1], "rank": r[2]} for r in cursor.fetchall()]
        except Exception:
            return []

    # --- Core Memory ---
    def set_core(self, section: str, key: str, value: str):
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO core_memory VALUES (?, ?, ?, ?)",
                (f"{section}::{key}", section, value, time.time())
            )

    def get_core_section(self, section: str) -> Dict[str, str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT key, value FROM core_memory WHERE section = ?", (section,))
        return {r[0].split("::")[-1]: r[1] for r in cursor.fetchall()}
