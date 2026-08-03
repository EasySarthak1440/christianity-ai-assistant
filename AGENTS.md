# AGENTS.md

## Quick Start

```bash
# Backend (port 8000) — the actual entry point is app.api, NOT api.api
uvicorn app.api:app --reload --port 8000

# Frontend (port 3000)
cd frontend && npm start
```

## Setup

```bash
pip install -r requirements.txt
```

- `GROQ_API_KEY` (or `.env`) required at import time in `rag/llm.py`
- `HF_API_TOKEN` (or `.env`) required for image generation in `app/image_generator.py:84`
- `MONGO_URL` (optional, e.g. `mongodb://localhost:27017`) enables MongoDB for audit log + trace persistence + `/analytics`. Without it, flat-file mode (`data/audit.log` + `data/traces/`) is used.
- NLTK `punkt` + `punkt_tab` downloaded automatically on first `import rag.chunker`
- JWT secret defaults to `change-me-in-production-use-a-real-secret` (`app/auth.py:16`)
- `.env` file in repo root — do NOT commit it

## Key Modules (all live in `rag/`, not root)

| File | Role |
|---|---|
| `rag/vector_store.py` | FAISS + BM25 hybrid (RRF fusion: dense 0.6 / sparse 0.4) |
| `rag/chunker.py` | Small-to-Big: child 200ch, parent 1500ch, overlap 100ch |
| `rag/llm.py` | Groq wrapper with rate-limit fallback |
| `rag/smart_retriever.py` | Multi-query expansion + cross-encoder reranking |
| `rag/query_router.py` | Intent classification → tunes `top_k`/`rerank` |
| `rag/pipeline.py` | End-to-end RAG orchestration |
| `rag/sensitivity_detector.py` | PII detection + redaction |

## Architecture

- `enterprise_rag_core/` — Shared library (v0.1.0) for microservices; installed as editable (`pip install -e ./enterprise_rag_core`)
- `app/api.py` — FastAPI app; single `VectorStore` instance; index persists to `data/index.index` + `data/index.meta`
- `ingestion/ingestion_manager.py:ingest_file()` — single entrypoint for multi-format ingestion (PDF/CSV/JSON auto-detected via `loaders/`)
- `app/auth.py` — JWT (HS256, 24h TTL) + RBAC; seeds default users to `data/users.json` on first import
- `app/access_policy.py` — resolves permitted sources via `data/access_policies.json`
- `app/audit_logger.py` — JSONL audit log with user, intent, PII findings
- `app/event_bus.py` — in-process pub/sub; events: `document.uploaded`, `document.deleted`, `query.executed`, `cache.invalidated`
- `app/mcp_server.py` — exposes FastAPI endpoints as MCP tools mounted at `/mcp`

## Endpoints

| Endpoint | Auth | Notes |
|---|---|---|
| `POST /login` | No | Returns JWT |
| `POST /upload` | JWT | Sets owner from authenticated user; invalidates semantic cache |
| `POST /query` | JWT | Main RAG query |
| `POST /agent/query` | JWT | LangGraph or CrewAI pipeline (`agent_framework` field) |
| `GET /sources` | JWT | List indexed documents |
| `DELETE /sources/{filename}` | Admin | Delete + rebuild index |
| `GET /debug/{query_id}` | Admin | Per-query trace |
| `DELETE /cache` | Admin | Clear semantic cache |
| `/christianity/*` | JWT | Scripture-grounded endpoints |

## Retrieval Pipeline

Self-RAG gate at `app/api.py:264` — queries with ≤4 greeting-like tokens (`hi`, `hello`, `hey`, `thanks`, `thank`, `bye`, `help`, `what`, `who`, `are`, `you`) skip retrieval entirely. Then: query router → semantic cache (threshold 0.95, max 512, FIFO, invalidated on upload/delete) → hybrid search (FAISS + BM25 fused via RRF) → multi-query expansion + cross-encoder reranking → Lost-in-the-Middle context builder (max 4000 chars) → LLM generation → answer similarity scoring (HIGH ≥0.75, MEDIUM ≥0.50).

## Guardrails

- PII redaction (SSN, credit card, email, phone, IP) in queries and answers (`rag/sensitivity_detector.py`)
- High-risk keyword flagging (`password`, `secret`, `credential`, etc.)
- 5-layer pre-LLM moderation in Christianity mode (rewrite detection, hate/extremism, violence justification, adversarial injection, blasphemy)
- Fake verse detection: verifies `Book N:V` patterns against FAISS (sim threshold 0.6)

## Docker (multi-service, Phase 2)

```bash
# Full stack with all services
GROQ_API_KEY=your_key docker compose up -d

# With Ollama fallback
GROQ_API_KEY=your_key LLM_FALLBACK_CHAIN=ollama docker compose up -d
```

Services: `gateway` (8000), `worker` (Celery), `document_store` (8001), `llm` (8002), `bible` (8003), `upload` (8004), `agent` (8005), `redis` (6379), `mongo` (27017). All share `data/` volume for FAISS persistence.

