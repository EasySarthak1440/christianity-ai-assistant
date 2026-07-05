FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY enterprise_rag_core/ /app/enterprise_rag_core/
RUN pip install --no-cache-dir -e /app/enterprise_rag_core

COPY *.py .
COPY loaders/ loaders/
COPY llm_providers/ llm_providers/
COPY models/ models/

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
