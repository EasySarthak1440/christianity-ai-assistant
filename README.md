# Enterprise RAG AI Knowledge Assistant

> Production-grade Retrieval-Augmented Generation (RAG) system — multi-format ingestion, source-cited answers, enterprise security, and a Christianity AI assistant with scripture grounding, denomination awareness, and hallucination prevention.

A full-stack RAG application with a futuristic React UI and a FastAPI backend, built on a clean modular Python pipeline. Upload PDFs, CSVs, and JSONs; ask questions in natural language; or switch to Christianity mode for KJV Bible-grounded answers with denominational context.

## Live Deployment (AWS ap-south-1)

| Component | URL |
|---|---|
| **Frontend (UI)** | https://d2vdkua64gpad1.cloudfront.net |
| **Backend API** | http://enterprise-rag-alb-1831201874.ap-south-1.elb.amazonaws.com |

**Demo login:** `admin` / `admin123`

---

## Features

### RAG Pipeline
- Multi-format ingestion: **PDF**, **CSV**, **JSON** with per-chunk `source` + `page` metadata
- Text cleaning + smart sentence-aware chunking (small-to-big: 200ch child / 1500ch parent, 100ch overlap)
- Hybrid retrieval: **FAISS inner-product** (dense, weight 0.6) + **BM25** (sparse, weight 0.4) fused via **RRF**
- Multi-query expansion (LLM generates 2 query variants) + **cross-encoder re-ranking** (`ms-marco-MiniLM-L-6-v2`)
- Answer generation via **Groq LLaMA-4 Maverick** (automatic rate-limit fallback to `llama-3.1-8b-instant`)
- Source + page citations returned with every answer
- **Semantic cache** (threshold 0.95, max 512 entries, FIFO eviction) — auto-invalidated on upload/delete
- **Query router** classifies intent (`fact_lookup`|`summarization`|`comparison`|`cross_source`|`data_analysis`) and tunes `top_k`/rerank per intent
- **Lost-in-the-Middle** context builder (max 4000 chars)

### Christianity AI Assistant
- **KJV Bible FAISS index** (31,102 verses, 66 books) — built at startup from public-domain JSON source
- **Three-tier retrieval cascade**: explicit verse reference → named passage map → semantic FAISS search
- **Range verse retrieval**: `Matthew 5:3-12` fetches all 10 Beatitudes in one lookup
- **Named passage mapping**: `"beatitudes"`, `"lord's prayer"`, `"ten commandments"`, `"23rd psalm"` auto-resolve to verse ranges
- **Book aliasing** (`Psalm` → `Psalms`) and false-positive filtering (regex word boundaries + known-book validation)
- **4 denomination-aware system prompts**: General, Catholic, Orthodox, Protestant — with denomination-specific short-circuit answers
- **5-layer pre-LLM moderation**: rewrite detection, hate/extremism, violence justification, adversarial injection, blasphemy
- **Fake verse detection**: verifies `Book N:V` against the FAISS index (token-overlap similarity, threshold 0.6)
- **Christian image generation**: Hugging Face Inference API (`black-forest-labs/FLUX.1-schnell`), prompt safety validator + enhancer, returns base64 data URL
- **Hallucination prevention**: every verse citation comes from FAISS-retrieved text, never LLM-generated

### Enterprise Security
- **JWT authentication** (HS256, 24h TTL) with **RBAC**: `admin`, `manager`, `employee`, `auditor`, `compliance`
- **Access control policies** per source via `data/access_policies.json`
- **PII detection + redaction** (SSN, credit card, email, phone, IP) in queries and answers
- **High-risk keyword flagging** (`password`, `secret`, `credential`, etc.)
- **Audit logging** — every query logged to `data/audit.log` (JSONL) with user, intent, PII findings
- **Per-query tracing** — trace persisted to `data/traces/{query_id}.json`; admin-only retrieval via `GET /debug/{query_id}`

