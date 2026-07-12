from __future__ import annotations

import os
from pathlib import Path

from ingestion.ingestion_manager import ingest_file
from rag.vector_store import VectorStore

from .celery_app import celery_app

DATA_DIR = "data"
INDEX_PATH = os.path.join(DATA_DIR, "index")


@celery_app.task(bind=True)
def ingest_document(
    self,
    file_path: str,
    owner: str = "unknown",
    classification: str = "internal",
) -> dict:
    vs = VectorStore()
    if os.path.exists(f"{INDEX_PATH}.index"):
        vs.load(INDEX_PATH)

    count = ingest_file(file_path, vs, owner=owner, classification=classification)
    vs.save(INDEX_PATH)

    return {
        "chunks": count,
        "file": Path(file_path).name,
        "task_id": self.request.id,
    }


@celery_app.task(bind=True)
def rebuild_bible_index(self) -> dict:
    from app.scripture_rag import BIBLE_JSON_URL, ScriptureStore

    store = ScriptureStore()
    store.build_index(BIBLE_JSON_URL)
    stats = store.stats()
    return {"verses": stats.get("verses", 0), "task_id": self.request.id}


@celery_app.task(bind=True)
def generate_image_task(self, prompt: str) -> dict:
    from app.image_generator import generate_image

    result = generate_image(prompt)
    result["task_id"] = self.request.id
    return result
