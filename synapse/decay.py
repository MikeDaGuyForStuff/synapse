"""Compression scheduling — determines WHEN each memory should be compressed.

SYNAPSE never forgets. Instead, memories are prioritized for progressive
compression based on age, access frequency, and importance.

The compression priority formula determines which memories get
compressed (summarized) first, not which get deleted.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional

from synapse.types import Memory, MemoryLayer

# How long before a RAW memory is eligible for compression (days)
COMPRESSION_ELIGIBILITY_DAYS = {
    MemoryLayer.RAW: 7,  # raw memories compress after 7 days
    MemoryLayer.COMPRESSED: 30,  # compressed memories promote after 30 days
    MemoryLayer.KNOWLEDGE: 90,  # knowledge promotes to identity after 90 days
    MemoryLayer.IDENTITY: float("inf"),  # identity never promotes
}


class CompressionScheduler:
    """Decides which memories to compress next and how to prioritize.

    Priority is based on: age, access frequency, importance, and current layer.
    Higher priority = compressed sooner.
    """

    def __init__(self):
        self.eligibility_days = COMPRESSION_ELIGIBILITY_DAYS

    def compression_priority(self, memory: Memory) -> float:
        """Compute compression priority score (0.0–10.0).

        Higher score = more urgent to compress.
        Factors:
        - Age bonus: older memories get compressed first
        - Access penalty: frequently accessed memories are kept raw longer
        - Importance penalty: important memories stay at their current layer longer
        """
        days_old = self._days_since(memory.created_at)
        days_since_access = self._days_since(memory.last_accessed_at)

        # Age bonus: exponential ramp after eligibility
        eligibility = self.eligibility_days.get(memory.layer, 7)
        if days_old < eligibility:
            return 0.0  # not yet eligible
        age_bonus = min(5.0, (days_old - eligibility) / 7.0)  # +1 per week past eligibility

        # Access penalty: frequently accessed = lower compression priority
        access_penalty = min(3.0, memory.access_count * 0.5)

        # Importance penalty: important memories stay longer
        importance_penalty = memory.importance_score * 2.0

        score = age_bonus - access_penalty - importance_penalty
        return max(0.0, score)

    def is_eligible(self, memory: Memory) -> bool:
        """Check if a memory is eligible for compression based on its layer."""
        eligibility = self.eligibility_days.get(memory.layer, 7)
        if eligibility == float("inf"):
            return False
        days_old = self._days_since(memory.created_at)
        return days_old >= eligibility

    def rank_for_compression(self, memories: list[Memory], top_k: int = 20) -> list[Memory]:
        """Return the top_k memories most eligible for compression, sorted by priority."""
        scored = [(self.compression_priority(m), m) for m in memories]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for s, m in scored if s > 0][:top_k]

    def estimate_compression_ratio(self, memories: list[Memory]) -> float:
        """Estimate how much space compression would save (1.0 = 100% reduction).

        Rough heuristic: compressing N memories produces ~1 summary per ~5 memories,
        with each summary being ~20% the length.
        """
        if len(memories) <= 3:
            return 0.0
        avg_len = sum(len(m.content) for m in memories) / len(memories)
        summary_len = avg_len * 0.2
        compressed_count = max(1, len(memories) // 5)
        original = avg_len * len(memories)
        compressed = summary_len * compressed_count
        return 1.0 - (compressed / original)

    @staticmethod
    def _days_since(dt: datetime) -> float:
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0.0, (now - dt).total_seconds() / 86400.0)