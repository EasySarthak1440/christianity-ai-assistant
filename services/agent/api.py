from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from enterprise_rag_core.shared_model import get_embedding_model
from enterprise_rag_core.vector_store import VectorStore

app = FastAPI(title="Agent Orchestration Service", version="0.2.0")

DOCUMENT_STORE_URL = os.environ.get("DOCUMENT_STORE_URL", "")
LLM_SERVICE_URL = os.environ.get("LLM_SERVICE_URL", "")
_use_remote_vs = bool(DOCUMENT_STORE_URL)
_use_remote_llm = bool(LLM_SERVICE_URL)

_agent_graph = None


class AgentQueryRequest(BaseModel):
    query: str
    top_k: int = 10
    agent_framework: str = "langgraph"
    source_filter: Optional[str] = None
    username: str = "anonymous"
    user_role: str = "employee"


@app.on_event("startup")
async def startup():
    get_embedding_model()

    from app.cache import SemanticCache

    vs: VectorStore
    if _use_remote_vs:
        from app.gateway_clients import RemoteVectorStore
        vs = RemoteVectorStore(DOCUMENT_STORE_URL)
        vs.load()
    else:
        vs = VectorStore()
        index_path = "data/index"
        if os.path.exists(f"{index_path}.index"):
            vs.load(index_path)

    cache = SemanticCache()

    if _use_remote_llm:
        from app.gateway_clients import remote_generate
        from rag import llm as _llm_mod
        _llm_mod.generate_answer = remote_generate

    from agents.graph import create_agent_graph
    global _agent_graph
    _agent_graph = create_agent_graph(vs, cache)
    print(f"[Agent] Graph ready | vs={'remote' if _use_remote_vs else 'local'} llm={'remote' if _use_remote_llm else 'local'}")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "agent",
        "agents": ["langgraph", "crewai"],
        "graph_loaded": _agent_graph is not None,
    }


@app.post("/agent/query")
async def agent_query(req: AgentQueryRequest):
    if req.agent_framework == "crewai":
        from agents.crew import RAGCrew

        if _use_remote_vs:
            from app.gateway_clients import RemoteVectorStore
            vs = RemoteVectorStore(DOCUMENT_STORE_URL)
        else:
            vs = VectorStore()
            idx = "data/index"
            if os.path.exists(f"{idx}.index"):
                vs.load(idx)

        import asyncio
        crew = RAGCrew(vs=vs, query=req.query, top_k=req.top_k, source_filter=req.source_filter)
        result = await asyncio.to_thread(crew.run)
        return {"answer": result["answer"], "_framework": "crewai"}

    if _agent_graph is None:
        raise HTTPException(503, "Agent graph not initialized")

    initial_state = {
        "query": req.query,
        "source_filter": req.source_filter,
        "permitted_sources": [],
        "username": req.username,
        "user_role": req.user_role,
        "intent": "",
        "sensitivity": "safe",
        "retrieval_config": {},
        "results": [],
        "context": "",
        "answer": "",
        "similarity": {},
        "sources_summary": [],
        "pii_in_query": [],
        "pii_in_answer": [],
        "error": None,
        "query_id": "",
        "skip_retrieval": False,
        "cache_hit": False,
        "no_access": False,
        "final_output": None,
    }

    import uuid
    result = _agent_graph.invoke(initial_state, config={"configurable": {"thread_id": str(uuid.uuid4())}})
    output = result.get("final_output") or {
        "query": req.query,
        "answer": result.get("answer", ""),
        "similarity": result.get("similarity", {}),
        "sources": result.get("sources_summary", []),
        "_query_id": result.get("query_id", ""),
    }
    output["_framework"] = "langgraph"
    return output
