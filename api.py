from __future__ import annotations
import re
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from ingestion_manager import ingest_file
from vector_store import VectorStore
from rag_pipeline import run_rag
from context_builder import build_sources_summary
from cache import SemanticCache
from auth import authenticate, create_token, decode_token
from access_policy import resolve_permitted_sources
from query_router import classify_query, get_retrieval_config
from sensitivity_detector import contains_pii, redact_pii, is_high_risk_query
from audit_logger import log_query
from models.user import User
from models.role import Role
from pathlib import Path
import os
import shutil
import uuid
import json

from agent_graph import create_agent_graph
from mcp_server import setup_mcp_server
from crew_agent import RAGCrew
from event_bus import get_event_bus
from celery.result import AsyncResult
from tasks import ingest_document

from scripture_rag import ScriptureStore, BIBLE_JSON_URL
from moderation import moderation_check
from denomination_prompts import get_system_prompt, get_denominations, validate_denomination
from image_generator import validate_prompt as validate_image_prompt, generate_image
from prompt import build_prompt
from llm import generate_answer

from gateway_clients import RemoteVectorStore, remote_generate, is_remote_vs, is_remote_llm

app = FastAPI()
_security = HTTPBearer(auto_error=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_use_remote_vs = is_remote_vs()
_use_remote_llm = is_remote_llm()

setup_mcp_server(app)

vs: VectorStore | RemoteVectorStore | None = None
_cache: SemanticCache | None = None
_agent_graph = None
event_bus = None
_debug_log: dict[str, dict] = {}
DATA_DIR = "data"
INDEX_PATH = os.path.join(DATA_DIR, "index")
scripture_store: ScriptureStore | None = None
_ready = False
_SUPPORTED_EXTENSIONS = {".pdf", ".csv", ".json"}

os.makedirs(DATA_DIR, exist_ok=True)


@app.middleware("http")
async def _ready_middleware(request, call_next):
    if not _ready and request.url.path != "/health":
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"status": "loading", "ready": False})
    return await call_next(request)


@app.on_event("startup")
async def _startup():
    import asyncio
    asyncio.create_task(_init_app())

async def _init_app():
    global vs, _cache, _agent_graph, event_bus, scripture_store, _ready

    if _use_remote_vs:
        print(f"[Gateway] Using remote vector store: {os.environ['DOCUMENT_STORE_URL']}")
        vs = RemoteVectorStore()
    else:
        print("[Gateway] Using local vector store")
        vs = VectorStore()

    if _use_remote_llm:
        print(f"[Gateway] Using remote LLM: {os.environ['LLM_SERVICE_URL']}")

    _cache = SemanticCache()
    _agent_graph = create_agent_graph(vs, _cache)
    event_bus = get_event_bus()

    scripture_store = ScriptureStore()
    if scripture_store.load():
        print(f"Bible index ready ({scripture_store.stats()['verses']} verses).")
    else:
        print("Building Bible index for the first time (this may take ~15s)...")
        try:
            scripture_store.build_index(BIBLE_JSON_URL)
        except Exception as e:
            print(f"Warning: Bible index build failed: {e}")

    if _use_remote_vs:
        vs.load()
        if vs.index is not None:
            print(f"[Gateway] Remote store ready — ~{len(vs.chunks)} chunks")
    else:
        if vs.load(INDEX_PATH):
            print(f"Loaded saved index with {len(vs.chunks)} chunks.")
        else:
            print("No saved index found. Loading documents...")
            existing = [
                os.path.join(DATA_DIR, f)
                for f in os.listdir(DATA_DIR)
                if Path(f).suffix.lower() in _SUPPORTED_EXTENSIONS
            ]
            if existing:
                for path in existing:
                    print(f"Loading: {path}")
                    ingest_file(path, vs)
                print(f"Vector store ready! {len(existing)} file(s) loaded.")
            else:
                print("No documents found — upload one via the UI.")

    from mongo_db import is_mongo_available, ensure_indexes
    if is_mongo_available():
        try:
            await ensure_indexes()
            print("[MongoDB] Indexes ready.")
        except Exception as e:
            print(f"[MongoDB] Index setup failed: {e}")

    _ready = True
    print("[Gateway] Startup complete — ready to serve requests.")

