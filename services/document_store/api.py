from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from enterprise_rag_core.shared_model import get_embedding_model
from enterprise_rag_core.vector_store import VectorStore

app = FastAPI(title="Document Store Service", version="0.2.0")

_store: VectorStore | None = None

DATA_DIR = Path("data")
INDEX_PATH = "data/index"


class SearchRequest(BaseModel):
    query: str
    top_k: int = 8
    source_filter: Optional[str] = None
    permitted_sources: Optional[list[str]] = None


class ChunkIn(BaseModel):
    text: str
    metadata: dict = {}


class AddRequest(BaseModel):
    chunks: list[ChunkIn]


@app.on_event("startup")
async def startup():
    global _store
    get_embedding_model()
    _store = VectorStore()
    if (DATA_DIR / "index.index").exists() and (DATA_DIR / "index.meta").exists():
        _store.load(INDEX_PATH)
        print(f"[DocumentStore] Loaded index — {_store.chunks} chunks, {len(_store.list_sources())} sources")
    else:
        print("[DocumentStore] No existing index — starting fresh")


@app.get("/health")
async def health():
    if _store is None:
        raise HTTPException(503, "Store not initialized")
    return {
        "status": "ok",
        "chunks": len(_store.chunks),
        "sources": len(_store.list_sources()),
    }


@app.post("/search")
async def search(req: SearchRequest):
    if _store is None:
        raise HTTPException(503, "Store not initialized")
    try:
        results = _store.search(
            query=req.query,
            top_k=req.top_k,
            source_filter=req.source_filter,
            permitted_sources=req.permitted_sources,
        )
        return {"results": results}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/add")
async def add(req: AddRequest):
    if _store is None:
        raise HTTPException(503, "Store not initialized")
    try:
        texts = [c.text for c in req.chunks]
        metadata_list = [c.metadata for c in req.chunks]
        _store.add(texts, metadata_list)
        _store.save(INDEX_PATH)
        return {"status": "ok", "chunks_added": len(texts)}
    except Exception as e:
        raise HTTPException(500, f"Add failed: {e}")


@app.delete("/sources/{filename:path}")
async def delete_source(filename: str):
    if _store is None:
        raise HTTPException(503, "Store not initialized")
    removed = _store.delete_source(filename)
    if removed == 0:
        raise HTTPException(404, f"Source '{filename}' not found")
    _store.save(INDEX_PATH)
    return {"status": "ok", "deleted": filename, "chunks_removed": removed}


@app.get("/sources")
async def list_sources():
    if _store is None:
        raise HTTPException(503, "Store not initialized")
    return {"sources": _store.list_sources()}


@app.get("/stats")
async def stats():
    if _store is None:
        raise HTTPException(503, "Store not initialized")
    return {
        "chunks": len(_store.chunks),
        "sources": _store.list_sources(),
        "source_count": len(_store.list_sources()),
        "dimension": 384,
    }
