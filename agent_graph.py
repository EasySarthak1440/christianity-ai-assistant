from __future__ import annotations

import os
import uuid
import json
from typing import TypedDict, Optional, List, Dict, Any

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from vector_store import VectorStore
from smart_retriever import retrieve
from context_builder import build_context, build_sources_summary
from prompt import build_prompt
from llm import generate_answer
from similarity_scorer import score_answer
from query_router import classify_query, get_retrieval_config
from sensitivity_detector import contains_pii, redact_pii, is_high_risk_query
from cache import SemanticCache
from audit_logger import log_query

_GREET_TOKENS = {"hi", "hello", "hey", "thanks", "thank", "bye", "help", "what", "who", "are", "you"}
_TRACES_DIR = "data/traces"


class AgentState(TypedDict):
    query: str
    source_filter: Optional[str]
    permitted_sources: List[str]
    username: str
    user_role: str
    intent: str
    sensitivity: str
    retrieval_config: dict
    results: List[dict]
    context: str
    answer: str
    similarity: dict
    sources_summary: List[dict]
    pii_in_query: List[dict]
    pii_in_answer: List[dict]
    error: Optional[str]
    query_id: str
    skip_retrieval: bool
    cache_hit: bool
    no_access: bool
    final_output: Optional[dict]


def _save_trace(query_id: str, trace: dict) -> None:
    os.makedirs(_TRACES_DIR, exist_ok=True)
    path = os.path.join(_TRACES_DIR, f"{query_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2, default=str)
    from mongo_db import is_mongo_available, save_trace as mongo_save
    if is_mongo_available():
        import asyncio
        asyncio.ensure_future(mongo_save(query_id, trace))


def self_rag_gate_node(state: AgentState, _config=None) -> dict:
    q = state["query"].lower().strip()
    words = set(q.split())
    if len(words) <= 4 and words.issubset(_GREET_TOKENS):
        return {
            "skip_retrieval": True,
            "answer": "I'm a document QA assistant. Ask me anything about the uploaded documents.",
            "results": [],
            "similarity": {},
            "sources_summary": [],
        }
    return {"skip_retrieval": False}


def query_router_node(state: AgentState, _config=None) -> dict:
    route = classify_query(state["query"])
    cfg = get_retrieval_config(route.get("intent", "fact_lookup"))
    return {
        "intent": route.get("intent", "fact_lookup"),
        "sensitivity": route.get("sensitivity", "safe"),
        "retrieval_config": cfg,
    }


def cache_check_node(state: AgentState, _config=None) -> dict:
    cache = _get_cache()
    hit = cache.get(state["query"])
    if hit:
        return {
            "cache_hit": True,
            "answer": hit["answer"],
            "similarity": hit.get("similarity", {}),
            "sources_summary": hit.get("sources", []),
        }
    return {"cache_hit": False}


def rbac_filter_node(state: AgentState, _config=None) -> dict:
    all_sources = _get_vs().list_sources()
    from access_policy import resolve_permitted_sources
    from models.user import User
    from models.role import Role
    user = User(id="", username=state["username"], password_hash="", role=Role(state["user_role"]), department="")
    permitted = resolve_permitted_sources(user, all_sources)
    if not permitted:
        return {
            "no_access": True,
            "answer": "You don't have access to any documents.",
            "results": [],
            "similarity": {},
            "sources_summary": [],
        }
    effective_filter = state.get("source_filter")
    if effective_filter is not None and effective_filter not in permitted:
        effective_filter = None
    return {"no_access": False, "permitted_sources": permitted, "source_filter": effective_filter}


def retrieval_agent_node(state: AgentState, _config=None) -> dict:
    cfg = state["retrieval_config"]
    try:
        results = retrieve(
            query=state["query"],
            vector_store=_get_vs(),
            top_k=cfg["top_k"],
            source_filter=state.get("source_filter"),
            permitted_sources=state.get("permitted_sources"),
            do_rerank=cfg["rerank"],
        )
    except Exception as e:
        return {"error": str(e), "results": []}

    if not results:
        return {
            "results": [],
            "answer": "I couldn't find relevant information in the uploaded documents. Please try rephrasing your question or upload a relevant file.",
            "similarity": {},
            "sources_summary": [],
        }
    return {"results": results, "error": None}


def context_builder_node(state: AgentState, _config=None) -> dict:
    results = state.get("results", [])
    if not results:
        return {"context": ""}
    context = build_context(results)
    return {"context": context}


def answer_generator_node(state: AgentState, _config=None) -> dict:
    if state.get("answer"):
        return {}

    prompt = build_prompt(context=state.get("context", ""), question=state["query"])
    answer = generate_answer(prompt)

    results = state.get("results", [])
    similarity = score_answer(answer, results) if results else {}

    pii_in_answer = contains_pii(answer)
    if pii_in_answer:
        answer = redact_pii(answer)

    return {
        "answer": answer,
        "similarity": similarity,
        "pii_in_answer": pii_in_answer,
    }


def output_formatter_node(state: AgentState, _config=None) -> dict:
    qid = str(uuid.uuid4())[:8]
    sources = build_sources_summary(state.get("results", [])) if state.get("results") else state.get("sources_summary", [])

    log_query(
        user=state["username"],
        query=state["query"],
        intent=state.get("intent", "unknown"),
        sensitivity=state.get("sensitivity", "safe"),
        sources_used=[s["source"] for s in sources],
        pii_found=state.get("pii_in_query", []) + state.get("pii_in_answer", []),
        answer_preview=state.get("answer", ""),
    )

    trace = {
        "query_id": qid,
        "timestamp": uuid.uuid1().hex[:8],
        "user": state["username"],
        "intent": state.get("intent", "unknown"),
        "sensitivity": state.get("sensitivity", "safe"),
        "query": state["query"],
        "answer": state.get("answer", ""),
        "similarity": state.get("similarity", {}),
        "sources": sources,
        "results_count": len(state.get("results", [])),
        "retrieval_config": state.get("retrieval_config", {}),
        "permitted_sources": state.get("permitted_sources", []),
        "source_filter": state.get("source_filter"),
    }
    _save_trace(qid, trace)

    if not state.get("skip_retrieval") and not state.get("cache_hit") and not state.get("no_access") and state.get("answer"):
        cache = _get_cache()
        cache.set(state["query"], state["answer"], state.get("similarity", {}), sources)

    output = {
        "query": state["query"],
        "answer": state.get("answer", ""),
        "similarity": state.get("similarity", {}),
        "sources": sources,
        "_query_id": qid,
        "_user": state["username"],
    }
    if state.get("cache_hit"):
        output["_cache_hit"] = True
    if state.get("skip_retrieval"):
        output["_self_rag"] = "skipped — non-document query"
    if state.get("error"):
        output["_error"] = state["error"]

    return {"final_output": output, "query_id": qid}


def route_after_gate(state: AgentState) -> str:
    return "output_formatter" if state.get("skip_retrieval") else "query_router"


def route_after_cache(state: AgentState) -> str:
    return "output_formatter" if state.get("cache_hit") else "rbac_filter"


def route_after_rbac(state: AgentState) -> str:
    return "output_formatter" if state.get("no_access") else "retrieval_agent"


_vs_instance: VectorStore | None = None
_cache_instance: SemanticCache | None = None


def _get_vs() -> VectorStore:
    global _vs_instance
    assert _vs_instance is not None, "VectorStore not set — call create_agent_graph(vs)"
    return _vs_instance


def _get_cache() -> SemanticCache:
    global _cache_instance
    assert _cache_instance is not None, "SemanticCache not set — call create_agent_graph(vs, cache)"
    return _cache_instance


def create_agent_graph(vs: VectorStore, cache: SemanticCache | None = None) -> StateGraph:
    global _vs_instance, _cache_instance
    _vs_instance = vs
    _cache_instance = cache or SemanticCache()

    workflow = StateGraph(AgentState)

    workflow.add_node("self_rag_gate", self_rag_gate_node)
    workflow.add_node("query_router", query_router_node)
    workflow.add_node("cache_check", cache_check_node)
    workflow.add_node("rbac_filter", rbac_filter_node)
    workflow.add_node("retrieval_agent", retrieval_agent_node)
    workflow.add_node("context_builder", context_builder_node)
    workflow.add_node("answer_generator", answer_generator_node)
    workflow.add_node("output_formatter", output_formatter_node)

    workflow.set_entry_point("self_rag_gate")

    workflow.add_conditional_edges(
        "self_rag_gate",
        route_after_gate,
        {"query_router": "query_router", "output_formatter": "output_formatter"},
    )

    workflow.add_edge("query_router", "cache_check")

    workflow.add_conditional_edges(
        "cache_check",
        route_after_cache,
        {"rbac_filter": "rbac_filter", "output_formatter": "output_formatter"},
    )

    workflow.add_conditional_edges(
        "rbac_filter",
        route_after_rbac,
        {"retrieval_agent": "retrieval_agent", "output_formatter": "output_formatter"},
    )

    workflow.add_edge("retrieval_agent", "context_builder")
    workflow.add_edge("context_builder", "answer_generator")
    workflow.add_edge("answer_generator", "output_formatter")
    workflow.add_edge("output_formatter", END)

    return workflow.compile(checkpointer=MemorySaver())
