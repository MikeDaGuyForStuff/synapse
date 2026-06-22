"""Tests for the memory store (SQLite layer)."""

import os
import tempfile
from pathlib import Path

from synapse.store import MemoryStore
from synapse.types import Memory, MemoryType, MemoryLayer


class TestMemoryStore:
    def setup_method(self):
        self.tmp = tempfile.mktemp(suffix=".db")
        self.store = MemoryStore(self.tmp)

    def teardown_method(self):
        self.store.close()
        os.unlink(self.tmp)

    def test_insert_and_get(self):
        m = Memory(content="hello world", tags=["test"])
        mid = self.store.insert(m)
        retrieved = self.store.get(mid)
        assert retrieved is not None
        assert retrieved.content == "hello world"
        assert retrieved.tags == ["test"]
        assert retrieved.id == mid
        assert retrieved.layer == MemoryLayer.RAW

    def test_update(self):
        m = Memory(content="original")
        mid = self.store.insert(m)
        m = self.store.get(mid)
        m.content = "updated"
        m.importance_score = 0.9
        self.store.update(m)
        updated = self.store.get(mid)
        assert updated.content == "updated"
        assert updated.importance_score == 0.9

    def test_count_and_all(self):
        assert self.store.count() == 0
        self.store.insert(Memory(content="a"))
        self.store.insert(Memory(content="b"))
        assert self.store.count() == 2
        assert len(self.store.all()) == 2

    def test_count_by_layer(self):
        self.store.insert(Memory(content="raw mem"))
        self.store.insert(Memory(content="compressed mem", layer=MemoryLayer.COMPRESSED))
        layers = self.store.count_by_layer()
        assert layers.get("raw", 0) >= 1
        assert layers.get("compressed", 0) >= 1

    def test_count_by_type(self):
        self.store.insert(Memory(content="ep", memory_type=MemoryType.EPISODIC))
        self.store.insert(Memory(content="sem", memory_type=MemoryType.SEMANTIC))
        types = self.store.count_by_type()
        assert types.get("episodic", 0) >= 1
        assert types.get("semantic", 0) >= 1

    def test_filter_by_layer(self):
        self.store.insert(Memory(content="r1"))
        self.store.insert(Memory(content="r2"))
        c = Memory(content="c1", layer=MemoryLayer.COMPRESSED)
        self.store.insert(c)
        raw = self.store.all(layer=MemoryLayer.RAW)
        compressed = self.store.all(layer=MemoryLayer.COMPRESSED)
        assert len(raw) >= 2
        assert len(compressed) >= 1

    def test_compressed_from_and_parent(self):
        m = Memory(content="child", compressed_from=["a", "b"], parent_id="parent123")
        mid = self.store.insert(m)
        retrieved = self.store.get(mid)
        assert retrieved.compressed_from == ["a", "b"]
        assert retrieved.parent_id == "parent123"