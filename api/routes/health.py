"""Health check route."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.main import get_engine
from synapse import MemoryEngine

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(eng: MemoryEngine = Depends(get_engine)):
    """Basic health check endpoint."""
    return {
        "status": "ok",
        "service": "SYNAPSE Memory Engine",
        "version": "0.1.0",
        "memories_stored": eng._store.count(),
    }