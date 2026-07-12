import json
import os

from groq import Groq

_groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))
_INTENT_PROMPT = """You are a query classifier for an enterprise RAG system.
Given a user query, classify it into exactly one intent and return JSON:
{"intent": "fact_lookup"|"summarization"|"comparison"|"cross_source"|"data_analysis", "sensitivity": "safe"|"sensitive"}

Definitions:
- fact_lookup: specific fact, number, name, date retrieval
- summarization: "summarize", "overview", "what is this about"
- comparison: compare, contrast, difference between
- cross_source: combine info from multiple documents
- data_analysis: trends, patterns, aggregates over structured data
- sensitive: query contains PII, credentials, or confidential info

Return ONLY valid JSON, no explanation."""

def classify_query(query: str) -> dict:
    try:
        resp = _groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": _INTENT_PROMPT},
                {"role": "user", "content": query},
            ],
            temperature=0,
            max_tokens=80,
        )
        text = resp.choices[0].message.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"[QueryRouter] Fallback to default: {e}")
        return {"intent": "fact_lookup", "sensitivity": "safe"}

_INTENT_CONFIG = {
    "fact_lookup":    {"top_k": 8,  "rerank": True},
    "summarization":  {"top_k": 15, "rerank": False},
    "comparison":     {"top_k": 10, "rerank": True},
    "cross_source":   {"top_k": 12, "rerank": True},
    "data_analysis":  {"top_k": 10, "rerank": False},
}

def get_retrieval_config(intent: str) -> dict:
    return _INTENT_CONFIG.get(intent, _INTENT_CONFIG["fact_lookup"])
