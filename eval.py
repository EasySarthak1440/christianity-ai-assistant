import numpy as np
import argparse
import json
import os
import sys
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

from vector_store import VectorStore
from rag_pipeline import run_rag
from context_builder import build_context

GOLDEN_PATH = "data/golden.json"
INDEX_PATH  = "data/index"
DATA_DIR    = "data"


def load_golden() -> list[dict]:
    if not os.path.exists(GOLDEN_PATH):
        print(f"[eval] Golden set not found at {GOLDEN_PATH}")
        print("Run: python eval.py --create-golden")
        sys.exit(1)
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        return json.load(f)


def create_golden_template(n: int = 25) -> None:
    if os.path.exists(GOLDEN_PATH):
        print(f"[eval] {GOLDEN_PATH} already exists. Delete it first to regenerate.")
        return
    template = [
        {
            "question": f"Question {i+1} — replace with a real question from your PDFs",
            "ground_truth": "Expected answer — be specific, use exact terms from the doc.",
            "source": None,
        }
        for i in range(n)
    ]
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(GOLDEN_PATH, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2)
    print(f"[eval] Template written to {GOLDEN_PATH}. Fill in questions + ground_truth, then run: python eval.py")


def _build_judge_llm():
    """
    LangchainLLMWrapper(ChatGroq) — bypasses instructor/structured-output entirely.
    instructor is what causes Groq 400 json_validate_failed errors in RAGAS 0.4.x.
    llm_factory uses instructor internally → incompatible with Groq.
    LangchainLLMWrapper uses plain chat completions → works.
    Requires: pip install langchain-groq
    """
    try:
        from ragas.llms import LangchainLLMWrapper
        from langchain_groq import ChatGroq
    except ImportError:
        print("[eval] Missing dep. Run: pip install langchain-groq")
        sys.exit(1)

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("[eval] GROQ_API_KEY not set.  Windows: set GROQ_API_KEY=your-key")
        sys.exit(1)

    return LangchainLLMWrapper(
        ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=api_key,
            temperature=0,
            max_tokens=1024,
        )
    )


def _build_judge_embeddings():
    """
    LangchainEmbeddingsWrapper(HuggingFaceEmbeddings) — exposes embed_query()
    which ragas answer_relevancy calls internally.
    Requires: pip install langchain-huggingface sentence-transformers
    """
    try:
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError:
        print("[eval] Missing dep. Run: pip install langchain-huggingface sentence-transformers")
        sys.exit(1)

    return LangchainEmbeddingsWrapper(
        HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    )


def run_eval(output_path: str | None = None) -> None:
    try:
        from ragas import evaluate
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        )
        from datasets import Dataset
    except ImportError:
        print("[eval] Missing dependencies. Run: pip install ragas datasets")
        sys.exit(1)

    golden = load_golden()

    vs = VectorStore()
    if not vs.load(INDEX_PATH):
        from ingestion_manager import ingest_file
        from pathlib import Path
        _SUPPORTED = {".pdf", ".csv", ".json"}
        docs = [
            os.path.join(DATA_DIR, f)
            for f in os.listdir(DATA_DIR)
            if Path(f).suffix.lower() in _SUPPORTED
        ]
        if not docs:
            print("[eval] No index and no documents found. Upload files first.")
            sys.exit(1)
        for p in docs:
            ingest_file(p, vs)

    print(f"[eval] Running {len(golden)} questions against pipeline...")

    eval_rows = []
    for i, item in enumerate(golden):
        q             = item["question"]
        ground_truth  = item["ground_truth"]
        source_filter = item.get("source")

        try:
            answer, similarity, results = run_rag(
                query=q,
                vector_store=vs,
                source_filter=source_filter,
            )
            contexts = [r.get("parent_text") or r["chunk"] for r in results]
        except Exception as e:
            print(f"[eval] Q{i+1} failed: {e}")
            answer   = ""
            contexts = []

        eval_rows.append({
            "question":     q,
            "answer":       answer,
            "contexts":     contexts,
            "ground_truth": ground_truth,
        })
        print(f"  [{i+1}/{len(golden)}] done — answer length: {len(answer)} chars")

    dataset = Dataset.from_list(eval_rows)

    judge_llm  = _build_judge_llm()
    judge_embs = _build_judge_embeddings()

    faithfulness.llm            = judge_llm
    context_precision.llm       = judge_llm
    context_recall.llm          = judge_llm
    answer_relevancy.llm        = judge_llm
    answer_relevancy.embeddings = judge_embs
    answer_relevancy.strictness = 1

    metrics = [faithfulness, answer_relevancy, context_precision, context_recall]

    print("\n[eval] Scoring with RAGAS (judge: Groq llama-3.3-70b-versatile)...")
    result = evaluate(dataset, metrics=metrics, raise_exceptions=False)

    report = {
        "timestamp":   datetime.utcnow().isoformat() + "Z",
        "judge_llm":   "groq/llama-3.3-70b-versatile",
        "judge_embs":  "all-MiniLM-L6-v2",
        "n_questions": len(golden),
        "scores": {
            "faithfulness":      round(float(np.nanmean(result["faithfulness"])), 4),
            "answer_relevancy":  round(float(np.nanmean(result["answer_relevancy"])), 4),
            "context_precision": round(float(np.nanmean(result["context_precision"])), 4),
            "context_recall":    round(float(np.nanmean(result["context_recall"])), 4),
        },
        "rows": eval_rows,
    }

    print("\n── RAGAS Results ──────────────────────────────────")
    for k, v in report["scores"].items():
        bar = ("█" * int(v * 20)) if (v == v) else "N/A (judge returned NaN)"
        print(f"  {k:<22} {v:.4f}  {bar}")
    print("───────────────────────────────────────────────────\n")

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"[eval] Results saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAGAS evaluation for RAG pipeline")
    parser.add_argument("--create-golden", action="store_true", help="Write golden set template")
    parser.add_argument("--n",      type=int, default=25,   help="Number of golden questions to template")
    parser.add_argument("--output", type=str, default=None, help="Save results to this JSON file")
    args = parser.parse_args()

    if args.create_golden:
        create_golden_template(n=args.n)
    else:
        run_eval(output_path=args.output)