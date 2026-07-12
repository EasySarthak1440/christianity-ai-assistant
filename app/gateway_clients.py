from __future__ import annotations

import os
from typing import Any

import httpx

DOCUMENT_STORE_URL = os.environ.get("DOCUMENT_STORE_URL", "")
LLM_SERVICE_URL = os.environ.get("LLM_SERVICE_URL", "")

_USING_REMOTE_VS = bool(DOCUMENT_STORE_URL)
_USING_REMOTE_LLM = bool(LLM_SERVICE_URL)


def is_remote_vs() -> bool:
    return _USING_REMOTE_VS


def is_remote_llm() -> bool:
    return _USING_REMOTE_LLM


class RemoteVectorStore:
    """Transparent proxy for VectorStore that delegates to the document_store HTTP service."""

    def __init__(self, base_url: str = ""):
        self._base = base_url or DOCUMENT_STORE_URL
        self._chunks: list[str] = []
        self._index: Any = None

    @property
    def chunks(self) -> list[str]:
        return self._chunks

    @chunks.setter
    def chunks(self, val: list[str]) -> None:
        self._chunks = val

    @property
    def index(self) -> Any:
        return self._index

    @index.setter
    def index(self, val: Any) -> None:
        self._index = val

    def load(self, _path: str = "") -> bool:
        try:
            r = httpx.get(f"{self._base}/health", timeout=5)
            if r.status_code == 200:
                data = r.json()
                count = data.get("chunks", 0)
                if count > 0:
                    self._chunks = ["_"] * count
                    self._index = {}
                    return True
        except Exception:
            pass
        return False

    def save(self, _path: str = "") -> None:
        pass

    def list_sources(self) -> list[str]:
        try:
            r = httpx.get(f"{self._base}/sources", timeout=5)
            return r.json().get("sources", [])
        except Exception:
            return []

    def search(
        self,
        query: str,
        top_k: int = 8,
        source_filter: str | None = None,
        permitted_sources: list[str] | None = None,
    ) -> list[dict]:
        payload: dict[str, Any] = {"query": query, "top_k": top_k}
        if source_filter:
            payload["source_filter"] = source_filter
        if permitted_sources is not None:
            payload["permitted_sources"] = permitted_sources
        try:
            r = httpx.post(f"{self._base}/search", json=payload, timeout=10)
            return r.json().get("results", [])
        except Exception:
            return []

    def delete_source(self, source: str) -> int:
        try:
            r = httpx.delete(f"{self._base}/sources/{source}", timeout=10)
            return r.json().get("chunks_removed", 0)
        except Exception:
            return 0

    def add(
        self,
        chunks: list[str],
        metadata: list[dict] | None = None,
    ) -> None:
        if metadata is None:
            metadata = [{}] * len(chunks)
        chunk_list = [{"text": t, "metadata": m} for t, m in zip(chunks, metadata)]
        try:
            httpx.post(f"{self._base}/add", json={"chunks": chunk_list}, timeout=60)
        except Exception:
            pass


def remote_generate(prompt: str, system_prompt: str | None = None) -> str:
    payload: dict[str, Any] = {"prompt": prompt}
    if system_prompt is not None:
        payload["system_prompt"] = system_prompt
    try:
        r = httpx.post(f"{LLM_SERVICE_URL}/generate", json=payload, timeout=30)
        return r.json().get("text", "")
    except Exception:
        return ""
