# RAG AI Knowledge Assistant

Enterprise RAG: Python backend (FastAPI + FAISS + Groq) + React frontend. Supports PDF, CSV, and JSON ingestion.

## Commands

```bash
# Terminal 1 — backend (port 8000)
uvicorn api:app --reload --port 8000

# Terminal 2 — frontend (port 3000)
cd frontend && npm start
```

## Requirements

- `GROQ_API_KEY` env var (or `.env` file) required at import time in `llm.py:6-7`
- `pip install -r requirements.txt` now includes all deps
- `HF_API_TOKEN` env var (or `.env` file) required for image generation in `image_generator.py:85` (uses Hugging Face Inference API via `huggingface_hub`)
- NLTK `punkt` + `punkt_tab` downloaded automatically on first `import chunker`
- `MONGO_URL` env var (optional, e.g. `mongodb://localhost:27017`) enables MongoDB for audit log + trace persistence + `/analytics` endpoint. Without it, flat-file mode (`data/audit.log` + `data/traces/`) is used.

## Default Users (seeded to `data/users.json` on first `auth.py` import)

| Username   | Password      | Role     |
|------------|---------------|----------|
| admin      | admin123      | admin    |
| manager    | manager123    | manager  |
| employee   | employee123   | employee |
| auditor    | auditor123    | auditor  |

## Architecture

- **`enterprise_rag_core/`** — Shared library package (v0.1.0) for microservices. Contains: `models/`, `chunker.py`, `cleaner.py`, `filter.py`, `shared_model.py`, `vector_store.py`, `event_bus.py`, `llm_providers/`. Installed as editable package (`pip install -e ./enterprise_rag_core`). Future services depend on this.
- `api.py` instantiates a single `VectorStore`. Index persists to `data/index.index` (FAISS) + `data/index.meta` (pickle) — loaded on startup, saved after every upload/delete.
- `data/` is gitignored; uploaded files live there at runtime.
- Multi-format ingestion: `loaders/` auto-detects `.pdf`/`.csv`/`.json` and routes to format-specific loader (`loaders/registry.py:8-12`). `ingestion_manager.py:ingest_file()` is the single entrypoint.
- Chunk metadata includes `format`, `owner`, `classification` (defaults: "unknown", "internal").
- **RBAC**: `POST /login` returns JWT (HS256, 24h TTL). `JWT_SECRET` defaults to `change-me-in-production-use-a-real-secret` (`auth.py:16`). Protected endpoints require `Authorization: Bearer <token>`.
- Roles: `admin`, `manager`, `employee`, `auditor`, `compliance` (`models/role.py:5-9`).
- `access_policy.py` resolves permitted sources via `data/access_policies.json`. Default policy allows `*` role to all sources.
- `/debug` and `/cache/*` admin-only; `/sources/{filename}` DELETE restricted to admin; `/upload` sets owner from authenticated user.
- **Retrieval**: FAISS inner-product (dense, 0.6) + BM25 (sparse, 0.4) fused via RRF (`vector_store.py:52-113`). `smart_retriever.py` adds multi-query expansion (LLM generates 2 variants) + cross-encoder reranking (`ms-marco-MiniLM-L-6-v2`).
- **Chunking**: Small-to-Big: child 200ch, parent 1500ch, overlap 100ch (`chunker.py:8-12`). `parent_text` in metadata, used in context.
- Context built with Lost-in-the-Middle ordering (`context_builder.py:6-12`), max 4000 chars.
- Semantic cache (threshold 0.95, max 512 entries, FIFO eviction). Invalidated on `/upload`, `DELETE /sources/{filename}`.
- Self-RAG gate: ≤4 greeting-like tokens skip retrieval (`api.py:162-173`).
- Query routing: `query_router.py` classifies intent (`fact_lookup`|`summarization`|`comparison`|`cross_source`|`data_analysis`) and tunes `top_k`/`rerank` per intent.
- Per-query trace persisted to `data/traces/{query_id}.json`; retrieve via `GET /debug/{query_id}` (admin-only). Rolling in-memory log capped at 200 entries.
- Answer similarity scored vs. chunks (`similarity_scorer.py`): HIGH ≥0.75, MEDIUM ≥0.50.

## Guardrails

- PII detection (SSN, credit card, email, phone, IP) in queries and answers — auto-redacts (`sensitivity_detector.py`).
- High-risk keyword check (`password`, `secret`, `credential`, etc.) flags queries (`is_high_risk_query`).
- Every query logged to `data/audit.log` (JSONL) with user, intent, PII findings (`audit_logger.py`).

## Evaluation

```bash
# Create golden question set template (edit data/golden.json with real Q&A)
python eval.py --create-golden

# Run RAGAS evaluation
python eval.py --output eval-report.json
```

- Judge LLM: Groq `llama-3.3-70b-versatile` via `LangchainLLMWrapper` (bypasses instructor — see `eval.py:47-53`). Metrics: faithfulness, answer_relevancy, context_precision, context_recall.
- Requires: `pip install ragas datasets langchain-groq langchain-huggingface`