### React UI
- Futuristic dark-mode interface with glassmorphism design
- Real-time upload with drag-and-drop + indexing progress
- Per-source filter — restrict answers to a specific document
- Christianity tab: denomination selector, image generator, scripture citation cards
- Collapsible "How this was generated" panel with reasoning trace
- Session memory, command palette (`⌘K`), voice input animation

---

## Quick Start (local)

```bash
# Backend (port 8000)
pip install -r requirements.txt
pip install python-multipart   # required for FastAPI file uploads
uvicorn app.api:app --reload --port 8000

# Frontend (port 3000)
cd frontend
npm install
npm start
```

Required env vars (or `.env` in repo root — do **not** commit it):
- `GROQ_API_KEY` — required at import time in `rag/llm.py`
- `HF_API_TOKEN` — required for image generation in `app/image_generator.py:84`
- `MONGO_URL` — optional (e.g. `mongodb://localhost:27017`) enables MongoDB audit log + trace persistence + `/analytics`; without it, flat-file mode (`data/audit.log` + `data/traces/`) is used
- `JWT_SECRET` — defaults to a dev-only value; set a real secret in production

**Note:** The KJV Bible index builds automatically on first startup. NLTK `punkt` + `punkt_tab` are downloaded on first import.

---

## Architecture

- **`app/`** — FastAPI service (entry point: `app.api:app`): auth/RBAC, upload, query, audit logging, event bus, MCP server, access policies
- **`rag/`** — shared RAG pipeline: vector store (FAISS + BM25 via RRF), chunker (Small-to-Big), smart retriever (multi-query + cross-encoder reranking), query router, sensitivity detector
- **`enterprise_rag_core/`** — shared library (v0.1.0) for microservices, installed as editable (`pip install -e ./enterprise_rag_core`)
- **`ingestion/`, `loaders/`** — multi-format ingestion (PDF/CSV/JSON), single entrypoint `ingestion_manager.py:ingest_file()`
- **`agents/`** — LangGraph (8-node) and CrewAI (3-agent) frameworks via `POST /agent/query`
- **`llm_providers/`** — pluggable LLM providers: Groq, OpenAI, Gemini, Claude, Ollama (fallback chain via `LLM_FALLBACK_CHAIN`)
- **`tasks/`** — Celery background ingestion (Redis broker)
- **`frontend/`** — React (Create React App) UI
- **`data/`** — runtime data (gitignored): uploaded files, FAISS index, Bible index, traces, audit log

## Tech Stack

| Layer | Tool |
|---|---|
| UI | React 18 + lucide-react |
| Backend | FastAPI + Uvicorn |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector DB | FAISS (dense) + BM25 (sparse) — fused via RRF |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| LLM | Groq — LLaMA-4 Maverick (fallback: `llama-3.1-8b-instant`) |
| Image Gen | Hugging Face — `black-forest-labs/FLUX.1-schnell` |
| Auth | JWT (HS256, 24h TTL) |
| File Parsing | PyPDF + csv + json |

---

## How It Works

### RAG Pipeline
```
PDF/CSV/JSON Upload
    │
    ▼
loader (auto-detect format) → page text + {source, page} metadata
    │
    ▼
chunker → small-to-big chunks (200ch / 1500ch)
    │
    ▼
vector_store → FAISS Index + BM25 + metadata store
    │
    ▼
User Query
    │
    ├── Self-RAG gate (greeting-like queries skip retrieval)
    ├── query_router → classify intent, tune top_k/rerank
    ├── semantic cache check
    ├── vector_store.hybrid_search → FAISS (0.6) + BM25 (0.4) → RRF fusion
    ├── smart_retriever → 2x query expansion + cross-encoder rerank
    └── context_builder → Lost-in-the-Middle ordering (max 4000 chars)
            │
            ▼
        prompt.py → grounded prompt → llm.py → Groq answer
            │
            ▼
    Answer + Source + Page Citations
```

