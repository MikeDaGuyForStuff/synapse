"""Pydantic schemas for the SYNAPSE API."""

from __future__ import annotations

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


class ContextRequest(BaseModel):
    query: str = Field(..., description="Query or topic to generate context for")
    max_tokens: int = Field(default=4000, ge=100, le=32000, description="Target max context size")


class CompressResponse(BaseModel):
    compressed_groups: int
    raw_memories_compressed: int
    summaries_created: int


class ExtractResponse(BaseModel):
    extracted: int


class ContextResponse(BaseModel):
    query: str
    has_memories: bool
    total_memories_found: int
    layers_used: list[str]
    layer_breakdown: dict
    token_estimate: int
    fits_in_context: bool
    context_block: str


class MemoryResponse(BaseModel):
    id: str
    content: str
    memory_type: str
    layer: str
    importance_score: float
    created_at: str
    last_accessed_at: str
    access_count: int
    tags: list[str]
    source: str
    linked_memories: list[str]
    compressed_from: list[str]
    parent_id: Optional[str] = None


class StatsResponse(BaseModel):
    total_memories: int
    layer_breakdown: dict
    type_breakdown: dict
    avg_importance: float
    total_links: int
    db_path: str