## Agentic AI (LangGraph Multi-Agent System)

- **`agent_graph.py`** — LangGraph stateful agent graph replacing the linear RAG pipeline. 8 nodes with conditional routing:

```
self_rag_gate → query_router → cache_check → rbac_filter → retrieval_agent → context_builder → answer_generator → output_formatter
```

- Each node is a pure function operating on `AgentState` (TypedDict). Conditional edges short-circuit to `output_formatter` at gate/cache/RBAC steps when appropriate.
- The graph is compiled with `MemorySaver` checkpointing and instantiated in `api.py` at startup as `_agent_graph`.
- New endpoint: `POST /agent/query` — same interface as `/query` but runs through the LangGraph. Accepts optional `agent_framework` field (`"langgraph"` or `"crewai"`).

## MCP (Model Context Protocol)

- **`mcp_server.py`** — Wires up `fastapi-mcp` (`FastApiMCP`) to auto-discover all FastAPI endpoints as MCP tools.
- Mounted at `/mcp` via HTTP transport in `api.py:38`.
- Enables Claude Desktop and other MCP-compatible clients to use RAG tools (query, upload, search, Bible lookup) via the MCP protocol.
- The MCP server forwards `Authorization` headers from incoming requests to tool invocations automatically.

## CrewAI (Alternative Agent Framework)

- **`crew_agent.py`** — `RAGCrew` class with three CrewAI agents:
  - `Research Analyst` — retrieves relevant document chunks
  - `Information Synthesizer` — composes answer from retrieved context
  - `Quality Reviewer` — verifies accuracy and source attribution
- Sequential process (`Process.sequential`). Invoked via `POST /agent/query` with `"agent_framework": "crewai"`.
- Uses Groq `llama-3.3-70b-versatile` as the LLM backend for all agents.

## Requirements (updated)

- `pip install -r requirements.txt` now includes all deps: `langgraph`, `langchain`, `langchain-community`, `crewai`, `crewai-tools`, `python-multipart`, `rank-bm25`, `python-dotenv`, `huggingface-hub`, `ragas`, `datasets`, `langchain-groq`, `langchain-huggingface`, `celery`, `redis`, `openai`, `anthropic`, `google-generativeai`

## Docker

- **`Dockerfile`** — `python:3.11-slim` build. Exposes port 8000.
- **`docker-compose.yml`** — 8 services:

| Service | Port | Description |
|---|---|---|
| `gateway` | 8000 | Current monolith (refactor target for Phase 2d) |
| `worker` | — | Celery worker |
| `document_store` | 8001 | FAISS + BM25 vector store (Phase 2b) |
| `llm` | 8002 | Multi-provider LLM generation (Phase 2c) |
| `bible` | 8003 | Scripture retrieval (Phase 2e) |
| `upload` | 8004 | Document ingestion (Phase 2f) |
| `agent` | 8005 | LangGraph/CrewAI orchestration (Phase 2g) |
| `redis` | 6379 | Broker + cache |

- `data/` volume mounted for FAISS index persistence across restarts.

```bash
# Start all services
GROQ_API_KEY=your_key docker compose up -d

# Or with provider keys for fallback
GROQ_API_KEY=your_key \
OPENAI_API_KEY=your_key \
ANTHROPIC_API_KEY=your_key \
GOOGLE_API_KEY=your_key \
docker compose up -d

# With Ollama as fallback (install Ollama first: ollama.com)
GROQ_API_KEY=your_key \
LLM_FALLBACK_CHAIN=ollama \
OLLAMA_URL=http://host.docker.internal:11434 \
docker compose up -d
```

## Multi-LLM Provider Layer

- **`llm_providers/`** — Abstract `LLMProvider` interface with pluggable backends:

| Provider | Class | Env Config |
|---|---|---|
| Groq (default) | `GroqProvider` | `GROQ_API_KEY`, primary: `llama-3.3-70b-versatile`, fallback: `llama-3.1-8b-instant` |
| OpenAI | `OpenAIProvider` | `OPENAI_API_KEY`, `OPENAI_MODEL` (default: `gpt-4o`) |
| Gemini | `GeminiProvider` | `GOOGLE_API_KEY`, `GEMINI_MODEL` (default: `gemini-2.0-flash`) |
| Claude | `ClaudeProvider` | `ANTHROPIC_API_KEY`, `CLAUDE_MODEL` (default: `claude-sonnet-4-20250514`) |
| Ollama | `OllamaProvider` | `OLLAMA_URL` (default: `http://localhost:11434`), `OLLAMA_MODEL` (default: `llama3.2`), `OLLAMA_TIMEOUT` (default: `120`s) |

- Provider selected via `LLM_PROVIDER` env var (default: `groq`).
- Fallback chain via `LLM_FALLBACK_CHAIN` (comma-separated, e.g. `openai,claude,ollama`).
- If primary rate-limits or fails, each fallback is tried in order.
- `llm.py` now delegates to the provider abstraction — all existing code works unchanged.
- **Ollama as fallback**: Set `LLM_PROVIDER=groq` and `LLM_FALLBACK_CHAIN=ollama` — Groq handles 99% of traffic at ~0.5s, Ollama kicks in only when Groq rate-limits. Ideal for local GPU setups or air-gapped deployments.

