"""Layer 2: The Memory Engine — store, retrieve, consolidate, forget, reflect."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import numpy as np

from synapse.store import MemoryStore
from synapse.types import Memory, MemoryType
from synapse.embeddings import EmbeddingProvider
from synapse.importance import ImportanceScorer
from synapse.decay import DecayEngine

logger = logging.getLogger("synapse.engine")


class MemoryEngine:
    """The core brain of SYNAPSE.

    Decides what to remember, how to retrieve, when to consolidate,
    what to forget, and how to reflect on what it knows.
    """

    def __init__(
        self,
        store: Optional[MemoryStore] = None,
        embedder: Optional[EmbeddingProvider] = None,
        scorer: Optional[ImportanceScorer] = None,
        decay: Optional[DecayEngine] = None,
    ):
        self._store = store or MemoryStore()
        self.embedder = embedder or EmbeddingProvider()
        self.scorer = scorer or ImportanceScorer()
        self.decay = decay or DecayEngine()

    # ------------------------------------------------------------------
    # 1. STORE
    # ------------------------------------------------------------------

    def store(
        self,
        content: str,
        source: str = "",
        tags: list[str] | None = None,
        memory_type: Optional[MemoryType] = None,
    ) -> str:
        """Store a new memory.

        Automatically generates embedding, scores importance,
        detects memory type, and links to related memories.
        """
        # Generate embedding
        embedding = self.embedder.embed(content)

        # Detect memory type
        if memory_type is None:
            memory_type = self.scorer.detect_memory_type(content)

        # Build initial memory
        memory = Memory(
            content=content,
            embedding=embedding,
            memory_type=memory_type,
            created_at=datetime.now(timezone.utc),
            last_accessed_at=datetime.now(timezone.utc),
            tags=tags or [],
            source=source,
            decay_rate=self.decay.rates.get(memory_type, 0.01),
        )

        # Score importance
        memory.importance_score = self.scorer.score(memory)

        # Link to related memories
        if embedding:
            related = self._find_similar(embedding, top_k=5, min_similarity=0.5)
            memory.linked_memories = [m.id for m in related]

        # Persist
        memory_id = self._store.insert(memory)

        # Update links bidirectionally
        for related_mem in related:
            rel = self._store.get(related_mem.id)
            if rel and memory_id not in rel.linked_memories:
                rel.linked_memories.append(memory_id)
                rel.linked_memories = rel.linked_memories[:20]  # cap
                self._store.update(rel)

        logger.info(
            "Stored memory %s (type=%s, importance=%.2f, links=%d)",
            memory_id,
            memory_type.value,
            memory.importance_score,
            len(related),
        )
        return memory_id

    # ------------------------------------------------------------------
    # 2. RETRIEVE
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        memory_type: Optional[MemoryType] = None,
        min_score: float = 0.0,
    ) -> list[dict]:
        """Retrieve memories relevant to a query.

        Uses vector similarity + re-ranking by importance/recency/frequency.
        Returns ranked list of dicts with memory data and relevance score.
        """
        query_emb = self.embedder.embed(query)

        # Get all candidates via vector similarity
        candidates = self._find_similar(query_emb, top_k=top_k * 3)

        # Filter by type
        if memory_type:
            candidates = [m for m in candidates if m.memory_type == memory_type]

        # Re-rank by combined score
        scored = []
        for mem in candidates:
            sim = self.embedder.cosine_similarity(query_emb, mem.embedding or [])
            effective_imp = self.decay.effective_importance(mem)
            recency_bonus = self._recency_bonus(mem)
            combined = (
                0.4 * sim
                + 0.3 * effective_imp
                + 0.2 * recency_bonus
                + 0.1 * min(mem.access_count / 10, 1.0)
            )
            if combined >= min_score:
                scored.append(
                    {
                        "memory": mem.to_dict(),
                        "relevance_score": round(sim, 4),
                        "combined_score": round(combined, 4),
                    }
                )

        # Sort by combined score
        scored.sort(key=lambda x: x["combined_score"], reverse=True)

        # Update access stats for retrieved memories
        retrieved_ids = [item["memory"]["id"] for item in scored[:top_k]]
        for mem_id in retrieved_ids:
            mem = self._store.get(mem_id)
            if mem:
                mem.access_count += 1
                mem.last_accessed_at = datetime.now(timezone.utc)
                self._store.update(mem)

        return scored[:top_k]

    # ------------------------------------------------------------------
    # 3. CONSOLIDATE
    # ------------------------------------------------------------------

    def consolidate(self) -> dict:
        """Run consolidation — merge duplicates, promote frequent, decay old, extract facts.

        This is the self-organizing step that makes SYNAPSE different.
        """
        stats = {
            "merged": 0,
            "promoted": 0,
            "decayed": 0,
            "extracted_facts": 0,
            "before_count": self._store.count(),
        }

        all_memories = self._store.all()

        # Phase 1: Merge near-duplicates
        merged_ids = set()
        for i, m1 in enumerate(all_memories):
            if m1.id in merged_ids:
                continue
            for m2 in all_memories[i + 1 :]:
                if m2.id in merged_ids:
                    continue
                if self._is_duplicate(m1, m2):
                    self._merge_memories(m1, m2)
                    merged_ids.add(m2.id)
                    stats["merged"] += 1

        # Phase 2: Promote frequently accessed memories
        for mem in self._store.all():
            if mem.access_count >= 5 and mem.importance_score < 0.8:
                mem.importance_score = min(1.0, mem.importance_score + 0.1)
                self._store.update(mem)
                stats["promoted"] += 1

        # Phase 3: Apply decay to all memories
        for mem in self._store.all():
            faded = self.decay.effective_importance(mem)
            if faded < mem.importance_score:
                mem.importance_score = faded
                self._store.update(mem)
                stats["decayed"] += 1

        # Phase 4: Extract semantic facts from episodic clusters
        episodic = [m for m in self._store.all() if m.memory_type == MemoryType.EPISODIC]
        semantic = [m for m in self._store.all() if m.memory_type == MemoryType.SEMANTIC]
        for ep in episodic:
            # If an episodic memory has been accessed many times,
            # extract it as a semantic fact
            if ep.access_count >= 3 and not self._has_similar_fact(ep, semantic):
                fact_memory = Memory(
                    content=ep.content,
                    embedding=ep.embedding,
                    memory_type=MemoryType.SEMANTIC,
                    importance_score=ep.importance_score * 0.9,
                    tags=ep.tags + ["extracted"],
                    source="consolidation",
                    linked_memories=[ep.id],
                )
                self._store.insert(fact_memory)
                stats["extracted_facts"] += 1
                semantic.append(fact_memory)

        # Clean up merged memories
        for mid in merged_ids:
            self._store.delete(mid)

        stats["after_count"] = self._store.count()
        logger.info("Consolidation complete: %s", stats)
        return stats

    # ------------------------------------------------------------------
    # 4. FORGET
    # ------------------------------------------------------------------

    def forget(self, threshold: float = 0.1) -> int:
        """Delete memories whose importance has decayed below threshold.

        Returns number of memories forgotten.
        """
        count = 0
        for mem in self._store.all():
            if self.decay.should_forget(mem, threshold):
                self._store.delete(mem.id)
                count += 1
        if count > 0:
            logger.info("Forgot %d memories (threshold=%.2f)", count, threshold)
        return count

    # ------------------------------------------------------------------
    # 5. REFLECT
    # ------------------------------------------------------------------

    def reflect(self, topic: str, top_k: int = 15) -> dict:
        """Synthesize memories about a topic into a coherent summary.

        Returns a rich context block ready to inject into any AI prompt.
        """
        memories = self.retrieve(topic, top_k=top_k, min_score=0.2)

        if not memories:
            return {
                "topic": topic,
                "has_memories": False,
                "summary": f"No memories found about '{topic}'.",
                "context_block": "",
                "memories": [],
            }

        # Organize by type
        episodic = []
        semantic = []
        procedural = []
        for item in memories:
            m = item["memory"]
            if m["memory_type"] == "episodic":
                episodic.append(m)
            elif m["memory_type"] == "semantic":
                semantic.append(m)
            else:
                procedural.append(m)

        # Build structured context block
        lines = [f"<memory_context topic=\"{topic}\">"]

        if semantic:
            lines.append("  <facts>")
            for m in semantic[:5]:
                lines.append(f"    <fact importance=\"{m['importance_score']:.2f}\">{m['content']}</fact>")
            lines.append("  </facts>")

        if episodic:
            lines.append("  <events>")
            for m in episodic[:5]:
                lines.append(f"    <event date=\"{m['created_at'][:10]}\">{m['content']}</event>")
            lines.append("  </events>")

        if procedural:
            lines.append("  <preferences>")
            for m in procedural[:3]:
                lines.append(f"    <preference>{m['content']}</preference>")
            lines.append("  </preferences>")

        lines.append("</memory_context>")

        return {
            "topic": topic,
            "has_memories": True,
            "memory_count": len(memories),
            "summary": f"Found {len(memories)} memories about '{topic}' "
            f"({len(semantic)} facts, {len(episodic)} events, {len(procedural)} preferences).",
            "context_block": "\n".join(lines),
            "memories": [m["memory"] for m in memories],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_similar(
        self,
        query_emb: list[float],
        top_k: int = 10,
        min_similarity: float = 0.0,
    ) -> list[Memory]:
        """Find memories with embeddings similar to the query vector."""
        all_embeddings = self._store.get_all_embeddings()
        if not all_embeddings:
            return []

        similarities = []
        for mem_id, emb in all_embeddings:
            sim = self.embedder.cosine_similarity(query_emb, emb)
            if sim >= min_similarity:
                similarities.append((sim, mem_id))

        similarities.sort(key=lambda x: x[0], reverse=True)
        top_ids = [sid for _, sid in similarities[:top_k]]
        return self._store.get_memories_by_ids(top_ids)

    def _is_duplicate(self, m1: Memory, m2: Memory, threshold: float = 0.88) -> bool:
        """Check if two memories are near-duplicates."""
        if m1.embedding and m2.embedding:
            sim = self.embedder.cosine_similarity(m1.embedding, m2.embedding)
            return sim >= threshold
        return m1.content.strip().lower() == m2.content.strip().lower()

    def _merge_memories(self, keep: Memory, remove: Memory):
        """Merge remove into keep — combine tags, boost importance, link histories."""
        keep.access_count += remove.access_count
        keep.importance_score = max(keep.importance_score, remove.importance_score)
        keep.tags = list(set(keep.tags + remove.tags))
        keep.linked_memories = list(
            set(keep.linked_memories + remove.linked_memories)
        )[:20]
        keep.last_accessed_at = max(keep.last_accessed_at, remove.last_accessed_at)
        self._store.update(keep)

    def _has_similar_fact(self, mem: Memory, facts: list[Memory], threshold: float = 0.85) -> bool:
        """Check if a semantic fact similar to mem already exists."""
        if not mem.embedding:
            return False
        for fact in facts:
            if fact.embedding:
                sim = self.embedder.cosine_similarity(mem.embedding, fact.embedding)
                if sim >= threshold:
                    return True
        return False

    @staticmethod
    def _recency_bonus(memory: Memory) -> float:
        """Compute recency score 0.0–1.0 (higher = more recent)."""
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)
        if memory.created_at.tzinfo is None:
            created = memory.created_at.replace(tzinfo=timezone.utc)
        else:
            created = memory.created_at
        days_old = max(0.0, (now - created).total_seconds() / 86400.0)
        return max(0.0, 1.0 - days_old / 90.0)  # Full recency bonus within 90 days