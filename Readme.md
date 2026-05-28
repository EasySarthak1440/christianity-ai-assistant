# 🧠 Christianity AI Assistant

> Production-grade Retrieval-Augmented Generation system — multi-format ingestion, source-cited answers, Christianity AI assistant with scripture grounding, denomination awareness, and hallucination prevention.

A full-stack RAG application with a **futuristic React UI** and a **FastAPI backend**, built on a clean modular Python pipeline. Upload PDFs, CSVs, and JSONs; ask questions in natural language; or switch to Christianity mode for KJV Bible-grounded answers with denominational context.

---

## ✨ Features

### 🤖 RAG Pipeline
- 📄 Multi-format ingestion: **PDF**, **CSV**, **JSON** with per-chunk `source` + `page` metadata
- 🧹 Text cleaning + smart sentence-aware chunking (small-to-big: 200ch child / 1500ch parent)
- 🔎 Hybrid retrieval: **FAISS inner-product** (dense, weight 0.6) + **BM25** (sparse, weight 0.4) fused via **RRF**
- 🎯 Multi-query expansion (LLM generates 2 query variants) + **cross-encoder re-ranking** (`ms-marco-MiniLM-L-6-v2`)
- 🤖 Answer generation via **Groq LLaMA-4 Maverick** (with automatic rate-limit fallback to `llama-3.1-8b-instant`)
- 📌 Source + page citations returned with every answer
- ⚡ **Semantic cache** (threshold 0.95, max 512 entries, FIFO eviction) — auto-invalidated on upload/delete
- 🔀 **Query router** classifies intent (`fact_lookup`|`summarization`|`comparison`|`cross_source`|`data_analysis`) and tunes `top_k`/rerank per intent

### 🙏 Christianity AI Assistant — Full Feature Set

**Scripture Retrieval Engine**
- Dedicated **KJV Bible FAISS index** (31,102 verses, 66 books) — built at startup from public-domain JSON source
- **Three-tier retrieval cascade**: explicit verse reference → named passage map → semantic FAISS search
- **Range verse retrieval**: queries like `Matthew 5:3-12` fetch all 10 Beatitudes in a single lookup
- **Named passage mapping**: `"beatitudes"`, `"lord's prayer"`, `"ten commandments"`, `"23rd psalm"` auto-resolve to full verse ranges — no verse reference needed
- **Book aliasing**: `Psalm` → `Psalms` handled transparently
- **False-positive filtering**: regex word boundaries + known-Bible-book validation prevent matching non-scripture words like "John" in "does John know"

**Denomination Awareness**
- **4 system prompt variants**: General (66 books, neutral), Catholic (73 books + Deuterocanon, Magisterium), Orthodox (79 books, Septuagint-based, Holy Tradition), Protestant (66 books, Sola Scriptura)
- **Denomination-specific short-circuit answers**: e.g. Catholic + "Tobit" → direct deuterocanonical explanation (no LLM call)
- Selected via radio buttons in the UI, sent with every query

**5-Layer Moderation Pipeline** (all pre-LLM, saves tokens)
1. **Rewrite detection** — blocks attempts to modify scripture text
2. **Hate/extremism** — blocks racism, supremacist content
3. **Violence justification** — blocks using scripture to justify harm toward any group (patterns: "justify violence", "Bible to attack non-Christians", "scripture to kill")
4. **Adversarial injection** — blocks system prompt override attempts, "pretend", "ignore instructions"
5. **Blasphemy/heresy** — blocks disrespectful content about sacred figures

**Fake Verse Detection**
- Extracts `Book N:V` patterns from user input, retrieves actual text from FAISS, compares via token-overlap similarity (threshold 0.6)
- On mismatch: returns the real verse text and flags inaccuracy

**Christian Image Generation**
- Uses **Hugging Face Inference API** (`black-forest-labs/FLUX.1-schnell`) — not DALL-E
- **Prompt safety validator**: blocks disrespectful, violent, sexual, or political mixes with Christian themes
- **Prompt enhancer**: appends "in the style of classical Christian art, reverent" suffix to safe prompts
- Returns base64 data URL — no external storage needed

**Hallucination Prevention**
- System prompt explicitly instructs: *"Never generate a Bible verse from memory — every verse citation must come from the FAISS-retrieved text"*
- Verified verses injected as structured `[Reference (KJV) — text]` blocks into LLM context
- Self-RAG gate: ≤4 greeting-like tokens skip retrieval entirely
- Post-processing adds italic grounding disclaimer only when no sources are present
- Historical claims tagged with `[Historical claim — not scripture]` to prevent double-disclaimers

### 🔒 Enterprise Security
- **JWT authentication** (HS256, 24h TTL) with **RBAC**: `admin`, `manager`, `employee`, `auditor`, `compliance` roles
- **Access control policies** per source via `data/access_policies.json` — fine-grained source-level permissions
- **PII detection + redaction** (SSN, credit card, email, phone, IP) in both queries and answers
- **High-risk keyword flagging** (`password`, `secret`, `credential`, etc.)
- **Audit logging** — every query logged to `data/audit.log` (JSONL) with user, intent, PII findings
- **Per-query tracing** — trace persisted to `data/traces/{query_id}.json`; admin-only retrieval via `GET /debug/{query_id}`
- Rolling in-memory debug log capped at 200 entries