def _save_index() -> None:
    vs.save(INDEX_PATH)
    print(f"Index saved ({len(vs.chunks)} chunks).")

# ── auth helpers ────────────────────────────────────────────

def _get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_security),
) -> User | None:
    if creds is None:
        return None
    payload = decode_token(creds.credentials)
    if payload is None:
        return None
    return User(
        id=payload["sub"],
        username=payload["username"],
        password_hash="",
        role=Role(payload["role"]),
        department=payload.get("department", ""),
    )

def _require_user(user: User | None = Depends(_get_current_user)) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Send a Bearer token from POST /login.",
        )
    return user

# ── login ───────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/login")
def login(request: LoginRequest):
    user = authenticate(request.username, request.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )
    token = create_token(user)
    return {
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role.value,
            "department": user.department,
        },
    }

# ── upload ──────────────────────────────────────────────────

@app.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(_require_user),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in _SUPPORTED_EXTENSIONS:
        return {
            "error": f"Unsupported format '{ext}'. "
                     f"Supported: {', '.join(_SUPPORTED_EXTENSIONS)}"
        }

    dest = os.path.join(DATA_DIR, file.filename)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    async_mode = request.query_params.get("async", "0") == "1"
    if async_mode:
        task = ingest_document.delay(dest, owner=user.username, classification="internal")
        event_bus.emit("document.uploaded", filename=file.filename, task_id=task.id, owner=user.username, async_mode=True)
        return {
            "message": f"Indexing started for {file.filename}",
            "filename": file.filename,
            "task_id": task.id,
            "async": True,
            "owner": user.username,
        }

    count = ingest_file(dest, vs, owner=user.username, classification="internal")
    sources = vs.list_sources()
    _save_index()
    _cache.invalidate()

    event_bus.emit("document.uploaded", filename=file.filename, chunks=count, owner=user.username)

    return {
        "message": f"Indexed {count} chunks from {file.filename}",
        "filename": file.filename,
        "chunks": count,
        "all_sources": sources,
        "owner": user.username,
    }

# ── query ───────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str
    source_filter: str | None = None

