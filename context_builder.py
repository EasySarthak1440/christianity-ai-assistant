# concatenate retrieved results into a single LLM-ready context string.
def build_context(results: list[dict], max_chars: int = 4000) -> str:
    if not results:
        return ""

    # Lost-in-Middle ordering: best first, second-best last, rest in middle
    if len(results) == 1:
        ordered = results
    elif len(results) == 2:
        ordered = [results[0], results[1]]
    else:
        ordered = [results[0]] + results[2:] + [results[1]]

    context_parts = []
    total = 0

    for r in ordered:
        # Small-to-Big: use parent_text if available, else fall back to chunk
        body = r.get("parent_text") or r["chunk"]
        header = f"[Source: {r['source']} | Page {r['page']}]"
        block = f"{header}\n{body}"
        if total + len(block) > max_chars:
            break
        context_parts.append(block)
        total += len(block)

    return "\n\n---\n\n".join(context_parts)

# uniquely summarization
def build_sources_summary(results: list[dict]) -> list[dict]:
    seen: dict[str, set] = {}
    for r in results:
        src = r.get("source", "unknown")
        page = r.get("page", 0)
        seen.setdefault(src, set()).add(page)

    return [
        {"source": src, "pages": sorted(pages)}
        for src, pages in seen.items()
    ]
