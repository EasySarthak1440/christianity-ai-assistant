# 🧠 RAG AI Knowledge Assistant

> Production-grade Retrieval-Augmented Generation system — multi-PDF, source-cited, hallucination-free.

A full-stack RAG application with a **futuristic React UI** and a **FastAPI backend**, built on a clean 12-module Python pipeline. Upload multiple PDFs, ask questions in natural language, and get grounded answers with exact source + page citations.

---

## ✨ Features

### 🤖 RAG Pipeline
- 📄 Multi-PDF ingestion with per-chunk `source` + `page` metadata
- 🧹 Text cleaning + smart sentence-aware chunking
- 🔎 Semantic search via **Sentence Transformers + FAISS**
- 🎯 Query rewriting + cross-encoder re-ranking (`ms-marco-MiniLM`)
- 🤖 Answer generation via **Groq LLaMA-4 Maverick** — grounded only to context
- 📌 Source + page citations returned with every answer

### 🖥️ React UI (Primary)
- Futuristic dark-mode interface with glassmorphism design
- Real-time PDF upload with drag-and-drop + indexing progress bar
- Per-source filter — restrict answers to a specific document
- Collapsible **"How this was generated"** reasoning panel
- Source cards panel showing filename + pages used
- Session memory panel, command palette (`⌘K`), voice input animation
- Toast notifications for upload/delete success and errors

### ⚙️ FastAPI Backend
- `POST /upload` — upload and index a PDF
- `POST /query` — query with optional per-source filter
- `GET /sources` — list all indexed documents
- `DELETE /sources/{filename}` — remove a PDF and rebuild the index
- CORS configured for React frontend at `localhost:3000`

### 🙏 Christianity AI Assistant
- Scripture-grounded answers with **KJV Bible FAISS index** (31K+ verses, 66 books)
- **Denomination-aware prompts**: General / Catholic / Orthodox / Protestant — selectable in UI
- **Moderation layer**: blocks verse rewriting, hateful content, adversarial injections, blasphemy, fake verses
- **Christian image generation**: DALL-E 3 with prompt safety validator
- **Hallucination prevention**: every verse citation retrieved from FAISS, never LLM-generated
- **Difficult questions**: contextual answers with denominational notes, no personal stance

---

## 📁 Folder Structure

```
rag-ai-knowledge-assistant/
│
├── api.py                 # FastAPI backend (port 8000)
├── mcp_server.py          # MCP server for AI agents (port 8002)
├── app.py                 # Streamlit UI (legacy, port 8501)
│
├── ingest.py              # Multi-PDF ingestion with metadata
├── pdf_loader.py          # Page-wise text extraction + source tagging
├── cleaner.py             # Text cleaning utilities
├── chunker.py             # Smart sentence-based chunking
├── vector_store.py        # FAISS vector DB with parallel metadata store
├── smart_retriever.py     # Query rewrite → FAISS search → rerank
├── reranker.py            # Cross-encoder re-ranking
├── filter.py              # Source-level filtering
├── context_builder.py     # Context string + source summary builder
├── prompt.py              # System + user prompt templates
├── llm.py                 # Groq LLM wrapper
├── rag_pipeline.py        # End-to-end RAG orchestration
├── query_rewrite.py       # Query rewriting logic
│
├── scripture_rag.py        # KJV Bible FAISS index + verse retrieval (NEW)
├── moderation.py           # Safety layer — pre-LLM checks (NEW)
├── denomination_prompts.py # Denomination-aware system prompts (NEW)
├── image_generator.py      # DALL-E 3 + prompt safety validator (NEW)
├── data/
│   ├── *.pdf              # Uploaded PDFs (runtime only, gitignored)
│   └── bible_index/       # KJV Bible FAISS index (built at startup)
│
├── frontend/
│   ├── src/
│   │   ├── App.js
│   │   ├── RAGInterface.jsx
│   │   └── components/
│   │       ├── DenominationSelector.jsx  (NEW)
│   │       ├── ImageGenerator.jsx        (NEW)
│   │       └── ScriptureCard.jsx         (NEW)
│   └── package.json
│
├── eval/
│   └── test_cases.json    # Christianity evaluation dataset (NEW)
├── docs/
│   └── ARCHITECTURE.md    # Architecture documentation (NEW)
├── requirements.txt
└── README.md
```

---

## ⚙️ Tech Stack

