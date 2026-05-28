from vector_store import VectorStore
from smart_retriever import retrieve
from context_builder import build_context
from prompt import build_prompt
from llm import generate_answer
from similarity_scorer import score_answer

# (answer_str, results_list) | results_list carries { chunk, score, source, page, chunk_id }
def run_rag(
    query: str,
    vector_store: VectorStore,
    top_k: int = 8,
    source_filter: str | None = None,
    permitted_sources: list[str] | None = None,
    rerank: bool = True,
) -> tuple[str, list[dict]]:
    # 1. Retrieve + rerank
    results = retrieve(
        query=query,
        vector_store=vector_store,
        top_k=top_k,
        source_filter=source_filter,
        permitted_sources=permitted_sources,
        do_rerank=rerank,
    )

    if not results:
        return (
            "I couldn't find relevant information in the uploaded documents. "
            "Please try rephrasing your question or upload a relevant PDF.",
            {},
            [],
        )

    # 2. Build context string
    context = build_context(results) # basically makes string of all top_k results that matched (in FAISS) from retriever

    # 3. Build prompt
    prompt = build_prompt(context=context, question=query)

    # 4. Call LLM
    answer = generate_answer(prompt)

    similarity = score_answer(answer, results)
    return answer, similarity, results
