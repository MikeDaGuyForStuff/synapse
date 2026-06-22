"""Health check route — shows engine health with layer breakdown."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.main import get_engine
from synapse import MemoryEngine

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(eng: MemoryEngine = Depends(get_engine)):
    """Basic health check with top-level stats."""
    store = eng._store
    return {
        "status": "ok",
        "service": "SYNAPSE Memory Engine",
        "version": "0.2.0",
        "memories_stored": store.count(),
        "layers": store.count_by_layer(),
        "types": store.count_by_type(),
        "never_forgets": True,
        "philosophy": "Memories are compressed, never deleted",
    }