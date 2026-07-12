import json
import os
import pickle
import re
import urllib.request
from typing import Optional

import faiss

from shared_model import get_embedding_model

BIBLE_JSON_URL = "https://raw.githubusercontent.com/midvash/bible-data/main/versions/en/kjv/kjv.json"
INDEX_DIR = os.path.join("data", "bible_index")
VERSES_PATH = os.path.join(INDEX_DIR, "bible_verses.json")
INDEX_PATH = os.path.join(INDEX_DIR, "bible.index")
META_PATH = os.path.join(INDEX_DIR, "bible_meta.pkl")

_REF_RE = re.compile(r"\b(\d\s+)?([A-Za-z]+(?:\s+[A-Za-z]+)?)\s*(\d+):(\d+)")
_RANGE_RE = re.compile(r"\b(\d\s+)?([A-Za-z]+(?:\s+[A-Za-z]+)?)\s*(\d+):(\d+)-(\d+)\b")

_BOOK_ALIASES = {
    "Psalm": "Psalms",
}

PASSAGE_MAP: dict[str, tuple[str, int, int, int]] = {
    "beatitudes": ("Matthew", 5, 3, 12),
    "lord's prayer": ("Matthew", 6, 9, 13),
    "ten commandments": ("Exodus", 20, 1, 17),
    "23rd psalm": ("Psalms", 23, 1, 6),
}

def _known_books() -> set[str]:
    known = {
        "Genesis","Exodus","Leviticus","Numbers","Deuteronomy","Joshua","Judges","Ruth",
        "1 Samuel","2 Samuel","1 Kings","2 Kings","1 Chronicles","2 Chronicles",
        "Ezra","Nehemiah","Esther","Job","Psalms","Proverbs","Ecclesiastes",
        "Song of Solomon","Isaiah","Jeremiah","Lamentations","Ezekiel","Daniel",
        "Hosea","Joel","Amos","Obadiah","Jonah","Micah","Nahum","Habakkuk",
        "Zephaniah","Haggai","Zechariah","Malachi",
        "Matthew","Mark","Luke","John","Acts",
        "Romans","1 Corinthians","2 Corinthians","Galatians","Ephesians",
        "Philippians","Colossians","1 Thessalonians","2 Thessalonians",
        "1 Timothy","2 Timothy","Titus","Philemon","Hebrews","James",
        "1 Peter","2 Peter","1 John","2 John","3 John","Jude","Revelation",
    }
    return known

