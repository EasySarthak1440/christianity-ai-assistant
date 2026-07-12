import numpy as np

from shared_model import get_embedding_model


class SemanticCache:
    def __init__(self, threshold: float = 0.95, max_size: int = 512):
        self.threshold = threshold
        self.max_size = max_size
        self._entries: list[dict] = []  # [{emb, query, answer, similarity, sources}]

    def _embed(self, query: str) -> np.ndarray:
        model = get_embedding_model()
        emb = model.encode(query, convert_to_numpy=True, normalize_embeddings=True)
        return emb.astype("float32")

    # return cached response dict if a sufficiently similar query exists | none
    def get(self, query: str) -> dict | None:
        if not self._entries:
            return None

        query_emb = self._embed(query)

        cached_embs = np.stack([e["emb"] for e in self._entries])  # (N, D)
        scores = cached_embs @ query_emb                            # (N,)

        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])

        if best_score >= self.threshold:
            entry = self._entries[best_idx]
            print(
                f"[SemanticCache] HIT — score={best_score:.4f} "
                f"matched: '{entry['query'][:60]}'"
            )
            return {
                "query":      query,
                "answer":     entry["answer"],
                "similarity": entry["similarity"],
                "sources":    entry["sources"],
                "_cache_hit": True,
                "_cache_score": round(best_score, 4),
            }

        return None

    # store query & rag-response
    def set(self, query: str, answer: str, similarity: dict, sources: list) -> None:
        emb = self._embed(query)

        if len(self._entries) >= self.max_size:
            self._entries.pop(0)  # FIFO eviction

        self._entries.append({
            "emb":        emb,
            "query":      query,
            "answer":     answer,
            "similarity": similarity,
            "sources":    sources,
        })
        print(f"[SemanticCache] SET — cache size: {len(self._entries)}/{self.max_size}")

    # reset cache on upload
    def invalidate(self) -> None:
        count = len(self._entries)
        self._entries = []
        print(f"[SemanticCache] INVALIDATED — cleared {count} entries.")

    def stats(self) -> dict:
        return {"entries": len(self._entries), "threshold": self.threshold, "max_size": self.max_size}