@app.post("/query")
def query_endpoint(
    request: QueryRequest,
    user: User = Depends(_require_user),
):
    if vs.index is None:
        return {"error": "No documents indexed yet. Upload a file first."}

    # Self-RAG gate
    _GREET_TOKENS = {"hi", "hello", "hey", "thanks", "thank", "bye", "help", "what", "who", "are", "you"}
    lower_q = request.query.lower().strip()
    words = set(lower_q.split())
    if len(words) <= 4 and words.issubset(_GREET_TOKENS):
        return {
            "query": request.query,
            "answer": "I'm a document QA assistant. Ask me anything about the uploaded documents.",
            "similarity": {},
            "sources": [],
            "_self_rag": "skipped — non-document query",
            "_user": user.username,
        }

    # Semantic cache check
    hit = _cache.get(request.query)
    if hit:
        return hit

    # RBAC: resolve permitted sources for this user
    all_sources = vs.list_sources()
    permitted = resolve_permitted_sources(user, all_sources)
    if not permitted:
        return {
            "query": request.query,
            "answer": "You don't have access to any documents.",
            "similarity": {},
            "sources": [],
            "_user": user.username,
        }

    effective_filter = request.source_filter
    if effective_filter is not None and effective_filter not in permitted:
        effective_filter = None

    # Query routing: classify intent + sensitivity check
    route = classify_query(request.query)
    cfg = get_retrieval_config(route.get("intent", "fact_lookup"))
    sensitivity = route.get("sensitivity", "safe")

    # Pre-query PII / high-risk guard
    pii_in_query = contains_pii(request.query)
    risky = is_high_risk_query(request.query)

    # Full RAG run
    try:
        answer, similarity, results = run_rag(
            query=request.query,
            vector_store=vs,
            source_filter=effective_filter,
            permitted_sources=permitted,
            top_k=cfg["top_k"],
            rerank=cfg["rerank"],
        )
    except Exception as e:
        return {"error": f"Query failed: {str(e)}", "query": request.query}

    # Post-answer PII redaction
    pii_in_answer = contains_pii(answer)
    if pii_in_answer:
        answer = redact_pii(answer)

    sources = build_sources_summary(results)

    # Audit log
    log_query(
        user=user.username,
        query=request.query,
        intent=route.get("intent", "unknown"),
        sensitivity=sensitivity,
        sources_used=[s["source"] for s in sources],
        pii_found=pii_in_query + pii_in_answer,
        answer_preview=answer,
    )

    query_id = str(uuid.uuid4())[:8]
    trace = {
        "query_id": query_id,
        "timestamp": uuid.uuid1().hex[:8],
        "user": user.username,
        "intent": route.get("intent", "unknown"),
        "sensitivity": sensitivity,
        "query": request.query,
        "answer": answer,
        "similarity": similarity,
        "sources": sources,
        "results_count": len(results),
        "retrieval_config": cfg,
        "permitted_sources": permitted,
        "source_filter": effective_filter,
    }
    _debug_log[query_id] = trace
    if len(_debug_log) > 200:
        oldest = next(iter(_debug_log))
        del _debug_log[oldest]
    _save_trace(query_id, trace)

    _cache.set(request.query, answer, similarity, sources)

    event_bus.emit("query.executed", query_id=query_id, user=user.username, intent=route.get("intent", "unknown"))

    return {
        "query": request.query,
        "answer": answer,
        "similarity": similarity,
        "sources": sources,
        "_query_id": query_id,
        "_user": user.username,
    }

# ── agent query (LangGraph) ─────────────────────────────────

class AgentQueryRequest(BaseModel):
    query: str
    source_filter: str | None = None
    agent_framework: str = "langgraph"

@app.post("/agent/query")
def agent_query_endpoint(
    request: AgentQueryRequest,
    user: User = Depends(_require_user),
):
    if vs.index is None:
        return {"error": "No documents indexed yet. Upload a file first."}

    if request.agent_framework == "crewai":
        crew = RAGCrew(
            vs=vs,
            query=request.query,
            top_k=8,
            source_filter=request.source_filter,
        )
        result = crew.run()
        return {
            "query": request.query,
            "answer": result["answer"],
            "_framework": "crewai",
            "_user": user.username,
        }

    initial_state = {
        "query": request.query,
        "source_filter": request.source_filter,
        "permitted_sources": [],
        "username": user.username,
        "user_role": user.role.value,
        "intent": "",
        "sensitivity": "safe",
        "retrieval_config": {},
        "results": [],
        "context": "",
        "answer": "",
        "similarity": {},
        "sources_summary": [],
        "pii_in_query": [],
        "pii_in_answer": [],
        "error": None,
        "query_id": "",
        "skip_retrieval": False,
        "cache_hit": False,
        "no_access": False,
        "final_output": None,
    }

    result = _agent_graph.invoke(initial_state)
    output = result.get("final_output") or {
        "query": request.query,
        "answer": result.get("answer", ""),
        "similarity": result.get("similarity", {}),
        "sources": result.get("sources_summary", []),
        "_query_id": result.get("query_id", ""),
        "_user": user.username,
    }
    output["_framework"] = "langgraph"
    return output

# ── trace persistence ───────────────────────────────────────

_TRACES_DIR = os.path.join(DATA_DIR, "traces")
os.makedirs(_TRACES_DIR, exist_ok=True)

