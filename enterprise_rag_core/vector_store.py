from __future__ import annotations

import os
import pickle
import re

import faiss
import numpy as np
from rank_bm25 import BM25Okapi

from enterprise_rag_core.shared_model import get_embedding_model

_RRF_K = 60
_DENSE_WEIGHT = 0.6
_BM25_WEIGHT = 0.4


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


class VectorStore:
    def __init__(self):
        self.model = get_embedding_model()
        self.index = None
        self.bm25: BM25Okapi | None = None
        self.chunks: list[str] = []
        self.metadata: list[dict] = []

    def add(self, chunks: list[str], metadata: list[dict] | None = None) -> None:
        if not chunks:
            return
        if metadata is None:
            metadata = [{}] * len(chunks)

        embeddings = self._encode(chunks)
        if self.index is None:
            dim = embeddings.shape[1]
            self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings)

        self.chunks.extend(chunks)
        self.metadata.extend(metadata)

        self.bm25 = BM25Okapi([_tokenize(c) for c in self.chunks])

    def reset(self) -> None:
        self.index = None
        self.bm25 = None
        self.chunks = []
        self.metadata = []

    def search(
        self,
        query: str,
        top_k: int = 8,
        source_filter: str | None = None,
        permitted_sources: list[str] | None = None,
    ) -> list[dict]:
        if self.index is None or not self.chunks:
            return []

        fetch_k = min(top_k * 5 if source_filter else top_k * 3, len(self.chunks))

        query_vec = self._encode([query])
        dense_scores, dense_indices = self.index.search(query_vec, fetch_k)
        dense_rank: dict[int, int] = {}
        for rank, (idx, _) in enumerate(zip(dense_indices[0], dense_scores[0])):
            if idx != -1:
                dense_rank[int(idx)] = rank

        bm25_rank: dict[int, int] = {}
        if self.bm25 is not None:
            bm25_scores = self.bm25.get_scores(_tokenize(query))
            top_bm25 = np.argsort(bm25_scores)[::-1][:fetch_k]
            for rank, idx in enumerate(top_bm25):
                bm25_rank[int(idx)] = rank

        candidate_indices = set(dense_rank) | set(bm25_rank)
        rrf_scores: dict[int, float] = {}
        for idx in candidate_indices:
            score = 0.0
            if idx in dense_rank:
                score += _DENSE_WEIGHT / (_RRF_K + dense_rank[idx])
            if idx in bm25_rank:
                score += _BM25_WEIGHT / (_RRF_K + bm25_rank[idx])
            rrf_scores[idx] = score

        ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        results = []
        for idx, rrf_score in ranked:
            if idx >= len(self.chunks):
                continue
            meta = self.metadata[idx]
            src = meta.get("source", "unknown")
            if source_filter and src != source_filter:
                continue
            if permitted_sources is not None and src not in permitted_sources:
                continue
            results.append({
                "chunk":       self.chunks[idx],
                "parent_text": meta.get("parent_text"),
                "score":       rrf_score,
                "source":      meta.get("source", "unknown"),
                "page":        meta.get("page", 0),
                "chunk_id":    meta.get("chunk_id", str(idx)),
            })
            if len(results) == top_k:
                break

        return results

    def delete_source(self, source: str) -> int:
        if not self.chunks:
            return 0

        keep = [i for i, m in enumerate(self.metadata) if m.get("source") != source]
        removed = len(self.chunks) - len(keep)
        if removed == 0:
            return 0

        kept_vecs = np.array(
            [self.index.reconstruct(i) for i in keep], dtype="float32"
        ) if keep else None

        self.chunks   = [self.chunks[i]   for i in keep]
        self.metadata = [self.metadata[i] for i in keep]

        if kept_vecs is not None and len(kept_vecs) > 0:
            dim = kept_vecs.shape[1]
            self.index = faiss.IndexFlatIP(dim)
            self.index.add(kept_vecs)
            self.bm25 = BM25Okapi([_tokenize(c) for c in self.chunks])
        else:
            self.index = None
            self.bm25 = None

        return removed

    def list_sources(self) -> list[str]:
        return sorted({m.get("source", "unknown") for m in self.metadata})

    def save(self, path: str = "data/index") -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        if self.index is not None:
            faiss.write_index(self.index, f"{path}.index")
        with open(f"{path}.meta", "wb") as f:
            pickle.dump({"chunks": self.chunks, "metadata": self.metadata}, f)

    def load(self, path: str = "data/index") -> bool:
        index_path = f"{path}.index"
        meta_path  = f"{path}.meta"
        if not os.path.exists(index_path) or not os.path.exists(meta_path):
            return False

        self.index = faiss.read_index(index_path)
        with open(meta_path, "rb") as f:
            data = pickle.load(f)
            self.chunks   = data["chunks"]
            self.metadata = data["metadata"]

        if self.chunks:
            _DEFAULT_META = {"format": "pdf", "owner": "unknown", "classification": "internal"}
            for m in self.metadata:
                for k, v in _DEFAULT_META.items():
                    m.setdefault(k, v)

            print(f"[VectorStore] Rebuilding BM25 from {len(self.chunks)} chunks...")
            self.bm25 = BM25Okapi([_tokenize(c) for c in self.chunks])

        return True

    def _encode(self, texts: list[str]) -> np.ndarray:
        embeddings = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return embeddings.astype("float32")
