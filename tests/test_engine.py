"""Tests for the memory engine (store, retrieve, consolidate, forget, reflect)."""

import os
import tempfile

from synapse.engine import MemoryEngine
from synapse.store import MemoryStore
from synapse.types import MemoryType


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

    def test_store_with_tags_and_source(self):
        mid = self.engine.store("hello", source="test", tags=["greeting", "test"])
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

    def test_retrieve(self):
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

    def test_consolidate_merges_and_promotes(self):
        self.engine.store("Mike loves AI")
        self.engine.store("Mike loves AI infrastructure")
        self.engine.store("Mike loves building AI tools")

        stats = self.engine.consolidate()
        assert stats["before_count"] >= 3
        assert isinstance(stats["merged"], int)
        assert isinstance(stats["promoted"], int)
        assert stats["after_count"] <= stats["before_count"]

    def test_forget(self):
        self.engine.store("this is very important", tags=["test"])
        forgotten = self.engine.forget(threshold=0.0)
        # With threshold 0, no memories should be forgotten
        assert forgotten == 0

    def test_reflect_with_results(self):
        self.engine.store("The user Mike is building a memory engine")
        self.engine.store("Mike prefers Python for backend work")
        self.engine.store("The project is open source")

        ref = self.engine.reflect("Mike")
        assert ref["has_memories"] is True
        assert ref["memory_count"] > 0
        assert "<memory_context" in ref["context_block"]

    def test_reflect_with_no_results(self):
        ref = self.engine.reflect("xyznonexistent1234")
        assert ref["has_memories"] is False