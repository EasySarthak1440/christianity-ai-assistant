import os
import concurrent.futures
from groq import Groq

from vector_store import VectorStore
from reranker import rerank
from filter import filter_chunks

_groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))
_RRF_K = 60

# returns [original, variant1, variant2].
def _generate_query_variants(query: str) -> list[str]:
    try:
        resp = _groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Generate exactly 2 alternative phrasings of the user's query. "
                        "Output only the 2 phrasings, one per line. No numbering, no explanations."
                    ),
                },
                {"role": "user", "content": query},
            ],
            temperature=0.4,
            max_tokens=120,
        )
        lines = [l.strip() for l in resp.choices[0].message.content.strip().splitlines() if l.strip()]
        variants = lines[:2]
        return [query] + variants
    except Exception as e:
        print(f"[MultiQuery] Groq call failed, using original only: {e}")
        return [query]

# Reciprocal Rank Fusion across multiple ranked result lists; deduplicates on chunk_id
def _rrf_fuse(result_lists: list[list[dict]], k: int = _RRF_K) -> list[dict]:
    rrf_scores: dict[str, float] = {}
    best_result: dict[str, dict] = {}

    for result_list in result_lists:
        for rank, r in enumerate(result_list):
            cid = r["chunk_id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (k + rank)
            if cid not in best_result:
                best_result[cid] = r

    ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    merged = []
    for cid, score in ranked:
        entry = dict(best_result[cid])
        entry["score"] = score
        merged.append(entry)

    return merged

# eduplicates on chunk_id
def retrieve(
    query: str,
    vector_store: VectorStore,
    top_k: int = 20,
    source_filter: str | None = None,
    permitted_sources: list[str] | None = None,
    do_rerank: bool = True,
) -> list[dict]:
    # Step 1 — Multi-Query variants
    queries = _generate_query_variants(query)

    # Step 2 — Parallel FAISS searches
    fetch_k = min(top_k * 3, len(vector_store.chunks) if vector_store.chunks else top_k * 3)

    def _search(q: str) -> list[dict]:
        return vector_store.search(
            query=q, top_k=fetch_k,
            source_filter=source_filter,
            permitted_sources=permitted_sources,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(queries)) as ex:
        result_lists = list(ex.map(_search, queries))

    # Remove empty lists
    result_lists = [r for r in result_lists if r]
    if not result_lists:
        return []

    # Step 3 — RRF fusion
    fused = _rrf_fuse(result_lists)

    if not fused:
        return []

    # Step 4 — Filter
    adapted = [{"text": r["chunk"], **r} for r in fused]
    filtered = filter_chunks(adapted, min_length=50)
    pool = filtered if filtered else adapted

    if do_rerank:
        reranked = rerank(query=query, chunks=pool, top_n=top_k)
        if not reranked:
            print("WARNING (smart_retriever): reranker returned empty")
            return pool[:3]
        return reranked

    return pool[:top_k]
