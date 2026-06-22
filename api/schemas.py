"""Pydantic schemas for the SYNAPSE API."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class StoreMemoryRequest(BaseModel):
    content: str = Field(..., description="The memory content to store")
    source: str = Field(default="", description="Where this memory came from")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    memory_type: Optional[str] = Field(default=None, description="episodic, semantic, or procedural")


class RetrieveRequest(BaseModel):
    query: str = Field(..., description="Query to search memories by")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results")
    memory_type: Optional[str] = Field(default=None, description="Filter by memory type")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum relevance score")


class ConsolidateResponse(BaseModel):
    merged: int
    promoted: int
    decayed: int
    extracted_facts: int
    before_count: int
    after_count: int


class ForgetRequest(BaseModel):
    threshold: float = Field(default=0.1, ge=0.0, le=1.0, description="Importance threshold for forgetting")


class ReflectRequest(BaseModel):
    topic: str = Field(..., description="Topic or question to reflect on")
    top_k: int = Field(default=15, ge=1, le=100, description="Number of memories to consider")


class MemoryResponse(BaseModel):
    id: str
    content: str
    memory_type: str
    importance_score: float
    created_at: str
    last_accessed_at: str
    access_count: int
    decay_rate: float
    tags: list[str]
    source: str
    linked_memories: list[str]


class StatsResponse(BaseModel):
    total_memories: int
    type_breakdown: dict
    avg_importance: float
    total_links: int
    db_path: str
