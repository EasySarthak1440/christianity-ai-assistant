import asyncio
import json
import os
from datetime import datetime, timezone

_AUDIT_PATH = "data/audit.log"
_MONGO_MODE = os.environ.get("MONGO_URL", "") != ""


def log_query(
    user: str,
    query: str,
    intent: str,
    sensitivity: str,
    sources_used: list[str],
    pii_found: list[dict],
    answer_preview: str = "",
) -> None:
    os.makedirs(os.path.dirname(_AUDIT_PATH) or ".", exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user": user,
        "query": query,
        "intent": intent,
        "sensitivity": sensitivity,
        "sources_used": sources_used,
        "pii_found": pii_found,
        "answer_preview": answer_preview[:200],
    }
    with open(_AUDIT_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    if _MONGO_MODE:
        try:
            from mongo_db import log_audit_entry
            asyncio.ensure_future(log_audit_entry(entry))
        except Exception:
            pass
