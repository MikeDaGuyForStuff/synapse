"""Use SYNAPSE with any LLM — the context() function is your integration point."""

from synapse import MemoryEngine

engine = MemoryEngine()

engine.store("I'm building a memory engine for AI called SYNAPSE", source="dev", tags=["project"])
engine.store("The architecture has 4 layers: raw, compressed, knowledge, identity", source="docs", tags=["architecture"])
engine.store("SYNAPSE never forgets — it progressively compresses instead of deleting", source="docs", tags=["philosophy"])

# Retrieve — searches all layers
results = engine.retrieve("architecture", top_k=5)
for r in results:
    print(f"  [{r['layer']}] [{r['combined_score']:.2f}] {r['memory']['content']}")

print("---")

# Context — the single function you call to integrate with any LLM
ctx = engine.context("SYNAPSE project")
print(ctx["summary"] if hasattr(ctx, 'summary') else f"Found {ctx['total_memories_found']} memories")
print()
print("Ready-to-inject context block:")
print(ctx["context_block"])
print()
print(f"Token estimate: {ctx['token_estimate']} | Fits in 4K window: {ctx['fits_in_context']}")