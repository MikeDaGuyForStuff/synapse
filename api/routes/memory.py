"""Memory API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.main import get_engine
from api.schemas import (
    StoreMemoryRequest,
    RetrieveRequest,
    ForgetRequest,
    ReflectRequest,
    ConsolidateResponse,
    MemoryResponse,
    StatsResponse,
)
from synapse import MemoryEngine
from synapse.types import MemoryType

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("", response_model=MemoryResponse)
def store_memory(req: StoreMemoryRequest, eng: MemoryEngine = Depends(get_engine)):
    """Store a new memory."""
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
    """Retrieve memories relevant to a query."""
    mtype = None
    if memory_type:
        try:
            mtype = MemoryType(memory_type)
        except ValueError:
            raise HTTPException(400, f"Invalid memory_type: {memory_type}")
    return eng.retrieve(query=query, top_k=top_k, memory_type=mtype, min_score=min_score)


@router.post("/consolidate", response_model=ConsolidateResponse)
def consolidate_memories(eng: MemoryEngine = Depends(get_engine)):
    """Trigger manual consolidation."""
    result = eng.consolidate()
    return ConsolidateResponse(**result)


@router.post("/forget")
def forget_memories(
    req: ForgetRequest,
    eng: MemoryEngine = Depends(get_engine),
):
    """Forget memories below the importance threshold."""
    count = eng.forget(threshold=req.threshold)
    return {"forgotten": count, "threshold": req.threshold}


@router.get("/reflect")
def reflect_on_topic(
    topic: str,
    top_k: int = 15,
    eng: MemoryEngine = Depends(get_engine),
):
    """Get a synthesized memory summary on a topic."""
    return eng.reflect(topic=topic, top_k=top_k)


@router.delete("/{memory_id}")
def delete_memory(memory_id: str, eng: MemoryEngine = Depends(get_engine)):
    """Delete a specific memory by ID."""
    deleted = eng._store.delete(memory_id)
    if not deleted:
        raise HTTPException(404, f"Memory {memory_id} not found")
    return {"deleted": True, "id": memory_id}


@router.get("/stats", response_model=StatsResponse)
def memory_stats(eng: MemoryEngine = Depends(get_engine)):
    """Get memory health statistics."""
    all_mems = eng._store.all()

    type_breakdown = {"episodic": 0, "semantic": 0, "procedural": 0}
    total_imp = 0.0
    total_links = 0
    for m in all_mems:
        type_breakdown[m.memory_type.value] = type_breakdown.get(m.memory_type.value, 0) + 1
        total_imp += m.importance_score
        total_links += len(m.linked_memories)

    return StatsResponse(
        total_memories=len(all_mems),
        type_breakdown=type_breakdown,
        avg_importance=round(total_imp / len(all_mems), 4) if all_mems else 0.0,
        total_links=total_links,
        db_path=eng._store.db_path,
    )