## Celery (background tasks)

- `tasks/celery_app.py` + `tasks/tasks.py` — Redis broker/backend
- `ingest_document` — async file ingestion
- Run worker: `celery -A tasks worker --loglevel=info`
- `POST /upload?async=1` dispatches via Celery (returns `task_id`)
- `GET /tasks/{task_id}` — query task status

## Agent Frameworks

- **LangGraph** (`agents/graph.py`): 8-node stateful graph with conditional edges
- **CrewAI** (`agents/crew.py`): 3 agents (Research Analyst, Information Synthesizer, Quality Reviewer) — sequential process
- Both invoked via `POST /agent/query` with `agent_framework` field (`"langgraph"` or `"crewai"`)
- CrewAI agents call Groq directly via `rag/llm.py` wrapper (not LangChain objects)

## Multi-LLM Provider Layer (`llm_providers/`)

Pluggable providers: Groq (default/fallback), OpenAI, Gemini, Claude, Ollama. Selected via `LLM_PROVIDER` env var; fallback chain via `LLM_FALLBACK_CHAIN` (comma-separated). Ollama as fallback: `LLM_PROVIDER=groq` + `LLM_FALLBACK_CHAIN=ollama`.

## Evaluation

```bash
# Create golden question set (writes data/golden.json)
python eval.py --create-golden

# Run RAGAS evaluation
python eval.py --output eval-report.json
```

- Golden set path: `data/golden.json` (not `eval/test_cases.json`)
- Judge LLM: Groq `llama-3.3-70b-versatile` via `LangchainLLMWrapper` (bypasses instructor — see `eval.py:47-53`)
- Metrics: faithfulness, answer_relevancy, context_precision, context_recall
- Requires: `pip install ragas datasets langchain-groq langchain-huggingface`

## CI

- **Python lint**: `ruff check --output-format=github .` (CI: `ruff check --output-format=github .`)
- **Frontend build**: `cd frontend && npm ci && npm run build --if-present`
- **Frontend test**: `cd frontend && npm test -- --watchAll=false`
- **Docker build**: `docker build -t enterprise-rag-gateway .` and per-service builds
- **Smoke test** (main branch only): starts full compose, polls `/health` on ports 8000/8001/8002

## Gotchas

- No formal Python lint/test suite — manual verification via UI
- Groq rate-limit fallback in `rag/llm.py`: `llama-3.3-70b-versatile` → `llama-3.1-8b-instant` on `RateLimitError`
- Frontend is Create React App (`react-scripts 5.0.1`); `npm test` runs in watch mode by default — use `--watchAll=false` for CI
- `data/` is gitignored; uploaded files live there at runtime
- The `app/` directory contains FastAPI-specific code; `rag/`, `agents/`, `loaders/`, `llm_providers/`, `tasks/`, `ingestion/`, `models/` are shared packages
- `ingestion/` has both legacy `ingest.py` (PDF-only) and current `ingestion_manager.py` (multi-format) — use the latter

## AWS Deployment (ap-south-1 Mumbai) — STOPPED TO SAVE COSTS

> ⚠️ All AWS resources have been stopped/deleted. See instructions below to restore if needed.

### Deployment Artifacts (deleted)

`deploy/` directory was removed. To redeploy, regenerate scripts from the patterns used in this session.

### To Restart Deployment (from scratch)

```bash
# 1. Create ECR repos
aws ecr create-repository --repository-name enterprise-rag-gateway --region ap-south-1
# ... repeat for enterprise-rag-{document-store,llm,bible,upload,agent}

# 2. Authenticate Docker
aws ecr get-login-password --region ap-south-1 \
  | docker login --username AWS --password-stdin 290199195192.dkr.ecr.ap-south-1.amazonaws.com

# 3. Build & push all 6 images
docker build -t 290199195192.dkr.ecr.ap-south-1.amazonaws.com/enterprise-rag-gateway:latest .
docker push 290199195192.dkr.ecr.ap-south-1.amazonaws.com/enterprise-rag-gateway:latest
# ... repeat for all 6 services using services/*/Dockerfile

# 4. Infrastructure (SG, Redis, MongoDB)
#    Create security group in default VPC (vpc-0323b9ec086cc521d)
#    Create ElastiCache Redis cluster
#    Launch EC2 instance for MongoDB (t3.micro, ami-00455f385512f4bb5)

# 5. ECS cluster + task definitions + services + ALB
# 6. Deploy frontend: npm run build; aws s3 sync build/ s3://enterprise-rag-frontend/
# 7. Create CloudFront distribution pointing to S3
```

### Key env vars for ECS task definitions

- `GROQ_API_KEY` — Groq API key
- `HF_API_TOKEN` — Hugging Face API key  
- `JWT_SECRET` — generate with `openssl rand -hex 32`
- `REDIS_URL` — ElastiCache endpoint (format: `redis://<endpoint>:6379`)
- `MONGO_URL` — `mongodb://<EC2_MONGODB_IP>:27017`
