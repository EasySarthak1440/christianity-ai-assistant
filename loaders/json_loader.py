import json
from pathlib import Path


def _flatten(obj, parent_key="", sep="."):
    items = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            items.extend(_flatten(v, new_key, sep=sep))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_key = f"{parent_key}{sep}[{i}]" if parent_key else f"[{i}]"
            items.extend(_flatten(v, new_key, sep=sep))
    else:
        items.append((parent_key, obj))
    return items


def load_json(file_path: str) -> list[dict]:
    source = Path(file_path).name
    pages = []
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    entries = data if isinstance(data, list) else [data]
    for idx, entry in enumerate(entries):
        flat = _flatten(entry)
        pairs = []
        for key, val in flat:
            val_str = str(val).strip()
            if val_str:
                pairs.append(f"{key} = {val_str}")
        text = f"In {source}: " + "; ".join(pairs)
        if text.strip():
            pages.append({
                "text": text,
                "source": source,
                "page": idx + 1,
            })
    return pages
