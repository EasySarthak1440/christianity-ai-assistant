from pathlib import Path

import pypdf


def load_pdf(file_path: str) -> list[dict]:
    pages = []
    source = Path(file_path).name

    with open(file_path, "rb") as f:
        reader = pypdf.PdfReader(f)
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():                          # skip blank pages
                pages.append({
                    "text": text,
                    "source": source,
                    "page": i + 1,
                })

    return pages

def load_pdfs(file_paths: list[str]) -> list[dict]:
    all_pages = []
    for path in file_paths:
        all_pages.extend(load_pdf(path))
    return all_pages
