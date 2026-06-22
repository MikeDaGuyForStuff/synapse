"""Decay math — inspired by the Ebbinghaus Forgetting Curve.

current_importance = base_importance * e^(-decay_rate * days_since_access)

Different memory types decay at different rates, mirroring how human
memory naturally fades: procedural skills last longest, episodic details fade fastest.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from synapse.types import Memory, MemoryType

# Default decay rates per memory type (per day)
DEFAULT_DECAY_RATES = {
    MemoryType.EPISODIC: 0.01,  # fastest — event details fade
    MemoryType.SEMANTIC: 0.001,  # slower — facts persist
    MemoryType.PROCEDURAL: 0.0001,  # slowest — skills last longest
}


class DecayEngine:
    """Applies the forgetting curve to memories and computes effective importance."""

    def __init__(self, rates: dict | None = None):
        self.rates = {**DEFAULT_DECAY_RATES, **(rates or {})}

    def effective_importance(self, memory: Memory) -> float:
        """Compute current importance after decay.

        Uses the Ebbinghaus forgetting curve:
            current = base * e^(-decay_rate * days_since_access)
        """
        days = self._days_since(memory.last_accessed_at)
        rate = self.rates.get(memory.memory_type, memory.decay_rate)
        faded = memory.importance_score * math.exp(-rate * days)
        return max(0.0, min(1.0, faded))

    def should_forget(self, memory: Memory, threshold: float = 0.1) -> bool:
        """Check if a memory has decayed below the forget threshold."""
        return self.effective_importance(memory) < threshold

    def days_until_forget(self, memory: Memory, threshold: float = 0.1) -> float:
        """Calculate how many days until this memory crosses the forget threshold.

        Returns inf if already below threshold or if decay won't reach it.
        """
        current = self.effective_importance(memory)
        if current <= threshold:
            return 0.0

        rate = self.rates.get(memory.memory_type, memory.decay_rate)
        if rate <= 0:
            return float("inf")

        # Solve: threshold = current * e^(-rate * days)
        # days = -ln(threshold / current) / rate
        days = -math.log(threshold / current) / rate
        return max(0.0, days)

    @staticmethod
    def _days_since(dt: datetime) -> float:
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0.0, (now - dt).total_seconds() / 86400.0)