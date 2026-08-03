# Enterprise RAG AI Knowledge Assistant

Enterprise-grade Retrieval-Augmented Generation (RAG) assistant with a FastAPI + FAISS + Groq backend, React frontend, and an AWS-deployed stack. Supports PDF, CSV, and JSON ingestion, hybrid retrieval, PII redaction, multi-agent frameworks, and Scripture-grounded Christianity endpoints.

## Live Deployment (AWS ap-south-1)

| Component | URL |
|---|---|
| **Frontend (UI)** | https://d2vdkua64gpad1.cloudfront.net |
| **Backend API** | http://enterprise-rag-alb-1831201874.ap-south-1.elb.amazonaws.com |

**Demo login:** `admin` / `admin123`

## Quick Start (local)

```bash
# Backend (port 8000)
pip install -r requirements.txt
uvicorn app.api:app --reload --port 8000

# Frontend (port 3000)
cd frontend && npm install && npm start
```

Required env vars (or `.env` in repo root — do NOT commit it):
- `GROQ_API_KEY` — required at import time in `rag/llm.py`
- `HF_API_TOKEN` — required for image generation in `app/image_generator.py:84`
- `MONGO_URL` — optional (e.g. `mongodb://localhost:27017`) enables MongoDB audit log + trace persistence + `/analytics`; without it, flat-file mode (`data/audit.log` + `data/traces/`) is used
- `JWT_SECRET` — defaults to a dev-only value; set a real secret in production

## Architecture

- **`app/`** — FastAPI service (entry point: `app.api:app`): auth/RBAC, upload, query, audit logging, event bus, MCP server, access policies
- **`rag/`** — shared RAG pipeline: vector store (FAISS + BM25 via RRF), chunking (Small-to-Big), smart retriever (multi-query + cross-encoder reranking), query router, sensitivity detection
- **`enterprise_rag_core/`** — shared library (v0.1.0) for microservices, installed as editable (`pip install -e ./enterprise_rag_core`)
- **`ingestion/`, `loaders/`** — multi-format ingestion (PDF/CSV/JSON), single entrypoint `ingestion_manager.py:ingest_file()`
- **`agents/`** — LangGraph (8-node) and CrewAI (3-agent) frameworks via `POST /agent/query`
- **`llm_providers/`** — pluggable LLM providers: Groq, OpenAI, Gemini, Claude, Ollama (fallback chain via `LLM_FALLBACK_CHAIN`)
- **`tasks/`** — Celery background ingestion (Redis broker)
- **`frontend/`** — React (Create React App) UI

## Endpoints

| Endpoint | Auth | Notes |
|---|---|---|
| `POST /login` | No | Returns JWT |
| `POST /upload` | JWT | Sets owner from authenticated user |
| `POST /query` | JWT | Main RAG query |
| `POST /agent/query` | JWT | LangGraph or CrewAI pipeline |
| `GET /sources` | JWT | List indexed documents |
| `DELETE /sources/{filename}` | Admin | Delete + rebuild index |
| `GET /debug/{query_id}` | Admin | Per-query trace |
| `DELETE /cache` | Admin | Clear semantic cache |
| `/christianity/*` | JWT | Scripture-grounded endpoints |

## Retrieval Pipeline

Self-RAG gate (greeting-like queries skip retrieval) → query router → semantic cache (0.95 threshold) → hybrid search (FAISS + BM25 fused via RRF) → multi-query expansion + cross-encoder reranking → Lost-in-the-Middle context builder (max 4000 chars) → LLM generation → answer similarity scoring.

## Guardrails

- PII redaction (SSN, credit card, email, phone, IP) in queries and answers
- High-risk keyword flagging (`password`, `secret`, `credential`, etc.)
- 5-layer pre-LLM moderation in Christianity mode
- Fake verse detection against the FAISS Bible index (sim threshold 0.6)

## AWS Deployment

Deployed to ECS Fargate (6 services: gateway, document-store, llm, bible, upload, agent) behind an ALB, with ElastiCache Redis, EC2 MongoDB, and a CloudFront + S3 frontend. CloudFront proxies API paths (`/login`, `/query`, `/sources`, `/christianity/*`, etc.) to the ALB so the SPA and API share one HTTPS origin.

**Stop/start (save costs):**

```bash
for svc in enterprise-rag-gateway enterprise-rag-document-store enterprise-rag-llm \
           enterprise-rag-bible enterprise-rag-upload enterprise-rag-agent; do
  aws ecs update-service --cluster enterprise-rag-cluster --service $svc \
    --desired-count 0 --region ap-south-1   # 0 = stop, 1 = start
done
```

## Evaluation

```bash
python eval.py --create-golden   # create golden question set (data/golden.json)
python eval.py --output eval-report.json   # RAGAS evaluation
```

Requires: `pip install ragas datasets langchain-groq langchain-huggingface`

## Default Users

| Username | Password | Role |
|---|---|---|
| admin | admin123 | admin |
| manager | manager123 | manager |
| employee | employee123 | employee |
| auditor | auditor123 | auditor |