| Layer       | Tool                                  |
|-------------|---------------------------------------|
| UI          | React + lucide-react                  |
| Backend     | FastAPI + Uvicorn                     |
| Embeddings  | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector DB   | FAISS (in-memory)                     |
| Reranker    | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| LLM         | Groq — LLaMA-4 Maverick               |
| PDF Parsing | PyPDF                                 |
| Legacy UI   | Streamlit                             |
| MCP Server  | FastAPI-MCP                           |

---

## 🚀 How It Works

```
PDF Upload
    │
    ▼
pdf_loader.py  →  page text + {source, page} metadata
    │
    ▼
cleaner.py     →  normalized text
    │
    ▼
chunker.py     →  sentence-aware chunks (smart_chunk)
    │
    ▼
vector_store.py →  FAISS index + parallel metadata list
    │
    ▼
User Query
    │
    ├── query_rewrite.py   →  semantically clearer query
    ├── vector_store.search →  top-K FAISS results (+ optional source filter)
    ├── reranker.py        →  cross-encoder reranked top-N
    └── context_builder.py →  context string with [Source | Page] headers
            │
            ▼
        prompt.py  →  grounded prompt
            │
            ▼
        llm.py     →  Groq LLaMA-4 answer
            │
            ▼
    Answer + Source Citations
```

---

## ▶️ Running the App

### 1. Clone & Install

```bash
git clone [https://github.com/EasySarthak1440/rag-ai-knowledge-assistant.git](https://github.com/infra-builder-coder/rag-assistant.git)
cd rag-ai-knowledge-assistant
pip install -r requirements.txt
pip install python-multipart   # required for FastAPI file uploads
```

### 2. Set API Keys

**Groq API Key** (required for LLM):
```bash
export GROQ_API_KEY="your_groq_key_here"
```

**OpenAI API Key** (optional — for image generation):
```bash
export OPENAI_API_KEY="your_openai_key_here"
```

**Note**: The KJV Bible index builds automatically on first startup (~15s). No manual download needed.

**Linux / macOS**
```bash
export GROQ_API_KEY="your_api_key_here"
```

**Windows (PowerShell)**
```powershell
setx GROQ_API_KEY "your_api_key_here"
```

### 3. Start the Services

#### Terminal 1: Start FastAPI Backend (Main API for React)
```bash
uvicorn api:app --reload --port 8000
```

#### Terminal 2: Start MCP Server (for AI Agents)
```bash
python -m mcp_server
# or: uvicorn mcp_server:app --reload --port 8002
```

#### Terminal 3: Start React Frontend
```bash
cd frontend
npm install
npm start
```

Opens at `http://localhost:3000`

### Alternative: Streamlit UI (legacy)
```bash
streamlit run app.py
```

---

## 🔌 API Reference

### Main API (port 8000)
```
POST /upload
  Body: multipart/form-data { file: <PDF> }
  Returns: { filename, chunks, all_sources }

POST /query
  Body: { query: string, source_filter?: string }
  Returns: { answer, sources: [{ source, pages }] }

GET /sources
  Returns: { sources: [filename, ...] }

DELETE /sources/{filename}
  Returns: { message, remaining_sources }
```

### MCP Server (port 8002)
The MCP server exposes the same endpoints as MCP tools:
- `upload_pdf` → POST /upload
- `query_documents` → POST /query  
- `list_sources` → GET /sources
- `delete_document` → DELETE /sources/{filename}
- `get_stats` → GET /stats

**MCP Endpoint**: `http://localhost:8002/mcp` (for AI agent connection)

### Christianity Assistant (port 8000 — same backend)
```
POST /christianity/query
  Body: { query: string, denomination?: "general"|"catholic"|"orthodox"|"protestant", source_filter?: string }
  Returns: { answer, verified_refs, denomination, sources, moderation }

POST /christianity/verify-verse
  Body: { reference: string, claimed_text?: string }
  Returns: { verified, actual_text, reference, found }

POST /christianity/generate-image
  Body: { prompt: string }
  Returns: { allowed, image_url, enhanced_prompt, available }

GET /christianity/denominations
  Returns: { denominations: [{id, label, description}] }

GET /christianity/bible-stats
  Returns: { loaded, verses, books }
```

---

## ✅ What This Project Demonstrates

- Production RAG architecture — not a tutorial clone
- Clean separation of concerns across 12+ single-responsibility modules
- Metadata-aware vector store — every chunk knows its source and page
- Full-stack integration: React → FastAPI → Python ML pipeline
- LLM grounding and hallucination control
- Per-source filtering for multi-document knowledge bases
- Real-world API design with file upload, CRUD, and CORS
- MCP (Model Context Protocol) support for AI agent integration

---

