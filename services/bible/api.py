from __future__ import annotations

import os
import re
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from enterprise_rag_core.shared_model import get_embedding_model

app = FastAPI(title="Bible Service", version="0.2.0")

DOCUMENT_STORE_URL = os.environ.get("DOCUMENT_STORE_URL", "")
LLM_SERVICE_URL = os.environ.get("LLM_SERVICE_URL", "")
_use_remote_vs = bool(DOCUMENT_STORE_URL)
_use_remote_llm = bool(LLM_SERVICE_URL)

_store = None
_SYSTEM_PROMPTS = {}
_DENOMINATION_LIST = []


class BibleQueryRequest(BaseModel):
    query: str
    denomination: str = "general"
    top_k: int = 10
    source_filter: Optional[str] = None


class VerifyVerseRequest(BaseModel):
    reference: str
    claimed_text: Optional[str] = None


class ImageGenRequest(BaseModel):
    prompt: str


@app.on_event("startup")
async def startup():
    global _store, _SYSTEM_PROMPTS, _DENOMINATION_LIST

    get_embedding_model()

    from scripture_rag import ScriptureStore
    _store = ScriptureStore()
    if _store.load():
        print(f"[Bible] Index ready ({_store.stats()['verses']} verses)")
    else:
        print("[Bible] No index found — will build on first query")
        try:
            from scripture_rag import BIBLE_JSON_URL
            _store.build_index(BIBLE_JSON_URL)
        except Exception as e:
            print(f"[Bible] Index build failed: {e}")

    from denomination_prompts import get_system_prompt, get_denominations
    _SYSTEM_PROMPTS = {"general", "catholic", "orthodox", "protestant"}
    _DENOMINATION_LIST = get_denominations()

    if _use_remote_vs:
        print(f"[Bible] Using remote document store: {DOCUMENT_STORE_URL}")
    if _use_remote_llm:
        print(f"[Bible] Using remote LLM: {LLM_SERVICE_URL}")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "bible_loaded": _store is not None and _store.loaded,
        "verses": _store.stats()["verses"] if _store and _store.loaded else 0,
    }


