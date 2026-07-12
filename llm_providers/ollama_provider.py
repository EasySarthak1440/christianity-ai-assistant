from __future__ import annotations

import os

import httpx

from llm_providers.base import LLMProvider


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self):
        self.base_url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", "llama3.2")
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", "120"))

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0,
    ) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            r = httpx.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            r.raise_for_status()
            return r.json().get("response", "")
        except Exception as e:
            print(f"[OllamaProvider] {self.model} failed: {e}")
            return ""
