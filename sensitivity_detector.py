import re

_PII_PATTERNS = [
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("credit_card", re.compile(r"\b(?:\d[ -]*?){13,16}\b")),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("phone", re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")),
    ("ip_address", re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")),
]

def contains_pii(text: str) -> list[dict]:
    found = []
    for label, pattern in _PII_PATTERNS:
        for match in pattern.finditer(text):
            found.append({
                "type": label,
                "value": match.group(),
                "start": match.start(),
                "end": match.end(),
            })
    return found

def redact_pii(text: str, replacement: str = "[REDACTED]") -> str:
    for label, pattern in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text

_HIGH_RISK_KEYWORDS = [
    "password", "secret", "credential", "api_key", "token",
    "ssn", "social security", "confidential",
]

def is_high_risk_query(query: str) -> bool:
    lower = query.lower()
    for kw in _HIGH_RISK_KEYWORDS:
        if kw in lower:
            return True
    return False
