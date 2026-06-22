"""SYNAPSE — Persistent Self-Organizing Memory for AI.

SYNAPSE never forgets. Memories are progressively compressed
through 4 layers — raw → compressed → knowledge → identity —
but NEVER deleted. The system gets smarter with more data.
"""

__version__ = "0.2.0"

from synapse.types import Memory, MemoryType, MemoryLayer
from synapse.store import MemoryStore
from synapse.embeddings import EmbeddingProvider
from synapse.importance import ImportanceScorer
from synapse.decay import CompressionScheduler
from synapse.engine import MemoryEngine

__all__ = [
    "Memory",
    "MemoryType",
    "MemoryLayer",
    "MemoryStore",
    "EmbeddingProvider",
    "ImportanceScorer",
    "CompressionScheduler",
    "MemoryEngine",
]