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
- `pip install -r requirements.txt` **then** `pip install python-multipart` (missing from requirements.txt, needed for `/upload`)
- Also missing from `requirements.txt`: `rank-bm25`, `python-dotenv` — already installed in this venv
- `HF_API_TOKEN` env var (or `.env` file) required for image generation in `image_generator.py:85` (uses Hugging Face Inference API via `huggingface_hub`)
- NLTK `punkt` + `punkt_tab` downloaded automatically on first `import chunker`

## Default Users (seeded to `data/users.json` on first `auth.py` import)

| Username   | Password      | Role     |
|------------|---------------|----------|
| admin      | admin123      | admin    |
| manager    | manager123    | manager  |
| employee   | employee123   | employee |
| auditor    | auditor123    | auditor  |

## Architecture

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

## Gotchas

- No formal Python lint/test suite — manual verification via UI
- Groq rate-limit fallback in `llm.py:36-41`: `llama-3.3-70b-versatile` → `llama-3.1-8b-instant` on `RateLimitError`
- Frontend is Create React App (`react-scripts 5.0.1`); tests via `npm test` in `frontend/`
- `pip install python-multipart` is required and easy to miss
- JWT default secret is `change-me-in-production-use-a-real-secret` (`auth.py:16`)
- `.env` file in this repo contains a real API key — do NOT commit it