@app.post("/query")
async def query(req: BibleQueryRequest):
    if _store is None or not _store.loaded:
        raise HTTPException(503, "Bible store not initialized")

    q = req.query.strip()
    if not q:
        return {"error": "Query is required."}

    from moderation import moderation_check

    mod = moderation_check(q, _store if _store.loaded else None)
    if not mod["allowed"]:
        return {"query": q, "answer": mod["safe_response"], "denomination": req.denomination, "moderation": mod["reason"], "sources": []}

    from denomination_prompts import validate_denomination
    denom = validate_denomination(req.denomination)

    _DENOM_BOOK_ANSWERS = {
        ("catholic", "tobit"): (
            "Yes — in the Catholic tradition, the Book of Tobit is deuterocanonical "
            "scripture, part of the 73-book Catholic Bible."
        ),
    }
    q_lower = q.lower()
    for (denom_key, book_name), answer in _DENOM_BOOK_ANSWERS.items():
        if denom == denom_key and book_name in q_lower:
            return {"query": q, "answer": answer, "denomination": denom, "moderation": "", "sources": []}

    bible_refs = _store.extract_references(q) if _store.loaded else []
    scripture_context = ""
    verified_refs = []
    passage_matched = False

    if not bible_refs:
        passage = _store.lookup_passage(q) if _store.loaded else None
        if passage:
            passage_matched = True
            book, ch, vs_start, vs_end = passage
            verses = _store.search_range(book, ch, vs_start, vs_end)
            if verses:
                for v in verses:
                    scripture_context += f'{v["reference"]} (KJV) — {v["text"]}\n'
                    verified_refs.append({"reference": v["reference"], "text": v["text"]})
            else:
                anchor_ref = f"{book} {ch}:{vs_start}"
                verse = _store.search_exact(anchor_ref)
                if verse:
                    scripture_context += f'{verse["reference"]} (KJV) — {verse["text"]}\n'
                    verified_refs.append({"reference": verse["reference"], "text": verse["text"]})

    if not passage_matched:
        for ref in bible_refs:
            range_match = re.match(r"(\S+)\s+(\d+):(\d+)-(\d+)", ref)
            if range_match:
                book, ch_s, vs_start_s, vs_end_s = range_match.groups()
                ch, vs_start, vs_end = int(ch_s), int(vs_start_s), int(vs_end_s)
                verses = _store.search_range(book, ch, vs_start, vs_end)
                if verses:
                    for v in verses:
                        scripture_context += f'{v["reference"]} (KJV) — {v["text"]}\n'
                        verified_refs.append({"reference": v["reference"], "text": v["text"]})
                else:
                    anchor_ref = f"{book} {ch}:{vs_start}"
                    verse = _store.search_exact(anchor_ref)
                    if verse:
                        scripture_context += f'{verse["reference"]} (KJV) — {verse["text"]}\n'
                        verified_refs.append({"reference": verse["reference"], "text": verse["text"]})
            else:
                verse = _store.search_exact(ref)
                if verse:
                    scripture_context += f'{verse["reference"]} (KJV) — {verse["text"]}\n'
                    verified_refs.append({"reference": verse["reference"], "text": verse["text"]})
                else:
                    scripture_context += f"[Reference not found: {ref}]\n"

    if not bible_refs and not passage_matched and _store.loaded:
        similar = _store.search_similar(q, top_k=10)
        for v in similar:
            scripture_context += f'{v["reference"]} (KJV) — {v["text"]}\n'
            verified_refs.append({"reference": v["reference"], "text": v["text"]})

    from denomination_prompts import get_system_prompt
    system_prompt = get_system_prompt(denom)

    doc_context = ""
    rag_sources = []
    if _use_remote_vs:
        import httpx
        try:
            r = httpx.post(f"{DOCUMENT_STORE_URL}/search", json={"query": q, "top_k": 5}, timeout=10)
            results = r.json().get("results", [])
            if results:
                from context_builder import build_context
                doc_context = build_context([res["chunk"] for res in results], max_chars=2000)
                rag_sources = [{"source": res.get("source", ""), "page": res.get("page", 0)} for res in results]
        except Exception:
            pass
    else:
        from vector_store import VectorStore
        from rag_pipeline import run_rag
        from access_policy import resolve_permitted_sources
        from context_builder import build_context
        try:
            vs = VectorStore()
            vs.load("data/index")
            if vs.index is not None and vs.chunks:
                _, _, results = run_rag(query=q, vector_store=vs, source_filter=req.source_filter,
                                        permitted_sources=["*"], top_k=5, rerank=True)
                if results:
                    doc_context = build_context(results, max_chars=2000)
                    rag_sources = [{"source": r.get("source", ""), "page": r.get("page", 0)} for r in results]
        except Exception:
            pass

    combined_context = ""
    if scripture_context:
        combined_context += f"Verified Scripture References:\n{scripture_context}\n"
    if doc_context:
        combined_context += f"Document Context:\n{doc_context}\n"
    if not combined_context.strip():
        combined_context = "No specific context was retrieved for this query."

    full_prompt = f"{system_prompt}\n\nContext:\n{combined_context}\n\nQuestion: {q}\n\nAnswer:"

    if _use_remote_llm:
        import httpx
        try:
            r = httpx.post(f"{LLM_SERVICE_URL}/generate", json={"prompt": full_prompt}, timeout=30)
            answer = r.json().get("text", "")
        except Exception:
            from llm import generate_answer
            answer = generate_answer(full_prompt)
    else:
        from llm import generate_answer
        answer = generate_answer(full_prompt)

    sources_used = []
    if verified_refs:
        sources_used.append("KJV Bible")
        ref_list = ", ".join(r["reference"] for r in verified_refs)
        answer += f"\n\n[Scripture citations verified from KJV: {ref_list}]"
    if rag_sources:
        docs = ", ".join(set(s["source"] for s in rag_sources))
        sources_used.append(docs)
    if not sources_used and "[Historical claim — not scripture]" not in answer:
        answer += "\n\n*This response is grounded in scripture and historical sources. Always verify with your pastor or a trusted theological resource.*"

    return {
        "query": q,
        "answer": answer,
        "denomination": denom,
        "verified_refs": verified_refs,
        "sources": rag_sources,
        "moderation": "passed",
    }


@app.post("/verify-verse")
async def verify_verse(req: VerifyVerseRequest):
    if _store is None or not _store.loaded:
        raise HTTPException(503, "Bible store not initialized")
    result = _store.verify_verse(req.reference, req.claimed_text)
    return result


@app.get("/denominations")
async def list_denominations():
    from denomination_prompts import get_denominations
    return {"denominations": get_denominations()}


@app.get("/stats")
async def bible_stats():
    if _store is None or not _store.loaded:
        raise HTTPException(503, "Bible store not initialized")
    return _store.stats()


@app.post("/generate-image")
async def generate_image(req: ImageGenRequest):
    p = req.prompt.strip()
    if not p:
        return {"error": "Prompt is required."}
    from image_generator import validate_prompt as validate_image_prompt, generate_image as gen_img
    validation = validate_image_prompt(p)
    if not validation["allowed"]:
        return {"allowed": False, "reason": validation["reason"], "message": validation["safe_response"]}
    result = gen_img(validation["enhanced_prompt"])
    return {
        "allowed": True,
        "original_prompt": p,
        "enhanced_prompt": validation["enhanced_prompt"],
        "image_url": result.get("image_url"),
        "available": result.get("available", False),
        "message": result.get("message", ""),
    }
