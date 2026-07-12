from __future__ import annotations

import os
from typing import Optional

from llm_providers.base import LLMProvider
from llm_providers.groq_provider import GroqProvider
from llm_providers.openai_provider import OpenAIProvider
from llm_providers.gemini_provider import GeminiProvider
from llm_providers.claude_provider import ClaudeProvider
from llm_providers.ollama_provider import OllamaProvider

PROVIDER_REGISTRY: dict[str, type[LLMProvider]] = {
    "groq": GroqProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "claude": ClaudeProvider,
    "ollama": OllamaProvider,
}


def get_provider(name: str | None = None) -> LLMProvider:
    name = name or os.getenv("LLM_PROVIDER", "groq")
    cls = PROVIDER_REGISTRY.get(name)
    if cls is None:
        available = list(PROVIDER_REGISTRY.keys())
        raise ValueError(f"Unknown LLM provider '{name}'. Available: {available}")
    return cls()


def get_fallback_chain() -> list[LLMProvider]:
    chain = os.getenv("LLM_FALLBACK_CHAIN", "")
    if not chain:
        return []
    providers: list[LLMProvider] = []
    for name in chain.split(","):
        name = name.strip()
        if name in PROVIDER_REGISTRY:
            providers.append(PROVIDER_REGISTRY[name]())
    return providers
