"""Basic usage — 3 lines to get started with SYNAPSE."""

from synapse import MemoryEngine

# Create a memory engine (stores in ./synapse_data/)
engine = MemoryEngine()

# Store a memory — never forgotten, only compressed over time
engine.store("Every AI forgets everything. SYNAPSE fixes that.", source="README", tags=["core"])

# Retrieve what's relevant — searches all layers
results = engine.retrieve("AI memory", top_k=5)
for r in results:
    print(f"[{r['layer']}] [{r['memory']['importance_score']:.2f}] {r['memory']['content']}")

# Generate an optimized context block ready for any LLM
ctx = engine.context("memory")
print(ctx["context_block"])