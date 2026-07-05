FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY enterprise_rag_core/ /app/enterprise_rag_core/
RUN pip install --no-cache-dir -e /app/enterprise_rag_core

COPY services/agent/ /app/

# Agent graph + CrewAI + RAG pipeline modules
COPY agent_graph.py crew_agent.py vector_store.py shared_model.py \
     smart_retriever.py reranker.py filter.py context_builder.py \
     prompt.py llm.py similarity_scorer.py query_router.py \
     sensitivity_detector.py audit_logger.py cache.py access_policy.py \
     gateway_clients.py /app/

COPY llm_providers/ /app/llm_providers/
COPY models/ /app/models/
COPY loaders/ /app/loaders/

RUN pip install --no-cache-dir fastapi uvicorn httpx langgraph langchain \
    langchain-community crewai crewai-tools groq openai anthropic google-generativeai

EXPOSE 8005

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8005"]
