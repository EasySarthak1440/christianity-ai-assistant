from __future__ import annotations

import os
from groq import Groq, RateLimitError

from enterprise_rag_core.llm_providers.base import LLMProvider, RateLimitFallbackError


class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(self):
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        self.primary = "llama-3.3-70b-versatile"
        self.fallback = "llama-3.1-8b-instant"

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = self.client.chat.completions.create(
                model=self.primary,
                messages=messages,
                temperature=temperature,
            )
            return resp.choices[0].message.content
        except RateLimitError:
            try:
                resp = self.client.chat.completions.create(
                    model=self.fallback,
                    messages=messages,
                    temperature=temperature,
                )
                return resp.choices[0].message.content
            except RateLimitError:
                raise RateLimitFallbackError("All Groq models rate-limited")
