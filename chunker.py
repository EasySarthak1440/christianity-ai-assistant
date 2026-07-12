import nltk  # noqa: E402
from nltk.tokenize import sent_tokenize  # noqa: E402

nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)


# used in ingest.py - small to big chunker
def smart_chunk(
    text: str,
    child_size: int = 200,
    parent_size: int = 1500,
    overlap: int = 100,
) -> tuple[list[str], list[str]]:
    sentences = sent_tokenize(text)
    if not sentences:
        return [], []

    # Build parent chunks (1500-char windows with overlap)
    parents: list[str] = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) + 1 <= parent_size:
            current = (current + " " + sent).strip()
        else:
            if current:
                parents.append(current)
            # Overlap: carry last sentence(s) into next parent
            prev_sents = sent_tokenize(current)
            overlap_text = ""
            for s in reversed(prev_sents):
                if len(overlap_text) + len(s) <= overlap:
                    overlap_text = s + " " + overlap_text
                else:
                    break
            current = (overlap_text + " " + sent).strip()
    if current:
        parents.append(current)

    if not parents:
        return [], []

    # Build child chunks (200-char slices from each parent)
    children: list[str] = []
    parent_refs: list[str] = []

    for parent in parents:
        p_sents = sent_tokenize(parent)
        child_buf = ""
        for sent in p_sents:
            if len(child_buf) + len(sent) + 1 <= child_size:
                child_buf = (child_buf + " " + sent).strip()
            else:
                if child_buf:
                    children.append(child_buf)
                    parent_refs.append(parent)
                child_buf = sent
        if child_buf:
            children.append(child_buf)
            parent_refs.append(parent)

    return children, parent_refs
