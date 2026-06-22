"""Use SYNAPSE with the Claude API for enriched reflection."""

import os
from synapse import MemoryEngine

engine = MemoryEngine()

# Store some memories
engine.store("The user is a developer building open-source AI infrastructure", source="onboarding", tags=["user"])
engine.store("The user prefers dark mode UI with purple accent colors", source="conversation", tags=["preference"])
engine.store("The project is called SYNAPSE — a persistent memory layer for AI", source="docs", tags=["project"])

# Get context block ready for Claude
reflection = engine.reflect("user preferences")

if reflection["has_memories"]:
    # The context_block is formatted XML you can inject directly
    # into any Claude system prompt
    print("/* Inject this into your Claude prompt: */")
    print(reflection["context_block"])
else:
    print("No memories found.")