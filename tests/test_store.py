"""Tests for the memory store (SQLite layer)."""

import os
import tempfile
from pathlib import Path

from synapse.store import MemoryStore
from synapse.types import Memory, MemoryType


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

    def test_delete(self):
        m = Memory(content="to delete")
        mid = self.store.insert(m)
        assert self.store.delete(mid) is True
        assert self.store.get(mid) is None
        assert self.store.delete("nonexistent") is False

    def test_count_and_all(self):
        assert self.store.count() == 0
        self.store.insert(Memory(content="a"))
        self.store.insert(Memory(content="b"))
        assert self.store.count() == 2
        assert len(self.store.all()) == 2

    def test_memory_types(self):
        self.store.insert(Memory(content="ep", memory_type=MemoryType.EPISODIC))
        self.store.insert(Memory(content="sem", memory_type=MemoryType.SEMANTIC))
        self.store.insert(Memory(content="pro", memory_type=MemoryType.PROCEDURAL))
        all_mem = self.store.all()
        types = [m.memory_type for m in all_mem]
        assert MemoryType.EPISODIC in types
        assert MemoryType.SEMANTIC in types
        assert MemoryType.PROCEDURAL in types