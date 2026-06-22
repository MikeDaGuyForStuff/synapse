"""Memory API routes — no forgetting, only compression."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.main import get_engine
from api.schemas import (
    StoreMemoryRequest,
    RetrieveRequest,
    ContextRequest,
    CompressResponse,
    ExtractResponse,
    ContextResponse,
    MemoryResponse,
    StatsResponse,
)
from synapse import MemoryEngine
from synapse.types import MemoryType

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("", response_model=MemoryResponse)
def store_memory(req: StoreMemoryRequest, eng: MemoryEngine = Depends(get_engine)):
    """Store a new memory. All memories start at the RAW layer."""
    mem_id = eng.store(
        content=req.content,
        source=req.source,
        tags=req.tags,
        memory_type=req.memory_type,
    )
    mem = eng._store.get(mem_id)
    if not mem:
        raise HTTPException(500, "Failed to store memory")
    return MemoryResponse(**mem.to_dict())


@router.get("/retrieve", response_model=list[dict])
def retrieve_memories(
    query: str,
    top_k: int = 10,
    memory_type: str | None = None,
    min_score: float = 0.0,
    eng: MemoryEngine = Depends(get_engine),
):
    """Retrieve memories across all layers (raw, compressed, knowledge, identity)."""
    mtype = None
    if memory_type:
        try:
            mtype = MemoryType(memory_type)
        except ValueError:
            raise HTTPException(400, f"Invalid memory_type: {memory_type}")
    return eng.retrieve(query=query, top_k=top_k, memory_type=mtype, min_score=min_score)


@router.post("/compress", response_model=CompressResponse)
def compress_memories(
    target_count: int = 10,
    eng: MemoryEngine = Depends(get_engine),
):
    """Compress old RAW memories into COMPRESSED summaries.
    Nothing is deleted — memories are promoted to higher layers."""
    result = eng.compress(target_count=target_count)
    return CompressResponse(**result)


@router.post("/extract", response_model=ExtractResponse)
def extract_knowledge(eng: MemoryEngine = Depends(get_engine)):
    """Extract KNOWLEDGE facts from clusters of COMPRESSED memories."""
    result = eng.extract()
    return ExtractResponse(**result)


@router.get("/context", response_model=ContextResponse)
def get_context(
    query: str,
    max_tokens: int = 4000,
    eng: MemoryEngine = Depends(get_engine),
):
    """Generate an optimized context block ready to inject into any LLM prompt.
    Searches all memory layers and formats the most relevant information."""
    return eng.context(query=query, max_tokens=max_tokens)


@router.delete("/{memory_id}")
def delete_memory(memory_id: str, eng: MemoryEngine = Depends(get_engine)):
    """Delete a specific memory by ID."""
    mem = eng._store.get(memory_id)
    if not mem:
        raise HTTPException(404, f"Memory {memory_id} not found")
    # In a true never-forget system this wouldn't exist,
    # but providing it for manual cleanup
    # Use SQLite DELETE to actually remove it
    import sqlite3
    conn = sqlite3.connect(eng._store.db_path)
    conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    conn.commit()
    conn.close()
    return {"deleted": True, "id": memory_id}


@router.get("/stats", response_model=StatsResponse)
def memory_stats(eng: MemoryEngine = Depends(get_engine)):
    """Get memory health statistics — layer breakdown, type breakdown, totals."""
    all_mems = eng._store.all()
    layer_breakdown = eng._store.count_by_layer()
    type_breakdown = eng._store.count_by_type()

    total_imp = sum(m.importance_score for m in all_mems)
    total_links = sum(len(m.linked_memories) for m in all_mems)

    return StatsResponse(
        total_memories=len(all_mems),
        layer_breakdown=layer_breakdown,
        type_breakdown=type_breakdown,
        avg_importance=round(total_imp / len(all_mems), 4) if all_mems else 0.0,
        total_links=total_links,
        db_path=eng._store.db_path,
    )