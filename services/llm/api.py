from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from enterprise_rag_core.llm_providers import get_fallback_chain, get_provider
from enterprise_rag_core.llm_providers.base import RateLimitFallbackError

app = FastAPI(title="LLM Service", version="0.2.0")

_provider = None
_fallback_chain: list = []


class GenerateRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    temperature: float = 0.0


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    temperature: float = 0.0


class GenerateResponse(BaseModel):
    text: str
    provider: str


@app.on_event("startup")
async def startup():
    global _provider, _fallback_chain
    os.environ.setdefault("LLM_PROVIDER", "groq")
    _provider = get_provider(os.getenv("LLM_PROVIDER"))
    _fallback_chain = get_fallback_chain()
    print(f"[LLM] Provider: {type(_provider).__name__}, {len(_fallback_chain)} fallbacks")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "provider": type(_provider).__name__ if _provider else "none",
        "fallbacks": len(_fallback_chain),
    }


@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    if _provider is None:
        raise HTTPException(503, "LLM not initialized")

    chain = [_provider] + _fallback_chain
    for provider in chain:
        try:
            text = provider.generate(
                prompt=req.prompt,
                system_prompt=req.system_prompt,
                temperature=req.temperature,
            )
            return GenerateResponse(text=text, provider=provider.name)
        except RateLimitFallbackError:
            print(f"[LLM] {provider.name} rate-limited, trying fallback...")
            continue
        except Exception as e:
            print(f"[LLM] {provider.name} failed: {e}")
            continue

    raise HTTPException(503, "All LLM providers failed or rate-limited")


@app.post("/chat", response_model=GenerateResponse)
async def chat(req: ChatRequest):
    if _provider is None:
        raise HTTPException(503, "LLM not initialized")

    prompt = _format_chat_prompt(req.messages)
    chain = [_provider] + _fallback_chain
    for provider in chain:
        try:
            text = provider.generate(
                prompt=prompt,
                temperature=req.temperature,
            )
            return GenerateResponse(text=text, provider=provider.name)
        except RateLimitFallbackError:
            print(f"[LLM] {provider.name} rate-limited, trying fallback...")
            continue
        except Exception as e:
            print(f"[LLM] {provider.name} failed: {e}")
            continue

    raise HTTPException(503, "All LLM providers failed or rate-limited")


def _format_chat_prompt(messages: list[ChatMessage]) -> str:
    parts = []
    for msg in messages:
        role = msg.role.upper()
        parts.append(f"{role}: {msg.content}")
    parts.append("ASSISTANT:")
    return "\n\n".join(parts)
