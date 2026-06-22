"""SYNAPSE API — FastAPI application.

Start with: uvicorn api.main:app --reload
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from synapse import MemoryEngine, MemoryStore

# Global engine instance — use env var to point to a specific DB
db_path = os.environ.get("SYNAPSE_DB_PATH")
if db_path:
    store = MemoryStore(db_path)
    engine: MemoryEngine = MemoryEngine(store=store)
else:
    engine: MemoryEngine = MemoryEngine()

description = """
SYNAPSE — Persistent Self-Organizing Memory for AI.

Give any AI model true long-term memory that persists, stays private,
self-organizes, and gets smarter over time. No cloud, no subscription,
no vendor lock-in.
"""

app = FastAPI(
    title="SYNAPSE Memory Engine",
    description=description,
    version="0.1.0",
    contact={
        "name": "SYNAPSE",
        "url": "https://github.com/MikeDaGuyForStuff/synapse",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_engine() -> MemoryEngine:
    """Dependency: get the shared memory engine."""
    return engine


# Import and register routers
from api.routes.memory import router as memory_router
from api.routes.health import router as health_router

app.include_router(memory_router)
app.include_router(health_router)