### Christianity Pipeline
```
User Query
    │
    ├── Self-RAG Gate (skip retrieval for <4 greeting-like tokens)
    ├── PII Scanner → redact if found
    ├── High-Risk Query Check → flag for review
    │
    ├── 5-layer Moderation (all pre-LLM):
    │   1. Rewrite attempt? → block
    │   2. Hate/extremism? → block
    │   3. Violence justification? → block
    │   4. Adversarial injection? → block
    │   5. Blasphemy? → block
    │
    ├── Fake Verse Detection → verify Book N:V against FAISS
    │
    ├── Scripture Retrieval (3 tiers):
    │   Tier 1: Extract explicit verse refs (John 3:16, Matthew 5:3-12)
    │   Tier 2: Named passage lookup (→ "beatitudes" = Matthew 5:3-12)
    │   Tier 3: Semantic FAISS search (topic queries like "Beatitudes")
    │
    ├── Denomination-aware system prompt selection
    ├── Context assembly + RAG document context (if available)
    ├── LLM generation with grounded context
    └── Post-processing (disclaimer only when no sources + not historical)
```

---

## API Reference

### Main Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/login` | No | Authenticate, receive JWT |
| POST | `/upload` | JWT | Upload PDF/CSV/JSON (sets owner from authenticated user) |
| POST | `/query` | JWT | Query documents with optional source filter |
| POST | `/agent/query` | JWT | LangGraph or CrewAI pipeline (`agent_framework` field) |
| GET | `/sources` | JWT | List indexed documents |
| DELETE | `/sources/{filename}` | Admin | Remove document and rebuild index |
| GET | `/debug/{query_id}` | Admin | Per-query trace |
| DELETE | `/cache` | Admin | Clear semantic cache |
| GET | `/analytics` | Admin | Mongo-backed query analytics |

### Christianity Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/christianity/query` | JWT | Scripture-grounded Q&A with denomination context |
| POST | `/christianity/verify-verse` | JWT | Verify a Bible verse reference + text |
| POST | `/christianity/generate-image` | JWT | Generate Christian art via FLUX.1-schnell |
| GET | `/christianity/denominations` | No | List denomination options |
| GET | `/christianity/bible-stats` | JWT | Bible index statistics |

---

## AWS Deployment

Deployed to **ECS Fargate** (6 services: gateway, document-store, llm, bible, upload, agent) behind an ALB, with ElastiCache Redis, EC2 MongoDB, and a CloudFront + S3 frontend. CloudFront proxies API paths (`/login`, `/query`, `/sources`, `/christianity/*`, etc.) to the ALB so the SPA and API share one HTTPS origin (no mixed-content/CORS issues).

### Stop/Start (save costs)

```bash
for svc in enterprise-rag-gateway enterprise-rag-document-store enterprise-rag-llm \
           enterprise-rag-bible enterprise-rag-upload enterprise-rag-agent; do
  aws ecs update-service --cluster enterprise-rag-cluster --service $svc \
    --desired-count 0 --region ap-south-1   # 0 = stop, 1 = start
done
```

Restart takes ~3-5 min for the gateway to become healthy (boot, model load, FAISS + Mongo reconnect). The Bible index is cached on the shared `data/` volume so no re-embedding is needed.

---

## Evaluation

```bash
python eval.py --create-golden              # create golden question set (data/golden.json)
python eval.py --output eval-report.json    # RAGAS evaluation
```

- Judge LLM: Groq `llama-3.3-70b-versatile` via `LangchainLLMWrapper`
- Metrics: faithfulness, answer_relevancy, context_precision, context_recall
- Requires: `pip install ragas datasets langchain-groq langchain-huggingface`

---

## Default Users

| Username | Password | Role |
|---|---|---|
| admin | admin123 | admin |
| manager | manager123 | manager |
| employee | employee123 | employee |
| auditor | auditor123 | auditor |
