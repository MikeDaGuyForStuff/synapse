"""Layer 1: The Memory Store — SQLite-backed persistence for memory objects."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from synapse.types import Memory, MemoryType


class MemoryStore:
    """Persistent memory store backed by SQLite with vector-similarity-capable schema."""

    def __init__(self, db_path: str = "mnemo_data/mnemo.db"):
        self.db_path = str(Path(db_path).expanduser().resolve())
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                embedding TEXT,          -- JSON array of floats
                memory_type TEXT NOT NULL DEFAULT 'episodic',
                importance_score REAL NOT NULL DEFAULT 0.5,
                created_at TEXT NOT NULL,
                last_accessed_at TEXT NOT NULL,
                access_count INTEGER NOT NULL DEFAULT 0,
                decay_rate REAL NOT NULL DEFAULT 0.01,
                tags TEXT NOT NULL DEFAULT '[]',   -- JSON array of strings
                source TEXT NOT NULL DEFAULT '',
                linked_memories TEXT NOT NULL DEFAULT '[]'  -- JSON array of ids
            );
            CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
            CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance_score DESC);
            CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC);
        """)
        self._conn.commit()

    def insert(self, memory: Memory) -> str:
        """Store a new memory. Returns its id."""
        self._conn.execute(
            """INSERT INTO memories
               (id, content, embedding, memory_type, importance_score,
                created_at, last_accessed_at, access_count, decay_rate,
                tags, source, linked_memories)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                memory.id,
                memory.content,
                json.dumps(memory.embedding) if memory.embedding else None,
                memory.memory_type.value,
                memory.importance_score,
                memory.created_at.isoformat(),
                memory.last_accessed_at.isoformat(),
                memory.access_count,
                memory.decay_rate,
                json.dumps(memory.tags),
                memory.source,
                json.dumps(memory.linked_memories),
            ),
        )
        self._conn.commit()
        return memory.id

    def get(self, memory_id: str) -> Optional[Memory]:
        """Retrieve a single memory by id."""
        row = self._conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()
        return self._row_to_memory(row) if row else None

    def update(self, memory: Memory):
        """Update an existing memory."""
        self._conn.execute(
            """UPDATE memories SET
               content=?, embedding=?, memory_type=?, importance_score=?,
               last_accessed_at=?, access_count=?, decay_rate=?,
               tags=?, source=?, linked_memories=?
               WHERE id=?""",
            (
                memory.content,
                json.dumps(memory.embedding) if memory.embedding else None,
                memory.memory_type.value,
                memory.importance_score,
                memory.last_accessed_at.isoformat(),
                memory.access_count,
                memory.decay_rate,
                json.dumps(memory.tags),
                memory.source,
                json.dumps(memory.linked_memories),
                memory.id,
            ),
        )
        self._conn.commit()

    def delete(self, memory_id: str) -> bool:
        """Delete a memory by id. Returns True if deleted."""
        cursor = self._conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def all(self) -> list[Memory]:
        """Return all memories."""
        rows = self._conn.execute(
            "SELECT * FROM memories ORDER BY importance_score DESC"
        ).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) as cnt FROM memories").fetchone()
        return row["cnt"]

    def search_by_content(self, query: str, limit: int = 50) -> list[Memory]:
        """Basic LIKE-based content search (fallback when no embedding)."""
        rows = self._conn.execute(
            "SELECT * FROM memories WHERE content LIKE ? ORDER BY importance_score DESC LIMIT ?",
            (f"%{query}%", limit),
        ).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def get_all_embeddings(self) -> list[tuple[str, list[float]]]:
        """Return (id, embedding) for all memories with embeddings."""
        rows = self._conn.execute(
            "SELECT id, embedding FROM memories WHERE embedding IS NOT NULL"
        ).fetchall()
        result = []
        for r in rows:
            emb = json.loads(r["embedding"])
            result.append((r["id"], emb))
        return result

    def get_memories_by_ids(self, ids: list[str]) -> list[Memory]:
        """Bulk fetch by ids."""
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        rows = self._conn.execute(
            f"SELECT * FROM memories WHERE id IN ({placeholders})", ids
        ).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def close(self):
        self._conn.close()

    def _row_to_memory(self, row: sqlite3.Row) -> Memory:
        return Memory(
            id=row["id"],
            content=row["content"],
            embedding=json.loads(row["embedding"]) if row["embedding"] else None,
            memory_type=MemoryType(row["memory_type"]),
            importance_score=row["importance_score"],
            created_at=self._parse_dt(row["created_at"]),
            last_accessed_at=self._parse_dt(row["last_accessed_at"]),
            access_count=row["access_count"],
            decay_rate=row["decay_rate"],
            tags=json.loads(row["tags"]),
            source=row["source"],
            linked_memories=json.loads(row["linked_memories"]),
        )

    @staticmethod
    def _parse_dt(s: str):
        from datetime import datetime
        return datetime.fromisoformat(s)
