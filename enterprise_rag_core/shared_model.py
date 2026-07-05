from sentence_transformers import SentenceTransformer

EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
_model: SentenceTransformer = None


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print(f"[SharedModel]: Loading SentenceTransformer '{EMBED_MODEL_NAME}' (once)...")
        _model = SentenceTransformer(EMBED_MODEL_NAME)
    return _model