### 🖥️ React UI
- Futuristic dark-mode interface with glassmorphism design
- Real-time upload with drag-and-drop + indexing progress
- Per-source filter — restrict answers to a specific document
- **Christianity tab**: denomination selector, image generator, scripture citation cards
- **Smart citation display**: only shows Verified Scripture cards for verses actually cited in the LLM response (max 3 cards)
- Collapsible **"How this was generated"** panel with reasoning trace
- Source cards panel, session memory, command palette (`⌘K`), voice input animation
- Scroll-aware layout: `scrollTop = scrollHeight` + `overscrollBehavior:contain` prevents header hiding
- Send button works without uploaded documents (Christian queries don't require RAG docs)

### 🧪 Evaluation Framework
- **RAGAS** evaluation suite: faithfulness, answer_relevancy, context_precision, context_recall
- Judge LLM: Groq `llama-3.3-70b-versatile` via `LangchainLLMWrapper`
- Golden question set template (`eval/test_cases.json`): 8 evaluation queries spanning scripture lookup, cross-reference, denom questions
- Usage: `python eval.py --create-golden` → `python eval.py --output eval-report.json`

---

## 📁 Folder Structure

```
enterprise_rag_app/
│
├── api.py                      # FastAPI backend (port 8000) — all RAG + Christianity endpoints
│
├── ingest.py                   # Multi-format ingestion orchestration
├── ingestion_manager.py        # Single-entry ingest_file() — routes to format-specific loader
├── loaders/                    # Format-specific loaders (auto-detects PDF/CSV/JSON)
│   ├── registry.py
│   ├── pdf_loader.py
│   ├── csv_loader.py
│   └── json_loader.py
├── cleaner.py                  # Text cleaning
├── chunker.py                  # Small-to-Big chunking (200ch/1500ch, 100ch overlap, NLTK punkt)
├── vector_store.py             # FAISS + BM25 hybrid index with per-source metadata
├── smart_retriever.py          # Multi-query expansion + cross-encoder reranking
├── reranker.py                 # Cross-encoder re-ranking
├── filter.py                   # Source-level filtering
├── context_builder.py          # Lost-in-the-Middle ordering, max 4000 chars
├── prompt.py                   # Prompt templates
├── llm.py                      # Groq LLM wrapper with automatic rate-limit fallback
├── rag_pipeline.py             # End-to-end RAG orchestration
├── query_rewrite.py            # Query rewriting
│
├── auth.py                     # JWT authentication (HS256, 24h TTL)
├── access_policy.py            # RBAC source-level access control
├── cache.py                    # Semantic cache (0.95 threshold, FIFO eviction)
├── query_router.py             # Intent classification for retrieval tuning
├── sensitivity_detector.py     # PII detection + redaction + high-risk keywords
├── audit_logger.py             # JSONL audit log with user/intent/PII
├── similarity_scorer.py        # Answer-to-chunk similarity scoring
│
├── scripture_rag.py            # KJV Bible FAISS index + 3-tier retrieval
├── moderation.py               # 5-layer pre-LLM safety checks
├── denomination_prompts.py     # 4 denomination-aware system prompt variants
├── image_generator.py          # Hugging Face FLUX.1-schnell image generation
│
├── shared_model.py             # Singleton embedding model (all-MiniLM-L6-v2)
├── models/
│   ├── user.py                 # User model
│   └── role.py                 # Role enum (admin/manager/employee/auditor/compliance)
│
├── data/                       # Runtime data (gitignored)
│   ├── *.pdf, *.csv, *.json    # Uploaded files
│   ├── index/                  # Document FAISS index + metadata
│   ├── bible_index/            # KJV Bible FAISS index (31K verses, 66 books)
│   ├── traces/                 # Per-query debug traces (admin-only)
│   └── audit.log               # Query audit log (JSONL)
│
├── frontend/
│   ├── src/
│   │   ├── App.js
│   │   ├── RAGInterface.jsx     # Main UI — RAG + Christianity tabs
│   │   └── components/
│   │       ├── DenominationSelector.jsx  # 4-denomination radio group
│   │       ├── ImageGenerator.jsx        # HF FLUX image generation
│   │       └── ScriptureCard.jsx         # Verified/unverified verse card
│   └── package.json
│
├── eval/
│   ├── test_cases.json          # 8 evaluation test cases
│   └── eval.py                  # RAGAS evaluation runner
├── docs/
│   └── ARCHITECTURE.md          # Full architecture documentation
├── requirements.txt
├── Readme.md
└── AGENTS.md
```

---

## ⚙️ Tech Stack

| Layer            | Tool                                          |
|------------------|-----------------------------------------------|
| UI               | React 18 + lucide-react                       |
| Backend          | FastAPI + Uvicorn                             |
| Embeddings       | `sentence-transformers/all-MiniLM-L6-v2`       |
| Vector DB        | FAISS (dense) + BM25 (sparse) — fused via RRF |
| Reranker         | `cross-encoder/ms-marco-MiniLM-L-6-v2`        |
| LLM              | Groq — LLaMA-4 Maverick                       |
| Bible Embeddings | `all-MiniLM-L6-v2` (shared singleton)         |
| Image Gen        | Hugging Face — `black-forest-labs/FLUX.1-schnell` |
| Auth             | JWT (HS256, 24h TTL)                          |
| File Parsing     | PyPDF + csv + json                            |

---

## 🚀 How It Works

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
    ├── query_router → classify intent, tune top_k/rerank
    ├── vector_store.hybrid_search → FAISS (0.6) + BM25 (0.4) → RRF fusion
    ├── smart_retriever → 2x query expansion + cross-encoder rerank
    └── context_builder → Lost-in-the-Middle ordering (max 4000 chars)
            │
            ▼
        prompt.py → grounded prompt
            │
            ▼
        llm.py → Groq answer (with fallback on rate limit)
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
    ├── Moderation (5 checks — all pre-LLM):
    │   1. Rewrite attempt?          → block
    │   2. Hate/extremism?           → block
    │   3. Violence justification?   → block ("John 13:34")
    │   4. Adversarial injection?    → block
    │   5. Blasphemy?                → block
    │
    ├── Fake Verse Detection → verify Book N:V against FAISS
    │
    ├── Scripture Retrieval (3 tiers):
    │   Tier 1: Extract explicit verse refs (John 3:16, Matthew 5:3-12)
    │   Tier 2: Named passage lookup (→ "beatitudes" = Matthew 5:3-12)
    │   Tier 3: Semantic FAISS search (for topic queries like "Beatitudes")
    │
    ├── Denomination-aware system prompt selection
    ├── Context assembly + RAG document context (if available)
    ├── LLM generation with grounded context
    └── Post-processing (disclaimer only when no sources + not historical)
```

---

## ▶️ Running the App

### 1. Clone & Install

```bash
git clone <repo-url>
cd enterprise_rag_app
pip install -r requirements.txt
pip install python-multipart   # required for FastAPI file uploads
```

### 2. Set API Keys

```bash
export GROQ_API_KEY="your_groq_key_here"    # Required — LLM inference
export HF_API_TOKEN="your_hf_token_here"     # Required — image generation
```

A `.env` file in the repo root is also supported (loaded via `python-dotenv`).

**Note**: The KJV Bible index builds automatically on first startup (~15s). No manual download needed.

### 3. Start the Services

#### Terminal 1: FastAPI Backend (port 8000)
```bash
uvicorn api:app --reload --port 8000
```

#### Terminal 2: React Frontend (port 3000)
```bash
cd frontend
npm install
npm start
```

Opens at `http://localhost:3000`

---

## 🔌 API Reference

### Main Endpoints (port 8000)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/login` | No | Authenticate, receive JWT |
| POST | `/upload` | JWT | Upload PDF/CSV/JSON |
| POST | `/query` | JWT | Query documents with optional source filter |
| GET | `/sources` | JWT | List indexed documents |
| DELETE | `/sources/{filename}` | Admin | Remove document and rebuild index |
| GET | `/debug` | Admin | View debug log |
| GET | `/debug/{query_id}` | Admin | View specific query trace |
| DELETE | `/cache` | Admin | Clear semantic cache |

### Christianity Endpoints (port 8000)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/christianity/query` | JWT | Scripture-grounded Q&A with denomination context |
| POST | `/christianity/verify-verse` | JWT | Verify a Bible verse reference + text |
| POST | `/christianity/generate-image` | JWT | Generate Christian art via FLUX.1-schnell |
| GET | `/christianity/denominations` | No | List denomination options |
| GET | `/christianity/bible-stats` | JWT | Bible index statistics |

---

## 🔄 What This Project Demonstrates

- **Production RAG architecture** — not a tutorial clone; 20+ single-responsibility modules
- **Hybrid retrieval** — FAISS (dense) + BM25 (sparse) with RRF fusion and per-source filtering
- **Full-stack integration** — React → FastAPI → Python ML pipeline → LLM
- **Multi-format ingestion** — PDF, CSV, and JSON with auto-detection
- **Enterprise security** — JWT + RBAC + access policies + PII redaction + audit trails
- **Christianity-specific AI** — dedicated Bible FAISS index, 3-tier retrieval, 4-denomination support, 5-layer moderation, fake verse detection, image generation
- **Named passage resolution** — common passage names automatically resolved to verse ranges
- **Range and semantic retrieval** — `Matthew 5:3-12` and "Tell me about the Beatitudes" both work
- **Hallucination prevention** — every verse citation is FAISS-retrieved, never LLM-generated; fake verse detection blocks fabricated scripture
- **Hugging Face image generation** — `FLUX.1-schnell` via HF Inference API (not DALL-E)
- **RAGAS evaluation** — quantitative quality metrics with Groq judge LLM
- **Semantic caching** — avoids redundant LLM calls for similar queries
- **Query routing** — intent classification drives retrieval parameter tuning
