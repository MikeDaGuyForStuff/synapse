"""Memory data types — hierarchical memory with compression layers.

SYNAPSE never forgets. Instead, memories are progressively compressed
through 4 layers, from raw verbatim storage up to stable identity knowledge.
"""

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


class MemoryLayer(str, Enum):
    """Compression hierarchy — higher layers = more compressed, more stable.

    Memories never get deleted. They get promoted through layers as they age,
    becoming smaller, more abstract representations of the original data.
    """

    RAW = "raw"  # verbatim — what was actually said/happened
    COMPRESSED = "compressed"  # summarized — multiple raw memories condensed
    KNOWLEDGE = "knowledge"  # extracted patterns — facts spanning many memories
    IDENTITY = "identity"  # stable user model — rarely changes


@dataclass
class Memory:
    """A single memory object stored and retrieved by the engine.

    Every memory has a layer in the compression hierarchy.
    No memory is ever deleted — it only moves up through layers.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    embedding: Optional[list[float]] = None
    memory_type: MemoryType = MemoryType.EPISODIC
    layer: MemoryLayer = MemoryLayer.RAW
    importance_score: float = 0.5
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    tags: list[str] = field(default_factory=list)
    source: str = ""
    linked_memories: list[str] = field(default_factory=list)
    compressed_from: list[str] = field(default_factory=list)  # ids of source memories (for COMPRESSED+)
    parent_id: Optional[str] = None  # if this is a compressed version, link to parent summary

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "embedding": self.embedding,
            "memory_type": self.memory_type.value,
            "layer": self.layer.value,
            "importance_score": self.importance_score,
            "created_at": self.created_at.isoformat(),
            "last_accessed_at": self.last_accessed_at.isoformat(),
            "access_count": self.access_count,
            "tags": self.tags,
            "source": self.source,
            "linked_memories": self.linked_memories,
            "compressed_from": self.compressed_from,
            "parent_id": self.parent_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Memory:
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            content=d.get("content", ""),
            embedding=d.get("embedding"),
            memory_type=MemoryType(d.get("memory_type", "episodic")),
            layer=MemoryLayer(d.get("layer", "raw")),
            importance_score=d.get("importance_score", 0.5),
            created_at=datetime.fromisoformat(d["created_at"])
            if isinstance(d.get("created_at"), str)
            else d.get("created_at", datetime.utcnow()),
            last_accessed_at=datetime.fromisoformat(d["last_accessed_at"])
            if isinstance(d.get("last_accessed_at"), str)
            else d.get("last_accessed_at", datetime.utcnow()),
            access_count=d.get("access_count", 0),
            tags=d.get("tags", []),
            source=d.get("source", ""),
            linked_memories=d.get("linked_memories", []),
            compressed_from=d.get("compressed_from", []),
            parent_id=d.get("parent_id"),
        )