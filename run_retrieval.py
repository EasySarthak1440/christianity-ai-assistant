import os
import sys

from ingestion.ingest import ingest_pdfs
from rag.vector_store import VectorStore

DATA_DIR = "data"
INDEX_PATH = os.path.join(DATA_DIR, "index")
vs = VectorStore()

# Try loading saved index first
if vs.load(INDEX_PATH):
    print(f"Loaded saved index with {len(vs.chunks)} chunks.")
else:
    # Fall back to ingesting all PDFs in data/
    pdf_files = [
        os.path.join(DATA_DIR, f)
        for f in os.listdir(DATA_DIR)
        if f.endswith(".pdf")
    ]
    if not pdf_files:
        print("No PDFs found in data/ and no saved index. Add a PDF to data/ and re-run.")
        sys.exit(1)

    total = ingest_pdfs(pdf_files, vs)
    print(f"Ingested {total} chunks from {len(pdf_files)} PDF(s).")

query = "What domain does rohit work in?"
results = vs.search(query)

for i, res in enumerate(results, 1):
    print(f"\nResult {i}")
    print(res["chunk"][:300])
    print("Source:", res["source"], "| Page:", res["page"])
