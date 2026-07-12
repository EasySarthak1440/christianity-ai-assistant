from pathlib import Path

from .csv_loader import load_csv
from .json_loader import load_json
from .pdf_loader import load_pdf

_FORMAT_LOADERS = {
    ".pdf": load_pdf,
    ".csv": load_csv,
    ".json": load_json,
}

def detect_format(file_path: str) -> str | None:
    ext = Path(file_path).suffix.lower()
    if ext in _FORMAT_LOADERS:
        return ext
    return None

def load_file(file_path: str) -> list[dict]:
    ext = detect_format(file_path)
    if ext is None:
        raise ValueError(
            f"Unsupported file format: {file_path}. "
            f"Supported formats: {', '.join(_FORMAT_LOADERS)}"
        )
    loader = _FORMAT_LOADERS[ext]
    return loader(file_path)
