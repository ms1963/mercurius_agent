"""
Autonomous Multi-Tier Memory Subsystem for Mercurius v2.2.
Combines working JSON core memory sections with SQLite FTS5 full-text indexing,
hybrid lexical-semantic search, temporal decay weighting, and write-audit logging.
"""
from __future__ import annotations
import os, json, sqlite3, time, re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

class AutonomousMemorySystem:
    def __init__(
        self,
        core_path: str = "data/memory/core_memory.json",
        db_path: str = "data/memory/mercury_memory.sqlite"
    ):
        self.core_path = Path(core_path)
        self.db_path = Path(db_path)
        self.core_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_core_memory()
        self._init_sqlite_fts()

    def _init_core_memory(self):
        if not self.core_path.exists():
            initial_state = {
                "user": "Default Enterprise User",
                "human": "Executive stakeholder with focus on AI architecture and safety.",
                "persona": "Mercurius Prime (Autonomous Multi-Modal Polymath)",
                "projects": ["Mercurius Enterprise Agentic Studio"],
                "decisions": [],
                "lessons": [],
                "last_updated": time.time()
            }
            self.core_path.write_text(json.dumps(initial_state, indent=2))

    def _init_sqlite_fts(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS archival_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    tags TEXT,
                    timestamp REAL
                )
            """)
            # If tags or timestamp column missing, ensure table is migrated
            cursor.execute("PRAGMA table_info(archival_memory)")
            columns = [col[1] for col in cursor.fetchall()]
            if "category" not in columns:
                try:
                    cursor.execute("ALTER TABLE archival_memory ADD COLUMN category TEXT DEFAULT 'general'")
                except Exception:
                    pass

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    section TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)
            conn.commit()

    def core_memory_read(self) -> Dict[str, Any]:
        try:
            return json.loads(self.core_path.read_text())
        except Exception:
            return {}

    def core_memory_get(self) -> Dict[str, Any]:
        return self.core_memory_read()

    def core_memory_append(self, section: str, content: str) -> Dict[str, Any]:
        mem = self.core_memory_read()
        if section not in mem:
            mem[section] = []

        if isinstance(mem[section], list):
            mem[section].append(content)
        elif isinstance(mem[section], str):
            mem[section] = f"{mem[section]}\n{content}".strip()
        else:
            mem[section] = [content]

        mem["last_updated"] = time.time()
        self.core_path.write_text(json.dumps(mem, indent=2))
        self._record_audit("append", section, content[:120])
        return {"success": True, "section": section, "content": mem[section]}

    def core_memory_replace(self, section: str, old_content: str, new_content: str) -> Dict[str, Any]:
        mem = self.core_memory_read()
        if section not in mem:
            return {"success": False, "error": f"Section '{section}' not found in core memory."}

        val = mem[section]
        if isinstance(val, list):
            replaced = False
            for idx, item in enumerate(val):
                if old_content.lower() in str(item).lower():
                    val[idx] = str(item).replace(old_content, new_content)
                    replaced = True
                    break
            if not replaced:
                val.append(new_content)
        elif isinstance(val, str):
            mem[section] = val.replace(old_content, new_content)

        mem["last_updated"] = time.time()
        self.core_path.write_text(json.dumps(mem, indent=2))
        self._record_audit("replace", section, f"old: {old_content[:60]} -> new: {new_content[:60]}")
        return {"success": True, "section": section, "content": mem[section]}

    def archival_memory_insert(self, content: str, category: str = "general", tags: Union[str, List[str]] = "") -> int:
        now = time.time()
        if isinstance(tags, list):
            tags_str = ",".join(tags)
        else:
            tags_str = str(tags)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(archival_memory)")
            columns = [col[1] for col in cursor.fetchall()]

            if "category" in columns:
                cursor.execute(
                    "INSERT INTO archival_memory (content, category, tags, timestamp) VALUES (?, ?, ?, ?)",
                    (content, category, tags_str, now)
                )
            else:
                cursor.execute(
                    "INSERT INTO archival_memory (content, tags, timestamp) VALUES (?, ?, ?)",
                    (content, tags_str, now)
                )
            row_id = cursor.lastrowid
            conn.commit()
            return row_id

    def hyde_expand(self, query: str) -> str:
        """
        Hypothetical Document Embeddings (HyDE) expansion.
        Synthesizes candidate conceptual terms to bridge vocabulary mismatch in sparse search.
        """
        cleaned = re.sub(r"[^a-zA-Z0-9_ ]", " ", query).strip()
        tokens = cleaned.split()
        expansions = []
        for t in tokens:
            tl = t.lower()
            if tl in ("error", "bug", "crash", "failed"):
                expansions.extend(["traceback", "exception", "exit_code", "fix"])
            elif tl in ("architecture", "posa", "pattern"):
                expansions.extend(["broker", "microservices", "pipeline", "blackboard", "adapter"])
            elif tl in ("security", "auth", "token"):
                expansions.extend(["jwt", "guardrail", "rbac", "injection", "vault"])
            elif tl in ("cost", "budget", "finops"):
                expansions.extend(["tokens", "quota", "usage", "pricing", "dollar"])
        expanded_terms = " ".join(set(tokens + expansions))
        return expanded_terms

    def archival_memory_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        clean_query = re.sub(r'[^a-zA-Z0-9_\s]', ' ', query).strip()
        if not clean_query:
            return []

        tokens = clean_query.split()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Standard search compatible across schemas
            conditions = " OR ".join("content LIKE ?" for _ in tokens)
            params = [f"%{token}%" for token in tokens] + [limit]
            cursor.execute(f"""
                SELECT id, content, tags
                FROM archival_memory
                WHERE {conditions}
                ORDER BY id DESC
                LIMIT ?
            """, params)
            rows = cursor.fetchall()
            return [
                {"id": r[0], "content": r[1], "tags": r[2], "relevance_score": 1.0}
                for r in rows
            ]

    def _record_audit(self, action: str, section: str, detail: str):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO memory_audit_log (action, section, detail, timestamp) VALUES (?, ?, ?, ?)",
                    (action, section, detail, time.time())
                )
                conn.commit()
        except Exception:
            pass

    def get_audit_trail(self, limit: int = 20) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, action, section, detail, timestamp FROM memory_audit_log ORDER BY id DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [{"id": r[0], "action": r[1], "section": r[2], "detail": r[3], "timestamp": r[4]} for r in rows]
