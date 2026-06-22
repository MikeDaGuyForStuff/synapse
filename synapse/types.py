"""Memory data types — the core schema for all memory objects."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class MemoryType(str, Enum):
    """Three memory types, mirroring human memory systems."""

    EPISODIC = "episodic"  # things that happened
    SEMANTIC = "semantic"  # facts and knowledge
    PROCEDURAL = "procedural"  # how to do things


@dataclass
class Memory:
    """A single memory object stored and retrieved by the engine."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    embedding: Optional[list[float]] = None
    memory_type: MemoryType = MemoryType.EPISODIC
    importance_score: float = 0.5
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    decay_rate: float = 0.01
    tags: list[str] = field(default_factory=list)
    source: str = ""
    linked_memories: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "embedding": self.embedding,
            "memory_type": self.memory_type.value,
            "importance_score": self.importance_score,
            "created_at": self.created_at.isoformat(),
            "last_accessed_at": self.last_accessed_at.isoformat(),
            "access_count": self.access_count,
            "decay_rate": self.decay_rate,
            "tags": self.tags,
            "source": self.source,
            "linked_memories": self.linked_memories,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Memory:
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            content=d.get("content", ""),
            embedding=d.get("embedding"),
            memory_type=MemoryType(d.get("memory_type", "episodic")),
            importance_score=d.get("importance_score", 0.5),
            created_at=datetime.fromisoformat(d["created_at"])
            if isinstance(d.get("created_at"), str)
            else d.get("created_at", datetime.utcnow()),
            last_accessed_at=datetime.fromisoformat(d["last_accessed_at"])
            if isinstance(d.get("last_accessed_at"), str)
            else d.get("last_accessed_at", datetime.utcnow()),
            access_count=d.get("access_count", 0),
            decay_rate=d.get("decay_rate", 0.01),
            tags=d.get("tags", []),
            source=d.get("source", ""),
            linked_memories=d.get("linked_memories", []),
        )
