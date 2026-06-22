"""Use SYNAPSE with Ollama local LLM for enhanced reflection."""

from synapse import MemoryEngine

engine = MemoryEngine()

engine.store("I'm building a memory engine for AI called SYNAPSE", source="dev", tags=["project"])
engine.store("The architecture has 4 layers: store, engine, API, dashboard", source="docs", tags=["architecture"])

# Retrieve without LLM — works on embeddings alone
results = engine.retrieve("architecture", top_k=5)
for r in results:
    print(f"  [{r['combined_score']:.2f}] {r['memory']['content']}")

print("---")

# Reflection works with or without an LLM — the context block is ready
# to be injected into any LLM prompt
ref = engine.reflect("SYNAPSE project")
print(ref["summary"])
print()
print("Ready-to-inject context block:")
print(ref["context_block"])