## Event-Driven Architecture

- **`event_bus.py`** — Lightweight in-process pub/sub event bus.
- Events: `document.uploaded`, `document.deleted`, `query.executed`, `cache.invalidated`.
- Emitted at key points in `api.py` — handlers can be registered via `@event_bus.on("event.type")`.
- Timestamps auto-attached to all payloads.

## Async Task Queue (Celery + Redis)

- **`celery_app.py`** — Celery app configured with Redis broker/backend.
- **`tasks.py`** — Background tasks:
  - `ingest_document` — Loads index, ingests file, saves index (avoids blocking API)
  - `rebuild_bible_index` — Rebuilds the KJV Bible FAISS index
  - `generate_image_task` — Generates Christian images via HF API
- **`GET /tasks/{task_id}`** — Query task status (pending/started/success/failure).
- **`POST /upload?async=1`** — Dispatch ingestion via Celery (returns `task_id` immediately).
- Run worker: `celery -A tasks worker --loglevel=info`

## Gotchas

- No formal Python lint/test suite — manual verification via UI
- Groq rate-limit fallback in `llm.py:36-41`: `llama-3.3-70b-versatile` → `llama-3.1-8b-instant` on `RateLimitError`
- Frontend is Create React App (`react-scripts 5.0.1`); tests via `npm test` in `frontend/`
- JWT default secret is `change-me-in-production-use-a-real-secret` (`auth.py:16`)
- `.env` file in this repo contains a real API key — do NOT commit it
- `crew_agent.py` agents use `llm_config` dict (not LangChain objects) because they call Groq directly via the existing `llm.py` wrapper.

## Microservices Architecture (Phase 2)

The monolith is being decomposed into 6 microservices + 1 Celery worker + Redis, orchestrated via `docker-compose.yml`.

### Service Layout

```
services/
├── document_store/   — FAISS + BM25 index owner (port 8001)
│   └── api.py        — /search, /add, /sources, /stats
├── llm/              — Stateless LLM generation (port 8002)
│   └── api.py        — /generate, /chat
├── bible/            — Scripture retrieval (port 8003)
│   └── api.py        — /query, /verify-verse, /denominations, /stats
├── upload/           — Document ingestion (port 8004)
│   └── api.py        — /upload
└── agent/            — LangGraph/CrewAI orchestration (port 8005)
    ├── api.py        — /agent/query (accepts agent_framework: langgraph|crewai)
    └── Dockerfile    — copies ~20 RAG pipeline modules; delegates to document_store + llm via HTTP
```

### Dependency Graph

```
gateway ──┬── document_store  (HTTP, Phase 2b real)
          ├── llm             (HTTP, Phase 2c real)
          ├── bible           (HTTP, Phase 2e real)
          ├── upload          (HTTP, Phase 2f real)
           └── agent           (HTTP, real)

agent ──┬── document_store  (HTTP)
        └── llm             (HTTP)

bible ──┬── document_store  (HTTP)
        └── llm             (HTTP)

upload ──→ document_store  (HTTP)
```

### Extraction Order

| Phase | Service | Status |
|---|---|---|
| 2a | Infrastructure (services/ + Dockerfiles) | ✅ Done |
| 2b | Document Store Service | ✅ Done |
| 2c | LLM Service | ✅ Done |
| 2d | Gateway refactor (api.py delegates) | ✅ Done |
| 2e | Bible Service | ✅ Done |
| 2f | Upload Service | ✅ Done |
| 2g | Agent Service | ✅ Done |

### Gateway Clients (`gateway_clients.py`)

The gateway transparently delegates to microservices via HTTP when configured:

```python
# api.py
from gateway_clients import RemoteVectorStore, remote_generate, is_remote_vs, is_remote_llm

if is_remote_vs():
    vs = RemoteVectorStore()    # delegates to document_store service
if is_remote_llm():
    generate_answer = remote_generate  # delegates to LLM service
```

- `DOCUMENT_STORE_URL` env var → `RemoteVectorStore` proxy for search/add/delete/list_sources
- `LLM_SERVICE_URL` env var → `remote_generate()` for top-level LLM calls
- Internal pipeline modules (`rag_pipeline.py`, `agent_graph.py`) use local imports (in-process)
- When URLs are not set, gateway falls back to local `VectorStore` / `llm.generate_answer` (current monolith behavior)

### Running Locally (development)

Each service can run standalone via uvicorn, e.g.:

```bash
# Terminal 1 — Document Store
uvicorn services.document_store.api:app --reload --port 8001

# Terminal 2 — LLM
uvicorn services.llm.api:app --reload --port 8002

# Terminal 3 — Gateway (monolith, delegates when URLs set)
uvicorn api:app --reload --port 8000

# Or with remote delegation:
DOCUMENT_STORE_URL=http://localhost:8001 LLM_SERVICE_URL=http://localhost:8002 uvicorn api:app --reload --port 8000
```
