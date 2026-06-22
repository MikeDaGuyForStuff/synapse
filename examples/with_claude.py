"""Use SYNAPSE with the Claude API for enriched reflection."""

from synapse import MemoryEngine

engine = MemoryEngine()

# Store some memories — they persist forever
engine.store("The user is a developer building open-source AI infrastructure", source="onboarding", tags=["user"])
engine.store("The user prefers dark mode UI with purple accent colors", source="conversation", tags=["preference"])
engine.store("The project is called SYNAPSE — a persistent memory layer for AI", source="docs", tags=["project"])

# Get optimized context block for Claude
ctx = engine.context("user preferences")

if ctx["has_memories"]:
    # The context_block is formatted XML you can inject directly
    # into any Claude system prompt
    print(f"/* {ctx['total_memories_found']} memories found across {len(ctx['layers_used'])} layers */")
    print(f"/* Token estimate: {ctx['token_estimate']} — fits in 4K: {ctx['fits_in_context']} */")
    print()
    print("/* Inject this into your Claude prompt: */")
    print(ctx["context_block"])
else:
    print("No memories found.")