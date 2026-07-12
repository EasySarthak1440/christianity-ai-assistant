from chunker import smart_chunk
from cleaner import clean_text
from pdf_loader import load_pdfs
from vector_store import VectorStore


# return quantity(chunk-indixed) in vector store
def ingest_pdfs(file_paths: list[str], vector_store: VectorStore) -> int:
    all_chunks = []
    all_metadata = []

    pages = load_pdfs(file_paths)                     # [{text, source, page}, ...]

    for page in pages:
        cleaned = clean_text(page["text"])
        child_chunks, parent_chunks = smart_chunk(cleaned)   # Small-to-Big tuple

        for i, (child, parent) in enumerate(zip(child_chunks, parent_chunks)):
            all_chunks.append(child)
            all_metadata.append({
                "source":      page["source"],
                "page":        page["page"],
                "chunk_id":    f"{page['source']}_p{page['page']}_c{i}",
                "parent_text": parent,
            })

    vector_store.add(all_chunks, all_metadata)
    return len(all_chunks)

# wrapper for single pdf
def ingest_single_pdf(file_path: str, vector_store: VectorStore) -> int:
    return ingest_pdfs([file_path], vector_store)
