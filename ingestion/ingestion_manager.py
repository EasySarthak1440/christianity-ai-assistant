from pathlib import Path

from loaders import load_file
from rag.chunker import smart_chunk
from rag.cleaner import clean_text
from rag.vector_store import VectorStore


def ingest_file(
    file_path: str,
    vector_store: VectorStore,
    owner: str = "unknown",
    classification: str = "internal",
) -> int:
    pages = load_file(file_path)
    source = Path(file_path).name
    ext = Path(file_path).suffix.lower().lstrip(".")
    format_map = {"pdf": "pdf", "csv": "csv", "json": "json"}
    fmt = format_map.get(ext, ext)

    all_chunks = []
    all_metadata = []

    for page in pages:
        cleaned = clean_text(page["text"])
        child_chunks, parent_chunks = smart_chunk(cleaned)

        for i, (child, parent) in enumerate(zip(child_chunks, parent_chunks)):
            all_chunks.append(child)
            all_metadata.append({
                "source": source,
                "page": page["page"],
                "format": fmt,
                "owner": owner,
                "classification": classification,
                "chunk_id": f"{source}_p{page['page']}_c{i}",
                "parent_text": parent,
            })

    vector_store.add(all_chunks, all_metadata)
    return len(all_chunks)