class ScriptureStore:
    def __init__(self):
        self.model = get_embedding_model()
        self.index: Optional[faiss.Index] = None
        self.verses: list[dict] = []
        self.verse_map: dict[str, dict] = {}
        self.loaded = False

    # ── build ──────────────────────────────────────────────

    def build_index(self, url: str = BIBLE_JSON_URL) -> None:
        os.makedirs(INDEX_DIR, exist_ok=True)
        print(f"[ScriptureStore] Downloading KJV Bible from {url} ...")
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode("utf-8"))
        books = data.get("books", data)

        verses = []
        for book_entry in books:
            book_name = book_entry.get("englishName") or book_entry["book"]
            chapters = book_entry.get("chapters", [])
            for ch_entry in chapters:
                chapter_num = ch_entry.get("chapter", 0)
                verses_list = ch_entry.get("verses", [])
                for v_entry in verses_list:
                    verse_num = v_entry.get("number", v_entry.get("verse", 0))
                    text = v_entry.get("text", "").strip()
                    reference = f"{book_name} {chapter_num}:{verse_num}"
                    verses.append({
                        "reference": reference,
                        "book": book_name,
                        "chapter": chapter_num,
                        "verse": verse_num,
                        "text": text,
                    })

        print(f"[ScriptureStore] Loaded {len(verses)} verses from KJV Bible")

        texts = [v["text"] for v in verses]
        embeddings = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        embeddings = embeddings.astype("float32")

        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings)

        self.verses = verses
        self.verse_map = {v["reference"]: v for v in verses}

        with open(VERSES_PATH, "w", encoding="utf-8") as f:
            json.dump(verses, f, indent=2)
        faiss.write_index(self.index, INDEX_PATH)
        with open(META_PATH, "wb") as f:
            pickle.dump({"count": len(verses), "dim": dim}, f)

        self.loaded = True
        print(f"[ScriptureStore] Bible index built and saved ({len(verses)} verses)")

    # ── load ───────────────────────────────────────────────

    def load(self) -> bool:
        if not os.path.exists(INDEX_PATH) or not os.path.exists(VERSES_PATH):
            return False
        try:
            self.index = faiss.read_index(INDEX_PATH)
            with open(VERSES_PATH, "r", encoding="utf-8") as f:
                self.verses = json.load(f)
            self.verse_map = {v["reference"]: v for v in self.verses}
            self.loaded = True
            print(f"[ScriptureStore] Loaded Bible index ({len(self.verses)} verses)")
            return True
        except Exception as e:
            print(f"[ScriptureStore] Load failed: {e}")
            return False

    def save(self) -> None:
        os.makedirs(INDEX_DIR, exist_ok=True)
        with open(VERSES_PATH, "w", encoding="utf-8") as f:
            json.dump(self.verses, f, indent=2)
        if self.index is not None:
            faiss.write_index(self.index, INDEX_PATH)
        with open(META_PATH, "wb") as f:
            pickle.dump({"count": len(self.verses)}, f)

    # ── lookups ────────────────────────────────────────────

    def search_exact(self, reference: str) -> Optional[dict]:
        normalized = reference.strip()
        return self.verse_map.get(normalized)

    def search_similar(self, query: str, top_k: int = 5) -> list[dict]:
        if self.index is None or not self.verses:
            return []
        query_vec = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        query_vec = query_vec.astype("float32")
        scores, indices = self.index.search(query_vec, top_k)
        results = []
        for idx, score in zip(indices[0], scores[0]):
            if idx != -1 and idx < len(self.verses):
                verse = dict(self.verses[int(idx)])
                verse["score"] = float(score)
                results.append(verse)
        return results

    def verify_verse(self, reference: str, claimed_text: Optional[str] = None) -> dict:
        ref = reference.strip()
        verse = self.search_exact(ref)
        if verse is None:
            match = _REF_RE.match(ref)
            if match:
                groups = match.groups()
                if groups[0]:
                    book = groups[0].strip() + " " + groups[1]
                else:
                    book = groups[1]
                ch, vs = groups[2], groups[3]
                alt_ref = f"{book} {ch}:{vs}"
                verse = self.search_exact(alt_ref)
        if verse is None:
            return {
                "verified": False,
                "reference": ref,
                "actual_text": None,
                "found": False,
                "message": f"Could not find {ref} in the Bible index.",
            }
        result = {
            "verified": True,
            "reference": verse["reference"],
            "actual_text": verse["text"],
            "found": True,
        }
        if claimed_text:
            similarity = self._text_similarity(claimed_text, verse["text"])
            if similarity < 0.6:
                result["verified"] = False
                result["claimed_text"] = claimed_text
                result["message"] = (
                    f"I could not verify that {ref} contains the stated text. "
                    f"The actual {ref} reads: \"{verse['text']}\""
                )
        return result

    def get_verse_text(self, reference: str) -> Optional[str]:
        verse = self.search_exact(reference)
        return verse["text"] if verse else None

    def search_range(self, book: str, chapter: int, start_verse: int, end_verse: int) -> list[dict]:
        results = []
        for v in self.verses:
            if (v["book"] == book and v["chapter"] == chapter
                    and start_verse <= v["verse"] <= end_verse):
                results.append(v)
        results.sort(key=lambda v: v["verse"])
        print(f"[ScriptureStore] search_range({book}, {chapter}, {start_verse}, {end_verse}) = {len(results)} verses")
        if results:
            print(f"  First: {results[0]['reference']} — {results[0]['text'][:60]}")
            print(f"  Last:  {results[-1]['reference']} — {results[-1]['text'][:60]}")
        return results

    def get_verses_in_range(self, book: str, chapter: int, start_verse: int, end_verse: int) -> list[dict]:
        return self.search_range(book, chapter, start_verse, end_verse)

    def lookup_passage(self, query: str) -> Optional[tuple[str, int, int, int]]:
        q = query.lower().strip()
        for name, ref in PASSAGE_MAP.items():
            if name in q:
                print(f"[ScriptureStore] lookup_passage matched '{name}' → {ref}")
                return ref
        return None

    def extract_references(self, text: str) -> list[str]:
        known = _known_books()
        known_lower = {b.lower() for b in known}

        def _resolve_book(raw_book: str) -> str | None:
            b = raw_book.strip()
            bl = b.lower()
            # Check alias
            for ak, av in _BOOK_ALIASES.items():
                if bl == ak.lower():
                    return av
            # Check known books
            if bl in known_lower:
                return next(bk for bk in known if bk.lower() == bl)
            # Check each word
            for w in b.split():
                wl = w.lower()
                if wl in known_lower:
                    return next(bk for bk in known if bk.lower() == wl)
                for ak, av in _BOOK_ALIASES.items():
                    if wl == ak.lower():
                        return av
            return None

        refs = []
        # First handle ranges
        for match in _RANGE_RE.finditer(text):
            if match:
                prefix, raw_book, ch_s, vs_start_s, vs_end_s = match.groups()
                raw = f"{prefix or ''}{raw_book}"
                book = _resolve_book(raw)
                if not book:
                    continue
                ch, vs_start, vs_end = int(ch_s), int(vs_start_s), int(vs_end_s)
                refs.append(f"{book} {ch}:{vs_start}-{vs_end}")

        # Then handle single references
        for match in _REF_RE.finditer(text):
            # Skip if this position is already covered by a range match
            if any(m.start() <= match.start() and m.end() >= match.end()
                   for m in _RANGE_RE.finditer(text)):
                continue
            prefix, raw_book, ch_s, vs_s = match.groups()
            raw = f"{prefix or ''}{raw_book}"
            book = _resolve_book(raw)
            if not book:
                continue
            ch, vs = int(ch_s), int(vs_s)
            refs.append(f"{book} {ch}:{vs}")

        seen = set()
        unique = []
        for r in refs:
            if r not in seen:
                seen.add(r)
                unique.append(r)
        return unique

    def stats(self) -> dict:
        return {
            "loaded": self.loaded,
            "verses": len(self.verses),
            "books": len(set(v["book"] for v in self.verses)) if self.verses else 0,
        }

    # ── helpers ────────────────────────────────────────────

    @staticmethod
    def _text_similarity(a: str, b: str) -> float:
        a_tokens = set(a.lower().split())
        b_tokens = set(b.lower().split())
        if not a_tokens or not b_tokens:
            return 0.0
        intersection = a_tokens & b_tokens
        return len(intersection) / max(len(a_tokens), len(b_tokens))
