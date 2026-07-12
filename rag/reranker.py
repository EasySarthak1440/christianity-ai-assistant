from sentence_transformers import CrossEncoder

reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", device="cpu")

def rerank(query, chunks, top_n=5):
    pairs = [(query, c["text"]) for c in chunks]
    scores = reranker.predict(pairs)

    ranked = sorted(
        zip(chunks, scores),
        key=lambda x: x[1],
        reverse=True
    )

    return [r[0] for r in ranked[:top_n]]
