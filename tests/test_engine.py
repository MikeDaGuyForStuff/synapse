"""Tests for the memory engine — store, retrieve, compress, extract, context."""

import os
import tempfile

from synapse.engine import MemoryEngine
from synapse.store import MemoryStore
from synapse.types import MemoryType, MemoryLayer


class TestMemoryEngine:
    def setup_method(self):
        self.tmp = tempfile.mktemp(suffix=".db")
        self.store = MemoryStore(self.tmp)
        self.engine = MemoryEngine(store=self.store)

    def teardown_method(self):
        self.engine._store.close()
        os.unlink(self.tmp)

    def test_store_returns_id(self):
        mid = self.engine.store("test memory")
        assert len(mid) > 0
        assert self.engine._store.count() == 1

    def test_store_sets_layer_to_raw(self):
        mid = self.engine.store("new memory")
        mem = self.engine._store.get(mid)
        assert mem.layer == MemoryLayer.RAW

    def test_store_with_tags_and_source(self):
        mid = self.engine.store("hello", source="test", tags=["greeting"])
        mem = self.engine._store.get(mid)
        assert mem.source == "test"
        assert "greeting" in mem.tags

    def test_store_detects_type(self):
        mid = self.engine.store("User prefers dark mode")
        mem = self.engine._store.get(mid)
        assert mem.memory_type == MemoryType.PROCEDURAL

        mid2 = self.engine.store("User is a developer who works on AI")
        mem2 = self.engine._store.get(mid2)
        assert mem2.memory_type == MemoryType.SEMANTIC

    def test_retrieve_returns_results(self):
        self.engine.store("Mike loves building AI infrastructure")
        self.engine.store("The weather today is sunny")

        results = self.engine.retrieve("Mike", top_k=5)
        assert len(results) >= 1
        assert results[0]["combined_score"] > 0

    def test_retrieve_populates_access_stats(self):
        mid = self.engine.store("test access tracking")
        self.engine.retrieve("test access tracking", top_k=5)
        mem = self.engine._store.get(mid)
        assert mem.access_count == 1

    def test_retrieve_includes_layer_info(self):
        self.engine.store("test layer tracking")
        results = self.engine.retrieve("test", top_k=5)
        assert "layer" in results[0]
        assert results[0]["layer"] == "raw"

    def test_compress(self):
        # Store many memories to trigger compression
        for i in range(10):
            self.engine.store(f"test memory number {i} about AI infrastructure development")
        stats = self.engine.compress(target_count=2)
        assert isinstance(stats["compressed_groups"], int)
        assert isinstance(stats["summaries_created"], int)

    def test_compress_preserves_originals(self):
        mids = []
        for i in range(8):
            mids.append(self.engine.store(f"memory {i} about machine learning"))
        before_count = self.engine._store.count()
        self.engine.compress(target_count=1)
        after_count = self.engine._store.count()
        # Total count should have INCREASED (original memories preserved + summaries added)
        assert after_count >= before_count

    def test_retrieves_from_all_layers(self):
        self.engine.store("raw layer memory")
        self.engine.store("another raw memory")
        self.engine.compress(target_count=3)
        results = self.engine.retrieve("memory", top_k=10)
        layers_used = set(r["layer"] for r in results)
        assert "raw" in layers_used

    def test_context_returns_formatted_block(self):
        self.engine.store("The user Mike is building a memory engine")
        self.engine.store("Mike prefers Python for backend work")
        ctx = self.engine.context("Mike")
        assert ctx["has_memories"] is True
        assert ctx["total_memories_found"] > 0
        assert "<memory_context" in ctx["context_block"]
        assert "token_estimate" in ctx

    def test_context_with_no_memories(self):
        ctx = self.engine.context("xyznonexistent")
        assert ctx["has_memories"] is False

    def test_memories_never_deleted(self):
        self.engine.store("this memory should persist forever")
        count_before = self.engine._store.count()
        self.engine.compress()
        self.engine.extract()
        count_after = self.engine._store.count()
        # Total should never decrease (no forget())
        assert count_after >= count_before

    def test_layer_stats(self):
        self.engine.store("raw memory one")
        self.engine.store("raw memory two")
        raw_count = self.engine._store.count(layer=MemoryLayer.RAW)
        assert raw_count >= 2