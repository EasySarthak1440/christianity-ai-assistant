from __future__ import annotations

import os

from anthropic import Anthropic

from enterprise_rag_core.llm_providers.base import LLMProvider


class ClaudeProvider(LLMProvider):
    name = "claude"

    def __init__(self):
        self.client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0,
    ) -> str:
        kwargs = dict(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        if system_prompt:
            kwargs["system"] = system_prompt
        resp = self.client.messages.create(**kwargs)
        return resp.content[0].text
