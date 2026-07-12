FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY enterprise_rag_core/ /app/enterprise_rag_core/
RUN pip install --no-cache-dir -e /app/enterprise_rag_core

COPY services/upload/ /app/

COPY app/ /app/app/
COPY rag/ /app/rag/
COPY tasks/ /app/tasks/
COPY ingestion/ /app/ingestion/
COPY loaders/ /app/loaders/

RUN pip install --no-cache-dir fastapi uvicorn httpx python-multipart pypdf celery redis

EXPOSE 8004

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8004"]