def _save_trace(query_id: str, trace: dict) -> None:
    path = os.path.join(_TRACES_DIR, f"{query_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2, default=str)
    from mongo_db import is_mongo_available, save_trace as mongo_save
    if is_mongo_available():
        import asyncio
        asyncio.ensure_future(mongo_save(query_id, trace))

# ── debug + cache (admin only) ──────────────────────────────

@app.get("/debug/{query_id}")
def debug_query(query_id: str, user: User = Depends(_require_user)):
    if user.role != Role.admin:
        raise HTTPException(status_code=403, detail="Admin only.")
    entry = _debug_log.get(query_id)
    if not entry:
        trace_path = os.path.join(_TRACES_DIR, f"{query_id}.json")
        if os.path.exists(trace_path):
            with open(trace_path, encoding="utf-8") as f:
                return json.load(f)
        from mongo_db import is_mongo_available, get_trace as mongo_get
        if is_mongo_available():
            import asyncio
            doc = asyncio.run(mongo_get(query_id))
            if doc:
                return doc
        return {"error": f"query_id '{query_id}' not found."}
    return entry

@app.get("/cache/stats")
def cache_stats(user: User = Depends(_require_user)):
    if user.role != Role.admin:
        raise HTTPException(status_code=403, detail="Admin only.")
    return _cache.stats()

@app.post("/cache/invalidate")
def cache_invalidate(user: User = Depends(_require_user)):
    if user.role != Role.admin:
        raise HTTPException(status_code=403, detail="Admin only.")
    _cache.invalidate()
    return {"message": "Cache cleared."}

# ── analytics (admin only, requires MongoDB) ─────────────────

class AnalyticsQuery(BaseModel):
    user: str | None = None
    intent: str | None = None
    days: int = 7
    limit: int = 50

@app.post("/analytics")
async def query_analytics(
    params: AnalyticsQuery,
    user: User = Depends(_require_user),
):
    if user.role != Role.admin:
        raise HTTPException(status_code=403, detail="Admin only.")
    from mongo_db import is_mongo_available, get_analytics
    if not is_mongo_available():
        return {"error": "MongoDB not configured. Set MONGO_URL env var."}
    return await get_analytics(
        user=params.user,
        intent=params.intent,
        days=params.days,
        limit=params.limit,
    )

# ── task status ──────────────────────────────────────────────

@app.get("/tasks/{task_id}")
def task_status(task_id: str, user: User = Depends(_require_user)):
    from celery_app import celery_app
    result = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "status": result.state,
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else None,
        "result": result.result if result.ready() else None,
    }

# ── health ──────────────────────────────────────────────────

@app.get("/health")
def health_check():
    if not _ready:
        return {"status": "loading", "ready": False}
    return {
        "status": "ok",
        "ready": True,
        "chunks": len(vs.chunks) if vs and vs.chunks else 0,
        "sources": len(vs.list_sources()) if vs and vs.index is not None else 0,
        "cache_entries": _cache.stats().get("entries", 0) if _cache else 0,
    }

# ── sources ─────────────────────────────────────────────────

@app.get("/sources")
def list_sources(user: User = Depends(_require_user)):
    all_sources = vs.list_sources()
    permitted = resolve_permitted_sources(user, all_sources)
    return {"sources": permitted, "_user": user.username}

# ── delete ──────────────────────────────────────────────────

@app.delete("/sources/{filename}")
def delete_source(
    filename: str,
    user: User = Depends(_require_user),
):
    if user.role != Role.admin:
        raise HTTPException(status_code=403, detail="Only admins can delete sources.")
    removed = vs.delete_source(filename)
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
    _save_index()
    _cache.invalidate()
    event_bus.emit("document.deleted", filename=filename, chunks_removed=removed)
    return {
        "message": f"Removed {filename}",
        "removed_chunks": removed,
        "remaining_sources": vs.list_sources(),
    }

# ═══════════════════════════════════════════════════════════
# Christianity AI Assistant routes
# ═══════════════════════════════════════════════════════════

class ChristianityQueryRequest(BaseModel):
    query: str
    denomination: str = "general"
    source_filter: str | None = None

