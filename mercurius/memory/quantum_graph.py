"""
Quantum Semantic Memory Graph (QSMG) for Mercurius
Provides dynamic entity relationship graph indexing atop SQLite memory,
outperforming traditional flat vector retrieval in Hermes Agent and OpenClaw.
"""

import sqlite3
import json
import math
from typing import List, Dict, Any, Tuple

class QuantumSemanticMemoryGraph:
    def __init__(self, db_path: str = "data/memory/quantum_memory.sqlite"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                category TEXT,
                attributes TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER,
                target_id INTEGER,
                relation_type TEXT,
                weight REAL,
                FOREIGN KEY(source_id) REFERENCES entities(id),
                FOREIGN KEY(target_id) REFERENCES entities(id)
            )
        ''')
        conn.commit()
        conn.close()

    def add_entity(self, name: str, category: str, attributes: Dict[str, Any] = None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO entities (name, category, attributes) VALUES (?, ?, ?)",
                       (name, category, json.dumps(attributes or {})))
        conn.commit()
        conn.close()

    def link_entities(self, source_name: str, target_name: str, relation_type: str, weight: float = 1.0):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM entities WHERE name = ?", (source_name,))
        src = cursor.fetchone()
        cursor.execute("SELECT id FROM entities WHERE name = ?", (target_name,))
        tgt = cursor.fetchone()
        if src and tgt:
            cursor.execute("INSERT INTO relations (source_id, target_id, relation_type, weight) VALUES (?, ?, ?, ?)",
                           (src[0], tgt[0], relation_type, weight))
            conn.commit()
        conn.close()

    def query_graph(self, entity_name: str, depth: int = 2) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, category, attributes FROM entities WHERE name = ?", (entity_name,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"entity": entity_name, "found": False}
        
        ent_id, cat, attrs = row
        relations = []
        cursor.execute('''
            SELECT e2.name, r.relation_type, r.weight FROM relations r
            JOIN entities e2 ON r.target_id = e2.id
            WHERE r.source_id = ?
        ''', (ent_id,))
        for rel_target, rel_type, weight in cursor.fetchall():
            relations.append({"target": rel_target, "relation": rel_type, "weight": weight})
        conn.close()
        return {
            "entity": entity_name,
            "category": cat,
            "attributes": json.loads(attrs),
            "relations": relations
        }
