"""Importance scoring heuristics — the secret sauce that decides what matters."""

from __future__ import annotations

import re

from synapse.types import Memory, MemoryType

# Regex for named entities (simple heuristic — detects capitalized words,
# common name patterns, and known entity structures)
_NAMED_ENTITY_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\b"
)

# Words/phrases that indicate user preferences or instructions
_PREFERENCE_PATTERNS = re.compile(
    r"\b(i\s+(like|prefer|want|need|love|hate|don'?t)\s|\b(my|mine|i'm|i am)\b"
    r"|\b(always|never|usually|whenever)\b"
    r"|\b(remember|important|note\s+that|please\s+(don'?t|do))\b)",
    re.IGNORECASE,
)

# Default tunable weights — expose these as config
SCORE_WEIGHTS = {
    "named_entity_bonus": 0.2,
    "preference_bonus": 0.15,
    "connectivity_bonus": 0.1,
    "access_frequency_bonus": 0.1,
    "decay_penalty_per_30_days": 0.1,
    "contradiction_penalty": 0.2,
    "base_score": 0.5,
}


class ImportanceScorer:
    """Scores a memory's importance on 0.0–1.0 using heuristics.

    The weights are exposed so users can tune them for their use case.
    """

    def __init__(self, weights: dict | None = None):
        self.weights = {**SCORE_WEIGHTS, **(weights or {})}

    def score(self, memory: Memory, linked_count: int = 0) -> float:
        """Compute importance_score for a memory.

        Args:
            memory: The memory to score.
            linked_count: Number of other memories linked to this one.
        """
        w = self.weights
        score = w["base_score"]

        # Named entity bonus
        if _NAMED_ENTITY_RE.search(memory.content):
            score += w["named_entity_bonus"]

        # Preference/instruction bonus
        if _PREFERENCE_PATTERNS.search(memory.content):
            score += w["preference_bonus"]

        # Connectivity bonus — well-connected memories matter more
        if linked_count >= 3:
            score += w["connectivity_bonus"]

        # Access frequency bonus
        if memory.access_count >= 5:
            score += w["access_frequency_bonus"]

        # Decay penalty based on days since last access
        days_since = self._days_since(memory)
        penalty = (days_since / 30) * w["decay_penalty_per_30_days"]
        score -= penalty

        return max(0.0, min(1.0, score))

    def detect_memory_type(self, content: str) -> MemoryType:
        """Auto-detect memory type from content using heuristics."""
        # Procedural — how-to, instructions, preferences
        procedural_patterns = [
            r"\b(prefer|always|never|when|customarily|usually)\w*\b",
            r"\b(don'?t|do\s+not)\b",
            r"\b(how\s+to|steps?|way\s+to|method)\b",
        ]
        for pat in procedural_patterns:
            if re.search(pat, content, re.IGNORECASE):
                return MemoryType.PROCEDURAL

        # Semantic — factual statements about identity, world knowledge
        semantic_patterns = [
            r"\b(is\s+a|works\s+as|studies|lives\s+in)\b",
            r"\b(name\s+is|called|known\s+as)\b",
            r"\b(fact:|reminder:)\b",
            r"\b(https?://|github\.com|twitter\.com)\b",
        ]
        for pat in semantic_patterns:
            if re.search(pat, content, re.IGNORECASE):
                return MemoryType.SEMANTIC

        # Default to episodic
        return MemoryType.EPISODIC

    @staticmethod
    def _days_since(memory: Memory) -> float:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        if memory.last_accessed_at.tzinfo is None:
            from datetime import timezone as tz

            last = memory.last_accessed_at.replace(tzinfo=tz.utc)
        else:
            last = memory.last_accessed_at
        return max(0.0, (now - last).total_seconds() / 86400.0)