@app.post("/christianity/query")
def christianity_query(
    request: ChristianityQueryRequest,
    user: User = Depends(_require_user),
):
    q = request.query.strip()
    if not q:
        return {"error": "Query is required."}

    denom = validate_denomination(request.denomination)

    # 1. Moderation check (runs before LLM)
    mod_result = moderation_check(q, scripture_store if scripture_store.loaded else None)
    if not mod_result["allowed"]:
        return {
            "query": q,
            "answer": mod_result["safe_response"],
            "denomination": denom,
            "moderation": mod_result["reason"],
            "sources": [],
        }

    # 1a. Denomination-specific book answers (short-circuit for known Q&A)
    _DENOM_BOOK_ANSWERS = {
        ("catholic", "tobit"): (
            "Yes — in the Catholic tradition, the Book of Tobit is deuterocanonical "
            "scripture, part of the 73-book Catholic Bible."
        ),
    }
    q_lower = q.lower()
    for (denom_key, book_name), answer in _DENOM_BOOK_ANSWERS.items():
        if denom == denom_key and book_name in q_lower:
            return {
                "query": q,
                "answer": answer,
                "denomination": denom,
                "moderation": "",
                "sources": [],
            }

    # 2. Extract Bible references from query
    bible_refs = scripture_store.extract_references(q) if scripture_store.loaded else []

    # 3. Look up each reference (supports ranges like Matthew 5:3-12)
    scripture_context = ""
    verified_refs = []
    passage_matched = False

    # 3a. Named passage lookup (only when no explicit refs found)
    if not bible_refs:
        passage = scripture_store.lookup_passage(q) if scripture_store.loaded else None
        if passage:
            passage_matched = True
            book, ch, vs_start, vs_end = passage
            verses = scripture_store.search_range(book, ch, vs_start, vs_end)
            if verses:
                for v in verses:
                    line = f'{v["reference"]} (KJV) — {v["text"]}\n'
                    scripture_context += line
                    verified_refs.append({"reference": v["reference"], "text": v["text"]})
            else:
                anchor_ref = f"{book} {ch}:{vs_start}"
                verse = scripture_store.search_exact(anchor_ref)
                if verse:
                    line = f'{verse["reference"]} (KJV) — {verse["text"]}\n'
                    scripture_context += line
                    verified_refs.append({"reference": verse["reference"], "text": verse["text"]})

    if not passage_matched:
        for ref in bible_refs:
            range_match = re.match(r"(\S+)\s+(\d+):(\d+)-(\d+)", ref)
            if range_match:
                book, ch_s, vs_start_s, vs_end_s = range_match.groups()
                ch, vs_start, vs_end = int(ch_s), int(vs_start_s), int(vs_end_s)
                verses = scripture_store.search_range(book, ch, vs_start, vs_end)
                if verses:
                    for v in verses:
                        line = f'{v["reference"]} (KJV) — {v["text"]}\n'
                        scripture_context += line
                        verified_refs.append({"reference": v["reference"], "text": v["text"]})
                else:
                    anchor_ref = f"{book} {ch}:{vs_start}"
                    verse = scripture_store.search_exact(anchor_ref)
                    if verse:
                        line = f'{verse["reference"]} (KJV) — {verse["text"]}\n'
                        scripture_context += line
                        verified_refs.append({"reference": verse["reference"], "text": verse["text"]})
            else:
                verse = scripture_store.search_exact(ref)
                if verse:
                    line = f'{verse["reference"]} (KJV) — {verse["text"]}\n'
                    scripture_context += line
                    verified_refs.append({"reference": verse["reference"], "text": verse["text"]})
                else:
                    scripture_context += f"[Reference not found: {ref}]\n"

    # 3b. Semantic fallback (only when no refs and no passage match)
    if not bible_refs and not passage_matched and scripture_store.loaded:
        similar_verses = scripture_store.search_similar(q, top_k=10)
        for v in similar_verses:
            ref_line = f'{v["reference"]} (KJV) — {v["text"]}\n'
            scripture_context += ref_line
            verified_refs.append({"reference": v["reference"], "text": v["text"]})

    # 4. Build denomination-aware system prompt
    system_prompt = get_system_prompt(denom)

    # 5. Run RAG on document store if available
    doc_context = ""
    rag_sources = []
    if vs.index is not None and vs.chunks:
        all_sources = vs.list_sources()
        permitted = resolve_permitted_sources(user, all_sources)
        if permitted:
            effective_filter = request.source_filter
            if effective_filter is not None and effective_filter not in permitted:
                effective_filter = None
            try:
                _, _, results = run_rag(
                    query=q,
                    vector_store=vs,
                    source_filter=effective_filter,
                    permitted_sources=permitted,
                    top_k=5,
                    rerank=True,
                )
                if results:
                    from context_builder import build_context
                    doc_context = build_context(results, max_chars=2000)
                    rag_sources = [{"source": r.get("source", ""), "page": r.get("page", 0)} for r in results]
            except Exception:
                pass

    # 6. Combine contexts
    combined_context = ""
    if scripture_context:
        combined_context += f"Verified Scripture References:\n{scripture_context}\n"
    if doc_context:
        combined_context += f"Document Context:\n{doc_context}\n"

    if not combined_context.strip():
        combined_context = "No specific context was retrieved for this query."

    # 7. Build prompt with denomination-aware system prompt
    full_prompt = (
        f"{system_prompt}\n\n"
        f"Context:\n{combined_context}\n\n"
        f"Question: {q}\n\n"
        f"Answer:"
    )

    # 8. Call LLM
    answer = remote_generate(full_prompt) if _use_remote_llm else generate_answer(full_prompt)

    # 9. Post-process: append grounding note
    sources_used = []
    if verified_refs:
        sources_used.append("KJV Bible")
        ref_list = ", ".join(r["reference"] for r in verified_refs)
        answer += f"\n\n[Scripture citations verified from KJV: {ref_list}]"
    if rag_sources:
        docs = ", ".join(set(s["source"] for s in rag_sources))
        sources_used.append(docs)

    if not sources_used and "[Historical claim — not scripture]" not in answer:
        answer += (
            "\n\n*This response is grounded in scripture and historical sources. "
            "Always verify with your pastor or a trusted theological resource.*"
        )

    return {
        "query": q,
        "answer": answer,
        "denomination": denom,
        "verified_refs": verified_refs,
        "sources": rag_sources,
        "moderation": "passed",
    }

