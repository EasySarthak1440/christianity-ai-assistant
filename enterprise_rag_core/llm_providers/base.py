from __future__ import annotations

from abc import ABC, abstractmethod


class RateLimitFallbackError(Exception):
    pass


class LLMProvider(ABC):
    name: str = ""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0,
    ) -> str:
        ...
