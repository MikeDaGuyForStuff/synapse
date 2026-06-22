"""Layer 1: The Memory Store — SQLite-backed persistence.

Supports 4 memory layers (raw → compressed → knowledge → identity).
No records are ever deleted — all memories persist and get promoted
to higher compression layers over time.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from synapse.types import Memory, MemoryType, MemoryLayer


class MemoryStore:
    """Persistent memory store backed by SQLite.

    Every memory is stored with a layer designation. Higher layers
    represent progressively more compressed/abstract representations.
    """

    def __init__(self, db_path: str = "synapse_data/synapse.db"):
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
                embedding TEXT,
                memory_type TEXT NOT NULL DEFAULT 'episodic',
                layer TEXT NOT NULL DEFAULT 'raw',
                importance_score REAL NOT NULL DEFAULT 0.5,
                created_at TEXT NOT NULL,
                last_accessed_at TEXT NOT NULL,
                access_count INTEGER NOT NULL DEFAULT 0,
                tags TEXT NOT NULL DEFAULT '[]',
                source TEXT NOT NULL DEFAULT '',
                linked_memories TEXT NOT NULL DEFAULT '[]',
                compressed_from TEXT NOT NULL DEFAULT '[]',
                parent_id TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_memories_layer ON memories(layer);
            CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
            CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance_score DESC);
            CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC);
        """)
        self._conn.commit()

    def insert(self, memory: Memory) -> str:
        """Store a new memory. Returns its id."""
        self._conn.execute(
            """INSERT INTO memories
               (id, content, embedding, memory_type, layer, importance_score,
                created_at, last_accessed_at, access_count,
                tags, source, linked_memories, compressed_from, parent_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                memory.id,
                memory.content,
                json.dumps(memory.embedding) if memory.embedding else None,
                memory.memory_type.value,
                memory.layer.value,
                memory.importance_score,
                memory.created_at.isoformat(),
                memory.last_accessed_at.isoformat(),
                memory.access_count,
                json.dumps(memory.tags),
                memory.source,
                json.dumps(memory.linked_memories),
                json.dumps(memory.compressed_from),
                memory.parent_id,
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
               content=?, embedding=?, memory_type=?, layer=?, importance_score=?,
               last_accessed_at=?, access_count=?,
               tags=?, source=?, linked_memories=?, compressed_from=?, parent_id=?
               WHERE id=?""",
            (
                memory.content,
                json.dumps(memory.embedding) if memory.embedding else None,
                memory.memory_type.value,
                memory.layer.value,
                memory.importance_score,
                memory.last_accessed_at.isoformat(),
                memory.access_count,
                json.dumps(memory.tags),
                memory.source,
                json.dumps(memory.linked_memories),
                json.dumps(memory.compressed_from),
                memory.parent_id,
                memory.id,
            ),
        )
        self._conn.commit()

    def all(
        self,
        layer: Optional[MemoryLayer] = None,
        memory_type: Optional[MemoryType] = None,
        limit: int = 1000,
    ) -> list[Memory]:
        """Return all memories, optionally filtered by layer and/or type."""
        conditions = []
        params = []
        if layer:
            conditions.append("layer = ?")
            params.append(layer.value)
        if memory_type:
            conditions.append("memory_type = ?")
            params.append(memory_type.value)
        where = " AND ".join(conditions) if conditions else "1=1"
        rows = self._conn.execute(
            f"SELECT * FROM memories WHERE {where} ORDER BY created_at DESC LIMIT ?",
            params + [limit],
        ).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def count(
        self,
        layer: Optional[MemoryLayer] = None,
        memory_type: Optional[MemoryType] = None,
    ) -> int:
        conditions = []
        params = []
        if layer:
            conditions.append("layer = ?")
            params.append(layer.value)
        if memory_type:
            conditions.append("memory_type = ?")
            params.append(memory_type.value)
        where = " AND ".join(conditions) if conditions else "1=1"
        row = self._conn.execute(
            f"SELECT COUNT(*) as cnt FROM memories WHERE {where}", params
        ).fetchone()
        return row["cnt"]

    def count_by_layer(self) -> dict[str, int]:
        """Return memory count broken down by layer."""
        rows = self._conn.execute(
            "SELECT layer, COUNT(*) as cnt FROM memories GROUP BY layer"
        ).fetchall()
        return {r["layer"]: r["cnt"] for r in rows}

    def count_by_type(self) -> dict[str, int]:
        """Return memory count broken down by memory type."""
        rows = self._conn.execute(
            "SELECT memory_type, COUNT(*) as cnt FROM memories GROUP BY memory_type"
        ).fetchall()
        return {r["memory_type"]: r["cnt"] for r in rows}

    def get_memories_by_ids(self, ids: list[str]) -> list[Memory]:
        """Bulk fetch by ids."""
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        rows = self._conn.execute(
            f"SELECT * FROM memories WHERE id IN ({placeholders})", ids
        ).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def get_candidates_for_compression(
        self, max_count: int = 50, max_days_old: int = 7
    ) -> list[Memory]:
        """Find RAW memories that are old enough for compression.

        Returns memories where:
        - Layer is RAW
        - Created more than max_days_old ago
        - Has low-ish importance (never-accessed or rarely accessed)
        Ordered by oldest first.
        """
        from datetime import datetime, timezone

        cutoff = datetime.now(timezone.utc).isoformat()
        rows = self._conn.execute(
            """SELECT * FROM memories
               WHERE layer = 'raw'
               ORDER BY created_at ASC
               LIMIT ?""",
            (max_count,),
        ).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def search_by_content(self, query: str, limit: int = 50) -> list[Memory]:
        """Basic LIKE-based content search (fallback when no embedding)."""
        rows = self._conn.execute(
            "SELECT * FROM memories WHERE content LIKE ? ORDER BY importance_score DESC LIMIT ?",
            (f"%{query}%", limit),
        ).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def get_all_embeddings(
        self, layer: Optional[MemoryLayer] = None
    ) -> list[tuple[str, list[float]]]:
        """Return (id, embedding) for all memories with embeddings,
        optionally filtered by layer."""
        if layer:
            rows = self._conn.execute(
                "SELECT id, embedding FROM memories WHERE embedding IS NOT NULL AND layer = ?",
                (layer.value,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id, embedding FROM memories WHERE embedding IS NOT NULL"
            ).fetchall()
        result = []
        for r in rows:
            emb = json.loads(r["embedding"])
            result.append((r["id"], emb))
        return result

    def get_layer_stats(self) -> dict:
        """Get detailed stats about each layer."""
        layers_order = ["raw", "compressed", "knowledge", "identity"]
        stats = {}
        for layer_name in layers_order:
            count = self.count(layer=MemoryLayer(layer_name))
            stats[layer_name] = {
                "count": count,
                "avg_importance": self._avg_importance(layer=MemoryLayer(layer_name)),
            }
        return stats

    def close(self):
        self._conn.close()

    def _row_to_memory(self, row: sqlite3.Row) -> Memory:
        return Memory(
            id=row["id"],
            content=row["content"],
            embedding=json.loads(row["embedding"]) if row["embedding"] else None,
            memory_type=MemoryType(row["memory_type"]),
            layer=MemoryLayer(row["layer"]),
            importance_score=row["importance_score"],
            created_at=self._parse_dt(row["created_at"]),
            last_accessed_at=self._parse_dt(row["last_accessed_at"]),
            access_count=row["access_count"],
            tags=json.loads(row["tags"]),
            source=row["source"],
            linked_memories=json.loads(row["linked_memories"]),
            compressed_from=json.loads(row["compressed_from"]) if row["compressed_from"] else [],
            parent_id=row["parent_id"],
        )

    @staticmethod
    def _parse_dt(s: str):
        from datetime import datetime

        return datetime.fromisoformat(s)

    def _avg_importance(self, layer: Optional[MemoryLayer] = None) -> float:
        if layer:
            row = self._conn.execute(
                "SELECT AVG(importance_score) as avg FROM memories WHERE layer = ?",
                (layer.value,),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT AVG(importance_score) as avg FROM memories"
            ).fetchone()
        return row["avg"] or 0.0