class VerifyVerseRequest(BaseModel):
    reference: str
    claimed_text: str | None = None

@app.post("/christianity/verify-verse")
def verify_verse_endpoint(
    request: VerifyVerseRequest,
    user: User | None = Depends(_get_current_user),
):
    if not scripture_store.loaded:
        return {"error": "Bible index is not loaded."}
    result = scripture_store.verify_verse(request.reference, request.claimed_text)
    return result

@app.get("/christianity/denominations")
def list_denominations():
    return {"denominations": get_denominations()}

@app.get("/christianity/bible-stats")
def bible_stats(user: User = Depends(_require_user)):
    return scripture_store.stats()

class ImageGenRequest(BaseModel):
    prompt: str

@app.post("/christianity/generate-image")
def generate_christian_image(
    request: ImageGenRequest,
    user: User = Depends(_require_user),
):
    p = request.prompt.strip()
    if not p:
        return {"error": "Prompt is required."}

    # Safety validator
    validation = validate_image_prompt(p)
    if not validation["allowed"]:
        return {
            "allowed": False,
            "reason": validation["reason"],
            "message": validation["safe_response"],
        }

    result = generate_image(validation["enhanced_prompt"])
    return {
        "allowed": True,
        "original_prompt": p,
        "enhanced_prompt": validation["enhanced_prompt"],
        "image_url": result.get("image_url"),
        "available": result.get("available", False),
        "message": result.get("message", ""),
    }
