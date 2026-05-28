import csv
from pathlib import Path


def load_csv(file_path: str) -> list[dict]:
    source = Path(file_path).name
    pages = []
    with open(file_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return pages

        col_names = reader.fieldnames
        for row_idx, row in enumerate(reader):
            pairs = []
            for col in col_names:
                val = row.get(col, "").strip()
                if val:
                    pairs.append(f"{col} = {val}")
            text = f"In {source}: " + "; ".join(pairs)
            if text.strip():
                pages.append({
                    "text": text,
                    "source": source,
                    "page": row_idx + 1,
                })
    return pages
