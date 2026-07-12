from __future__ import annotations

import os

import google.generativeai as genai

from enterprise_rag_core.llm_providers.base import LLMProvider


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self):
        genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
        self.model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0,
    ) -> str:
        model = genai.GenerativeModel(
            self.model_name,
            system_instruction=system_prompt,
        )
        resp = model.generate_content(
            prompt,
            generation_config={"temperature": temperature},
        )
        return resp.text
