import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scripture_rag import ScriptureStore

_VERSE_RE = re.compile(r"\b(rewrite|modify|change|rephrase|paraphrase|alter|edit|update|reframe)\b.*\b(Bible|scripture|verse|Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|Samuel|Kings|Chronicles|Ezra|Nehemiah|Esther|Job|Psalms|Proverbs|Ecclesiastes|Song|Isaiah|Jeremiah|Lamentations|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|Romans|Corinthians|Galatians|Ephesians|Philippians|Colossians|Thessalonians|Timothy|Titus|Philemon|Hebrews|James|Peter|John|Jude|Revelation|Gospel|Proverb)\b", re.IGNORECASE)

_HATE_PATTERNS = [
    re.compile(r"\b(inferior|subhuman|race.?war|white.?supremac|black.?supremac|ethnic.?cleans[ei])\b", re.IGNORECASE),
    re.compile(r"\b(kill|murder|exterminate|destroy|hurt|harm)\s+(all|every|the)\s+(jew|muslim|christian|gay|black|white)\w*\b", re.IGNORECASE),
    re.compile(r"\b(prove|justify|support|endorse|promote)\s+(that|how|why)\s+(a\s+)?(race|ethnic|group|religion)\s+(is\s+)?(inferior|superior|lesser|greater)\b", re.IGNORECASE),
]

_ADVERSARIAL_PATTERNS = [
    re.compile(r"\b(ignore|disregard|forget)\s+(previous|above|all)\s+(instructions|prompts|context|rules)\b", re.IGNORECASE),
    re.compile(r"\byou\s+are\s+now\b.*\b(not|without|bypass|override)\b", re.IGNORECASE),
    re.compile(r"\bsystem\s+prompt\b", re.IGNORECASE),
    re.compile(r"\bpretend\b.*\b(you are|to be|that)\b", re.IGNORECASE),
    re.compile(r"\b(override|bypass|ignore)\s+(safety|guideline|rule|restriction|moderation)\b", re.IGNORECASE),
]

_VIOLENCE_JUSTIFICATION_PATTERNS = [
    re.compile(r"\b(justify|justifying|justification)\s+(violence|harm|attack|killing|murder|war|force|aggression)\b", re.IGNORECASE),
    re.compile(r"\b(use|using)\b.*?\b(scripture|bible|verse)s?\b.*?\bto\s+(attack|harm|kill|punish|hurt|strike)\b", re.IGNORECASE),
    re.compile(r"\b(bible|scripture|verse)s?\b.*?\b(kill|harm|punish|attack|hate)\w*\b.*?\b(non.?christians?|heathens?|unbelievers?|infidels?|pagans?|gentiles?)\b", re.IGNORECASE),
]

_BLASPHEMY_PATTERNS = [
    re.compile(r"\b(jesus|christ|god|holy spirit|yahweh|lord)\s+(is\s+)?(fake|myth|imaginary|not real|stupid|dumb|evil|hateful|cruel|terrible|worthless)\b", re.IGNORECASE),
    re.compile(r"\b(curse|damn|fuck)\s+(god|jesus|christ)", re.IGNORECASE),
    re.compile(r"\bbible\s+is\s+(fake|made up|fiction|manipulation|control tool)\b", re.IGNORECASE),
    re.compile(r"\bgod\s+(doesn't|does not|isn't|is not|can't|cannot)\s+(exist|love|care|hear|answer)\b", re.IGNORECASE),
]

_REFERENCE_PATTERN = re.compile(r"(\d?\s?[A-Za-z]+\s*\d+:\d+)")

SAFE_RESPONSES = {
    "rewrite": (
        "Scripture is not something I can rewrite or reframe. "
        "The Bible's text is preserved as-is. I'm happy to discuss its "
        "meaning, context, or translation."
    ),
    "hate": (
        "I'm not able to generate content that promotes hatred or extremism. "
        "The Bible calls us to love our neighbors and treat all people with dignity."
    ),
    "injection": (
        "This request attempts to use scripture out of its Biblical context. "
        "I'm here to provide faithful, respectful answers grounded in the text."
    ),
    "blasphemy": (
        "I'm not able to generate content that is disrespectful toward faith "
        "or sacred beliefs. I'm here to offer helpful, respectful information."
    ),
    "violence": (
        "I'm not able to use scripture to justify harm toward any person "
        "or group. The Bible's core message is love — John 13:34."
    ),
}

def _check_rewrite(user_input: str) -> dict | None:
    match = _VERSE_RE.search(user_input)
    if match:
        return {"allowed": False, "reason": "rewrite", "safe_response": SAFE_RESPONSES["rewrite"]}
    return None

def _check_hate(user_input: str) -> dict | None:
    for pattern in _HATE_PATTERNS:
        if pattern.search(user_input):
            return {"allowed": False, "reason": "hate", "safe_response": SAFE_RESPONSES["hate"]}
    return None

def _check_adversarial(user_input: str) -> dict | None:
    for pattern in _ADVERSARIAL_PATTERNS:
        if pattern.search(user_input):
            return {"allowed": False, "reason": "injection", "safe_response": SAFE_RESPONSES["injection"]}
    return None

def _check_blasphemy(user_input: str) -> dict | None:
    for pattern in _BLASPHEMY_PATTERNS:
        if pattern.search(user_input):
            return {"allowed": False, "reason": "blasphemy", "safe_response": SAFE_RESPONSES["blasphemy"]}
    return None

def _check_violence_justification(user_input: str) -> dict | None:
    for pattern in _VIOLENCE_JUSTIFICATION_PATTERNS:
        if pattern.search(user_input):
            return {"allowed": False, "reason": "violence", "safe_response": SAFE_RESPONSES["violence"]}
    return None

def _check_fake_verse(user_input: str, scripture_store: "ScriptureStore") -> dict | None:
    refs = _REFERENCE_PATTERN.findall(user_input)
    for ref in refs:
        result = scripture_store.verify_verse(ref.strip())
        if result.get("found") and result.get("claimed_text"):
            if not result["verified"]:
                return {
                    "allowed": False,
                    "reason": "fake_verse",
                    "safe_response": result["message"],
                }
    if refs and not scripture_store.loaded:
        return {
            "allowed": True,
            "reason": "bible_not_loaded",
            "safe_response": None,
        }
    return None

def moderation_check(user_input: str, scripture_store: "ScriptureStore" = None) -> dict:
    checks = [_check_rewrite, _check_hate, _check_violence_justification, _check_adversarial, _check_blasphemy]
    for check in checks:
        result = check(user_input)
        if result is not None:
            return result
    if scripture_store is not None and scripture_store.loaded:
        result = _check_fake_verse(user_input, scripture_store)
        if result is not None:
            return result
    return {"allowed": True, "reason": "", "safe_response": ""}
