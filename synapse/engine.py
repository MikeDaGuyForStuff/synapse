"""The SYNAPSE Memory Engine.

Core philosophy: AI should NEVER forget. Memories are progressively
compressed through 4 layers — raw → compressed → knowledge → identity —
but NEVER deleted. The system gets smarter with more data.

5 operations:
1. store()     — store a new memory (always RAW at first)
2. retrieve()  — search ALL layers, return most relevant
3. compress()  — promote oldest/lowest-priority RAW → COMPRESSED summaries
4. extract()   — find patterns across COMPRESSED → KNOWLEDGE facts
5. context()   — generate optimal context block for any LLM query
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from synapse.store import MemoryStore
from synapse.types import Memory, MemoryType, MemoryLayer
from synapse.embeddings import EmbeddingProvider
from synapse.importance import ImportanceScorer
from synapse.decay import CompressionScheduler

logger = logging.getLogger("synapse.engine")


class MemoryEngine:
    """The core brain of SYNAPSE.

    Stores everything forever. Compresses progressively.
    Retrieves across all layers. Never forgets.
    """

    def __init__(
        self,
        store: Optional[MemoryStore] = None,
        embedder: Optional[EmbeddingProvider] = None,
        scorer: Optional[ImportanceScorer] = None,
        scheduler: Optional[CompressionScheduler] = None,
    ):
        self._store = store or MemoryStore()
        self.embedder = embedder or EmbeddingProvider()
        self.scorer = scorer or ImportanceScorer()
        self.scheduler = scheduler or CompressionScheduler()

    # ------------------------------------------------------------------
    # 1. STORE — everything starts as RAW
    # ------------------------------------------------------------------

    def store(
        self,
        content: str,
        source: str = "",
        tags: list[str] | None = None,
        memory_type: Optional[MemoryType] = None,
    ) -> str:
        """Store a new memory.

        All new memories enter at the RAW layer.
        They are never deleted — only promoted through compression.
        """
        embedding = self.embedder.embed(content)

        if memory_type is None:
            memory_type = self.scorer.detect_memory_type(content)

        memory = Memory(
            content=content,
            embedding=embedding,
            memory_type=memory_type,
            layer=MemoryLayer.RAW,
            created_at=datetime.now(timezone.utc),
            last_accessed_at=datetime.now(timezone.utc),
            tags=tags or [],
            source=source,
        )

        memory.importance_score = self.scorer.score(memory)
        memory_id = self._store.insert(memory)

        # Link to related memories
        if embedding:
            related = self._find_similar(embedding, top_k=5, min_similarity=0.4)
            mem = self._store.get(memory_id)
            if mem:
                mem.linked_memories = [m.id for m in related]
                self._store.update(mem)
                for rel in related:
                    r = self._store.get(rel.id)
                    if r and memory_id not in r.linked_memories:
                        r.linked_memories.append(memory_id)
                        r.linked_memories = r.linked_memories[:30]
                        self._store.update(r)

        logger.info(
            "Stored %s [%s] (importance=%.2f, links=%d)",
            memory_id[:8],
            memory_type.value,
            memory.importance_score,
            len(related) if embedding else 0,
        )
        return memory_id

    # ------------------------------------------------------------------
    # 2. RETRIEVE — search ALL layers, raw → compressed → knowledge
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        memory_type: Optional[MemoryType] = None,
        min_score: float = 0.0,
        include_layers: Optional[list[MemoryLayer]] = None,
    ) -> list[dict]:
        """Retrieve memories relevant to a query.

        Searches across ALL layers by default.
        Higher layers (knowledge, identity) are boosted because they
        represent more distilled, reliable information.
        """
        query_emb = self.embedder.embed(query)

        # Search all layers unless specified
        layers = include_layers or [
            MemoryLayer.RAW,
            MemoryLayer.COMPRESSED,
            MemoryLayer.KNOWLEDGE,
            MemoryLayer.IDENTITY,
        ]

        candidates = []
        for layer in layers:
            candidates.extend(self._find_similar(
                query_emb,
                top_k=top_k,
                layer=layer,
            ))

        # Filter by type
        if memory_type:
            candidates = [m for m in candidates if m.memory_type == memory_type]

        # De-duplicate by content similarity
        seen_content = set()
        deduped = []
        for m in candidates:
            # Use embedding similarity to avoid near-duplicates
            if m.embedding:
                is_dup = False
                for existing in deduped:
                    if existing.embedding:
                        sim = self.embedder.cosine_similarity(m.embedding, existing.embedding)
                        if sim > 0.92:
                            is_dup = True
                            break
                if not is_dup:
                    deduped.append(m)
            else:
                if m.content not in seen_content:
                    seen_content.add(m.content)
                    deduped.append(m)

        # Layer boost: higher layers get a relevance bump
        layer_boost = {
            MemoryLayer.RAW: 0.0,
            MemoryLayer.COMPRESSED: 0.15,
            MemoryLayer.KNOWLEDGE: 0.3,
            MemoryLayer.IDENTITY: 0.5,
        }

        # Score and rank
        scored = []
        for mem in deduped:
            sim = self.embedder.cosine_similarity(query_emb, mem.embedding or [])
            boost = layer_boost.get(mem.layer, 0.0)
            recency = self._recency_bonus(mem)
            combined = (
                0.35 * sim
                + 0.25 * mem.importance_score
                + 0.15 * recency
                + 0.15 * boost
                + 0.10 * min(mem.access_count / 10, 1.0)
            )
            if combined >= min_score:
                scored.append({
                    "memory": mem.to_dict(),
                    "relevance_score": round(sim, 4),
                    "combined_score": round(combined, 4),
                    "layer": mem.layer.value,
                })

        scored.sort(key=lambda x: x["combined_score"], reverse=True)

        # Update access stats
        for item in scored[:top_k]:
            mem = self._store.get(item["memory"]["id"])
            if mem:
                mem.access_count += 1
                mem.last_accessed_at = datetime.now(timezone.utc)
                self._store.update(mem)

        return scored[:top_k]

    # ------------------------------------------------------------------
    # 3. COMPRESS — promote RAW → COMPRESSED summaries
    # ------------------------------------------------------------------

    def compress(self, target_count: int = 10) -> dict:
        """Compress the oldest/lowest-priority RAW memories into summaries.

        Instead of forgetting, we bundle similar/old RAW memories
        into a single COMPRESSED summary. The original RAW memories
        are preserved but marked as compressed.

        This is the progressive compression step.
        """
        stats = {
            "compressed_groups": 0,
            "raw_memories_compressed": 0,
            "summaries_created": 0,
        }

        # Get candidates for compression
        candidates = self._store.get_candidates_for_compression(max_count=50)

        if len(candidates) < 5:
            logger.info("Not enough RAW memories for compression (%d)", len(candidates))
            return stats

        # Rank by compression priority
        ranked = self.scheduler.rank_for_compression(candidates, top_k=30)

        if not ranked:
            return stats

        # Group similar memories by embedding similarity
        groups = self._cluster_by_similarity(ranked, similarity_threshold=0.6)

        for group in groups[:target_count]:
            if len(group) < 3:
                continue  # skip tiny groups

            # Create compressed summary
            summary = self._generate_summary(group)
            source_ids = [m.id for m in group]

            compressed_memory = Memory(
                content=summary,
                memory_type=self._dominant_type(group),
                layer=MemoryLayer.COMPRESSED,
                importance_score=min(
                    1.0,
                    sum(m.importance_score for m in group) / len(group) * 1.2,
                ),
                tags=list(set(t for m in group for t in m.tags)),
                source="compression",
                compressed_from=source_ids,
                linked_memories=[m.id for m in group[:10]],
            )
            compressed_memory.embedding = self.embedder.embed(summary)
            summary_id = self._store.insert(compressed_memory)

            # Update original memories to point to parent
            for m in group:
                m.parent_id = summary_id
                m.tags = list(set(m.tags + ["compressed"]))
                self._store.update(m)

            stats["compressed_groups"] += 1
            stats["raw_memories_compressed"] += len(group)
            stats["summaries_created"] += 1

        logger.info(
            "Compression complete: %d groups, %d memories → %d summaries",
            stats["compressed_groups"],
            stats["raw_memories_compressed"],
            stats["summaries_created"],
        )
        return stats

    # ------------------------------------------------------------------
    # 4. EXTRACT — find patterns across COMPRESSED → KNOWLEDGE
    # ------------------------------------------------------------------

    def extract(self) -> dict:
        """Find patterns across COMPRESSED memories extract KNOWLEDGE.

        When multiple COMPRESSED summaries cover the same topic,
        extract a higher-level KNOWLEDGE fact from them.
        """
        stats = {"extracted": 0}

        compressed = self._store.all(layer=MemoryLayer.COMPRESSED, limit=100)
        knowledge = self._store.all(layer=MemoryLayer.KNOWLEDGE, limit=100)

        if len(compressed) < 3:
            logger.info("Not enough COMPRESSED memories for extraction (%d)", len(compressed))
            return stats

        # Find clusters among compressed memories
        groups = self._cluster_by_similarity(compressed, similarity_threshold=0.65)

        for group in groups:
            if len(group) < 3:
                continue

            # Check if we already have knowledge about this topic
            topic_emb = self.embedder.embed(group[0].content[:100])
            already_known = False
            for k in knowledge:
                if k.embedding:
                    sim = self.embedder.cosine_similarity(topic_emb, k.embedding)
                    if sim > 0.8:
                        already_known = True
                        break
            if already_known:
                continue

            # Extract a knowledge fact
            knowledge_text = self._extract_knowledge(group)
            source_ids = [m.id for m in group]

            knowledge_memory = Memory(
                content=knowledge_text,
                memory_type=MemoryType.SEMANTIC,
                layer=MemoryLayer.KNOWLEDGE,
                importance_score=min(1.0, 0.5 + len(group) * 0.05),
                tags=list(set(t for m in group for t in m.tags if t not in ["compressed"])),
                source="extraction",
                compressed_from=source_ids,
            )
            knowledge_memory.embedding = self.embedder.embed(knowledge_text)
            self._store.insert(knowledge_memory)
            stats["extracted"] += 1

        logger.info("Extracted %d knowledge facts", stats["extracted"])
        return stats

    # ------------------------------------------------------------------
    # 5. CONTEXT — generate optimal context for any LLM
    # ------------------------------------------------------------------

    def context(self, query: str, max_tokens: int = 4000) -> dict:
        """Generate an optimal context block for an LLM.

        This is the key integration point. Instead of stuffing all
        memories into a prompt, SYNAPSE intelligently selects and
        formats the most relevant memories from ALL layers,
        optimized to fit within an LLM's context window.

        Returns a ready-to-inject context block with metadata.
        """
        # Retrieve from all layers
        results = self.retrieve(query, top_k=20, min_score=0.1)

        if not results:
            return {
                "query": query,
                "has_memories": False,
                "context_block": "",
                "token_estimate": 0,
                "layers_used": [],
            }

        # Organize by layer
        by_layer = {"raw": [], "compressed": [], "knowledge": [], "identity": []}
        for item in results:
            layer = item.get("layer", "raw")
            if layer in by_layer:
                by_layer[layer].append(item)

        # Build context block — highest layers first
        lines = [f'<memory_context query="{query}">']

        # Identity facts (most distilled)
        if by_layer["identity"]:
            lines.append("  <identity>")
            for item in by_layer["identity"][:3]:
                m = item["memory"]
                lines.append(f'    <fact importance="{m["importance_score"]:.2f}">{m["content"]}</fact>')
            lines.append("  </identity>")

        # Knowledge facts
        if by_layer["knowledge"]:
            lines.append("  <knowledge>")
            for item in by_layer["knowledge"][:5]:
                m = item["memory"]
                lines.append(f'    <fact importance="{m["importance_score"]:.2f}">{m["content"]}</fact>')
            lines.append("  </knowledge>")

        # Compressed summaries
        if by_layer["compressed"]:
            lines.append("  <summaries>")
            for item in by_layer["compressed"][:5]:
                m = item["memory"]
                lines.append(f'    <summary>{m["content"]}</summary>')
            lines.append("  </summaries>")

        # Recent raw memories
        if by_layer["raw"]:
            lines.append("  <recent>")
            for item in by_layer["raw"][:7]:
                m = item["memory"]
                lines.append(f'    <memory date="{m["created_at"][:10]}">{m["content"]}</memory>')
            lines.append("  </recent>")

        lines.append("</memory_context>")
        context_block = "\n".join(lines)

        # Rough token estimate (4 chars ≈ 1 token for English)
        token_estimate = len(context_block) // 4

        return {
            "query": query,
            "has_memories": True,
            "total_memories_found": len(results),
            "layers_used": [l for l, items in by_layer.items() if items],
            "layer_breakdown": {l: len(items) for l, items in by_layer.items()},
            "token_estimate": token_estimate,
            "fits_in_context": token_estimate <= max_tokens,
            "context_block": context_block,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_similar(
        self,
        query_emb: list[float],
        top_k: int = 10,
        min_similarity: float = 0.0,
        layer: Optional[MemoryLayer] = None,
    ) -> list[Memory]:
        """Find memories with embeddings similar to the query vector."""
        all_embeddings = self._store.get_all_embeddings(layer=layer)
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

    def _cluster_by_similarity(
        self,
        memories: list[Memory],
        similarity_threshold: float = 0.6,
    ) -> list[list[Memory]]:
        """Cluster memories by embedding similarity.

        Returns groups of related memories.
        """
        if not memories:
            return []

        clusters = []
        assigned = set()

        for i, m1 in enumerate(memories):
            if i in assigned:
                continue
            cluster = [m1]
            assigned.add(i)
            for j, m2 in enumerate(memories):
                if j in assigned:
                    continue
                if m1.embedding and m2.embedding:
                    sim = self.embedder.cosine_similarity(m1.embedding, m2.embedding)
                    if sim >= similarity_threshold:
                        cluster.append(m2)
                        assigned.add(j)
            clusters.append(cluster)

        # Sort clusters by size (largest first)
        clusters.sort(key=lambda c: len(c), reverse=True)
        return clusters

    def _generate_summary(self, memories: list[Memory]) -> str:
        """Generate a summary text from a group of related memories.

        Uses a template-based approach (no LLM call needed).
        """
        if len(memories) == 1:
            return memories[0].content

        # Extract key phrases from each memory
        topics = list(set(t for m in memories for t in m.tags if t not in ["compressed"]))
        topic_str = f" regarding {', '.join(topics[:3])}" if topics else ""

        # Type-based summary
        mtype = self._dominant_type(memories)
        if mtype == MemoryType.PROCEDURAL:
            prefix = "User preferences and patterns"
        elif mtype == MemoryType.SEMANTIC:
            prefix = "Key facts and information"
        else:
            prefix = "Recorded events and interactions"

        date_range = f" from {memories[-1].created_at.strftime('%b %d')} to {memories[0].created_at.strftime('%b %d')}"

        return f"{prefix}{topic_str}{date_range}: {len(memories)} related items stored."

    def _extract_knowledge(self, memories: list[Memory]) -> str:
        """Extract a knowledge fact from a cluster of compressed memories."""
        topics = list(set(t for m in memories for t in m.tags if t not in ["compressed"]))
        topic_str = f" about {', '.join(topics[:3])}" if topics else ""

        mtype = self._dominant_type(memories)
        if mtype == MemoryType.PROCEDURAL:
            return (
                f"Pattern identified{topic_str}: Based on {len(memories)} related observations, "
                f"the user demonstrates consistent preferences and behaviors in this area."
            )
        elif mtype == MemoryType.SEMANTIC:
            return (
                f"Established fact{topic_str}: Synthesized from {len(memories)} related pieces of "
                f"information that form a consistent picture."
            )
        else:
            return (
                f"Emerging pattern{topic_str}: {len(memories)} related events follow a "
                f"consistent trajectory and suggest an ongoing theme."
            )

    @staticmethod
    def _dominant_type(memories: list[Memory]) -> MemoryType:
        """Find the most common memory type in a list."""
        counts = {}
        for m in memories:
            counts[m.memory_type] = counts.get(m.memory_type, 0) + 1
        return max(counts, key=counts.get)

    @staticmethod
    def _recency_bonus(memory: Memory) -> float:
        """Compute recency score 0.0–1.0 (higher = more recent)."""
        days_old = max(0.0, (datetime.now(timezone.utc) - memory.created_at).total_seconds() / 86400.0)
        return max(0.0, 1.0 - days_old / 90.0)