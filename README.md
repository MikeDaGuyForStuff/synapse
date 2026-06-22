# SYNAPSE — AI Never Forgets

![PyPI](https://img.shields.io/pypi/v/synapse-memory)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)

**Every AI forgets everything. SYNAPSE fixes that.**

```python
from synapse import MemoryEngine

engine = MemoryEngine()
engine.store("Every AI forgets everything. SYNAPSE fixes that.")
print(engine.context("AI memory")["context_block"])
```

SYNAPSE is a persistent, self-organizing memory engine for any AI model. It gives AI true long-term memory — persistent, private, and gets smarter over time. No cloud, no subscription, no vendor lock-in.

Built for AI agents, chatbots, and any application where context needs to survive beyond a single session.

---

## The Revolution: AI Should Never Forget

Human brains forget. **AI shouldn't.**

Every memory system today uses some form of forgetting — delete old data, prune rarely accessed items, apply a decay threshold. This is wrong. It's copying human biology instead of improving on it.

SYNAPSE uses **progressive compression** instead of deletion:

```
RAW ──► COMPRESSED ──► KNOWLEDGE ──► IDENTITY
(single facts) → (summaries) → (patterns) → (stable truths)
```

1. Everything starts at **RAW** — verbatim, exactly what happened
2. Old/low-priority RAW memories get **COMPRESSED** into summaries
3. COMPRESSED clusters get **EXTRACTED** into KNOWLEDGE facts
4. Established facts become part of **IDENTITY** — the stable user model

**Nothing is ever deleted.** Total storage grows forever. Retrieval stays fast because compressed representations are smaller and more meaningful. The system gets smarter with more data.

> This is how Claude handles 200K tokens of context — not by forgetting, but by managing information efficiently. SYNAPSE brings this same philosophy to your own AI stack.

## Live Demo

Try it: start the API, open `demo/chat.html` in a browser, add your API key, and talk to an AI. Watch memories appear as nodes on the graph in real time. Toggle memory off to see what the AI forgets.

## Quick Start

### Install

```bash
pip install synapse-memory

# For local embeddings (recommended):
pip install synapse-memory[embeddings]
```

> **⚠️ Without sentence-transformers, SYNAPSE falls back to 128-dim hash embeddings.** Retrieval quality will be noticeably poor. Always install `[embeddings]` for real use.

### Use it

```python
from synapse import MemoryEngine

engine = MemoryEngine()

# Store — everything is remembered forever
engine.store("Mike loves building AI infrastructure", source="conversation")
engine.store("Mike prefers dark mode with purple accents", source="conversation")

# Retrieve — searches all layers (raw, compressed, knowledge, identity)
results = engine.retrieve("user preferences", top_k=5)
for r in results:
    print(f"[{r['layer']}] {r['memory']['content']}")

# Compress — transforms old RAW memories into COMPRESSED summaries
engine.compress()

# Extract — finds patterns and promotes to KNOWLEDGE layer
engine.extract()

# Context — get an optimized context block ready for any LLM prompt
ctx = engine.context("user preferences")
print(ctx["context_block"])
```

### Start the API

```bash
uvicorn api.main:app --reload
```

### Start the Dashboard

```bash
cd dashboard
npm install
npm run dev
```

### Run the Demo

Open `demo/chat.html` in any browser while the API is running. Talk to an AI. Watch its memory grow.

### Or use Docker

```bash
docker compose up
```

This starts the API (port 8742), dashboard (port 5173), and demo (port 8080) — one command, everything running.

## The Context Function — Your LLM Integration

`engine.context(query)` is the single function you call to integrate SYNAPSE with any AI model:

```python
# Before sending a prompt to Claude/GPT/local model:
ctx = engine.context("what the user was working on")

# Inject ctx["context_block"] into your system prompt
# SYNAPSE handles: what to retrieve, what layer to use,
# how to format, token budget management
system_prompt = f"""
You are a helpful assistant with persistent memory.

{ctx['context_block']}

Respond to the user naturally, referencing relevant memories.
"""
```

The context block is formatted as structured XML, organized by layer (identity → knowledge → summaries → recent), and includes a token estimate so you know it fits.

## Dashboard

![SYNAPSE Dashboard](dashboard-screenshot.png)

React + D3 interface showing your AI's memory as a force-directed graph. Nodes are sized by importance, colored by memory type (episodic/semantic/procedural), and connected by relevance links. Switch between Graph, Timeline, Cards, and Reflect tabs.

## Architecture

**4 Memory Layers** (never delete, only promote):

| Layer | Description | Persistence |
|-------|-------------|-------------|
| RAW | Verbatim facts and events | Until compressed (7+ days) |
| COMPRESSED | Summaries of related RAW memories | Until promoted (30+ days) |
| KNOWLEDGE | Extracted patterns and facts | Until abstracted (90+ days) |
| IDENTITY | Stable user model | Forever |

**3 Memory Types** (mirror human cognition):

- **Episodic** — things that happened
- **Semantic** — facts and knowledge  
- **Procedural** — how to do things

**Importance Scoring** — each memory scored 0.0–1.0 based on named entities, user preferences, connectivity, access frequency.

**Compression Priority** — determines which memories to compress next, based on age, access frequency, and importance. Frequently accessed memories stay raw longer. Old, rarely accessed memories get compressed first.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/memory` | Store a new memory (RAW layer) |
| GET | `/memory/retrieve` | Search all memory layers |
| POST | `/memory/compress` | Compress RAW → COMPRESSED summaries |
| POST | `/memory/extract` | Extract COMPRESSED → KNOWLEDGE facts |
| GET | `/memory/context` | Generate optimized LLM context block |
| DELETE | `/memory/{id}` | Delete a specific memory |
| GET | `/memory/stats` | Memory health + layer breakdown |
| GET | `/health` | Health check |

## Project Structure

```
synapse/
├── synapse/           # Core library
│   ├── engine.py      # Store, retrieve, compress, extract, context
│   ├── store.py       # SQLite persistence (4 layers)
│   ├── types.py       # Memory model with compression hierarchy
│   ├── embeddings.py  # Local embedding generation
│   ├── importance.py  # Importance scoring
│   └── decay.py       # Compression scheduling
├── api/               # FastAPI layer
├── dashboard/         # React + D3 visualization
├── demo/              # Chat demo (single HTML file)
├── examples/          # Usage examples
└── tests/             # 21 tests, all passing
```

## License

MIT — free for any use, personal or commercial.

---

**One person built this. One weekend. No permission needed.**

[GitHub](https://github.com/MikeDaGuyForStuff/synapse) — built by MikeDaGuyForStuff

*"AI should never forget. It should only understand better."*