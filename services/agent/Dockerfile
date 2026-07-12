FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY enterprise_rag_core/ /app/enterprise_rag_core/
RUN pip install --no-cache-dir -e /app/enterprise_rag_core

COPY services/agent/ /app/

COPY app/ /app/app/
COPY rag/ /app/rag/
COPY agents/ /app/agents/
COPY llm_providers/ /app/llm_providers/
COPY models/ /app/models/
COPY loaders/ /app/loaders/

RUN pip install --no-cache-dir fastapi uvicorn httpx langgraph langchain \
    langchain-community crewai crewai-tools groq openai anthropic google-generativeai

EXPOSE 8005

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8005"]
