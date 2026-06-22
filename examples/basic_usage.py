"""Basic usage — 3 lines to get started with SYNAPSE."""

from synapse import MemoryEngine

# Create a memory engine (stores in ./synapse_data/)
engine = MemoryEngine()

# Store a memory
engine.store("Every AI forgets everything. SYNAPSE fixes that.", source="README", tags=["core"])

# Retrieve what's relevant
results = engine.retrieve("AI memory", top_k=5)
for r in results:
    print(f"[{r['memory']['importance_score']:.2f}] {r['memory']['content']}")

# Reflect on what you know
reflection = engine.reflect("memory")
print(reflection["summary"])