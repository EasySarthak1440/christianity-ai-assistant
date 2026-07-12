from sentence_transformers import util

from shared_model import get_embedding_model


# returns 'chunk', 'source', 'page'
def score_answer(answer: str, results: list[dict]) -> dict:
    if not answer or not results:
        return {"label": "LOW", "score": 0.0, "best_chunk": "", "best_source": "", "best_page": ""}

    model = get_embedding_model()

    answer_emb = model.encode(answer, convert_to_tensor=True)
    chunk_embs = model.encode([r["chunk"] for r in results], convert_to_tensor=True)

    scores    = util.cos_sim(answer_emb, chunk_embs)[0]
    best_idx  = int(scores.argmax())
    best_score = float(scores[best_idx])

    label = "HIGH" if best_score >= 0.75 else "MEDIUM" if best_score >= 0.50 else "LOW"

    return {
        "label":       label,
        "score":       round(best_score, 3),
        "best_chunk":  results[best_idx]["chunk"],
        "best_source": results[best_idx].get("source", ""),
        "best_page":   results[best_idx].get("page", ""),
    }
