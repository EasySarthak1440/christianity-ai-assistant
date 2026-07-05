from __future__ import annotations

import os
from dotenv import load_dotenv

from llm_providers import get_provider, get_fallback_chain
from llm_providers.base import RateLimitFallbackError

load_dotenv()
if not os.getenv("GROQ_API_KEY"):
    raise ValueError("GROQ_API_KEY environment variable not set")

_provider = None
_fallback_chain: list = []


def _get_provider():
    global _provider, _fallback_chain
    if _provider is None:
        _provider = get_provider(os.getenv("LLM_PROVIDER", "groq"))
        _fallback_chain = get_fallback_chain()
    return _provider


_token_log = {"total_tokens": 0, "requests": 0}


def get_token_stats() -> dict:
    return dict(_token_log)


def generate_answer(prompt, system_prompt=None):
    chain = [_get_provider()] + _fallback_chain
    for provider in chain:
        try:
            res = provider.generate(prompt, system_prompt=system_prompt)
            _token_log["requests"] += 1
            return res
        except RateLimitFallbackError:
            print(f"[LLM] {provider.name} rate-limited, trying fallback...")
            continue
        except Exception as e:
            print(f"[LLM] {provider.name} failed: {e}")
            continue

    _token_log["requests"] += 1
    return "Service is temporarily busy. Please try again in a few minutes."
