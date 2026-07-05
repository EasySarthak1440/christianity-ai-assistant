from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

app = FastAPI(title="Upload Service", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

DOCUMENT_STORE_URL = os.environ.get("DOCUMENT_STORE_URL", "")
_use_remote_vs = bool(DOCUMENT_STORE_URL)

_SUPPORTED_EXTENSIONS = {".pdf", ".csv", ".json"}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "upload",
        "remote_doc_store": _use_remote_vs,
    }


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    async_mode: bool = Form(False),
    owner: str = Form("unknown"),
    classification: str = Form("internal"),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in _SUPPORTED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported format '{ext}'. Supported: {', '.join(_SUPPORTED_EXTENSIONS)}")

    file_path = DATA_DIR / file.filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    if async_mode:
        from tasks import ingest_document
        task = ingest_document.delay(str(file_path), owner=owner, classification=classification)
        return {
            "message": f"Indexing started for {file.filename}",
            "filename": file.filename,
            "task_id": task.id,
            "async": True,
        }

    from ingestion_manager import ingest_file
    from enterprise_rag_core.event_bus import get_event_bus

    if _use_remote_vs:
        import httpx
        chunks, chunk_data = _ingest_locally(str(file_path), owner, classification)
        r = httpx.post(f"{DOCUMENT_STORE_URL}/add", json={"chunks": chunk_data}, timeout=60)
        if r.status_code != 200:
            raise HTTPException(502, f"Document store rejected chunks: {r.text}")
        sources = [c["metadata"]["source"] for c in chunk_data]
        sources = list(set(sources))
    else:
        from vector_store import VectorStore
        vs = VectorStore()
        index_path = "data/index"
        if Path(f"{index_path}.index").exists():
            vs.load(index_path)
        count = ingest_file(str(file_path), vs, owner=owner, classification=classification)
        vs.save(index_path)
        sources = vs.list_sources()
        chunks = count
        get_event_bus().emit("document.uploaded", filename=file.filename, chunks=count, owner=owner)

    return {
        "message": f"Indexed {chunks} chunks from {file.filename}",
        "filename": file.filename,
        "chunks": chunks if isinstance(chunks, int) else len(chunks),
        "all_sources": sources,
    }


def _ingest_locally(file_path: str, owner: str, classification: str) -> tuple[int, list[dict]]:
    from loaders import load_file
    from cleaner import clean_text
    from chunker import smart_chunk

    pages = load_file(file_path)
    source = Path(file_path).name
    ext = Path(file_path).suffix.lower().lstrip(".")
    fmt_map = {"pdf": "pdf", "csv": "csv", "json": "json"}
    fmt = fmt_map.get(ext, ext)

    all_chunks = []
    chunk_data = []

    for page in pages:
        cleaned = clean_text(page["text"])
        child_chunks, parent_chunks = smart_chunk(cleaned)
        for i, (child, parent) in enumerate(zip(child_chunks, parent_chunks)):
            all_chunks.append(child)
            chunk_data.append({
                "text": child,
                "metadata": {
                    "source": source,
                    "page": page["page"],
                    "format": fmt,
                    "owner": owner,
                    "classification": classification,
                    "chunk_id": f"{source}_p{page['page']}_c{i}",
                    "parent_text": parent,
                },
            })

    return len(all_chunks), chunk_data
