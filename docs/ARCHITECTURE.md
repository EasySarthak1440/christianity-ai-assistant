# Christianity AI Assistant — Architecture

## 1. Scripture Grounding Strategy

**Why FAISS over pure LLM memory:**

LLMs are known to hallucinate Bible verses — they produce plausible-sounding but fabricated citations. By loading the KJV Bible into a dedicated FAISS index (separate from the document store), every verse citation can be retrieved and verified before the LLM sees it.

**Approach:**
- The KJV Bible (31,102 verses, 66 books) is downloaded from a public-domain JSON source
- Each verse is a standalone chunk indexed via `all-MiniLM-L6-v2` embeddings in a `faiss.IndexFlatIP`
- Metadata per verse: `reference`, `book`, `chapter`, `verse`, `text`
- Persisted to `data/bible_index/` (separate from the document index `data/index/`)
- Exact lookups use a Python dict (`verse_map`) keyed by reference string (e.g. "John 3:16")
- Semantic searches use the FAISS index for finding verses by meaning

**Pipeline:**
```
Query → extract Book N:V patterns via regex → ScriptureStore.verify_verse()
  → if found: inject exact text into LLM context
  → if not found: respond "I could not verify this reference"
```

## 2. Hallucination Prevention

**Retrieval-first for all verse citations:**

1. The denomination-aware system prompt explicitly instructs: *"Never generate a Bible verse from memory — every verse citation must come from the FAISS-retrieved text"*
2. Before the LLM call, the moderation layer extracts `Book N:V` patterns and queries the FAISS index
3. Verified verses are injected into the LLM context as structured `[Reference (KJV) — text]` blocks
4. The LLM is constrained to only cite verses present in the context
5. Post-processing appends a grounding note: *"This response is grounded in [source]. Always verify with your pastor or a trusted theological resource."*

**Historical claims** are flagged with `[Historical claim — not scripture]` appended by the system prompt.

## 3. Moderation Pipeline

All checks run **before** the LLM call. Flow:

```
User Input
    │
    ├── Check 1: Verse rewriting attempt?
    │     └── YES → "Scripture is not something I can rewrite"
    │
    ├── Check 2: Hateful/extremist content?
    │     └── YES → "I'm not able to generate content that promotes hatred"
    │
    ├── Check 3: Adversarial injection (ignore previous, system prompt override)?
    │     └── YES → "This request attempts to use scripture out of context"
    │
    ├── Check 4: Blasphemous/heretical content?
    │     └── YES → Decline gracefully
    │
    ├── Check 5: Fake verse validation (Book N:V patterns + claimed text)?
    │     └── MISMATCH → "I could not verify [ref]. The actual text reads: [retrieved]"
    │
    └── ALL CHECKS PASS → proceed to LLM
```

Each check returns `{allowed: bool, reason: str, safe_response: str}`. On block, the safe response is returned directly without calling the LLM, saving tokens and latency.

## 4. Denomination Handling

**Prompt injection strategy** (not separate models — same LLM, different context):

Four system prompt variants in `denomination_prompts.py`:

| Variant | Canon | Distinctive Context |
|---|---|---|
| General | 66 books, notes differences | Neutral |
| Catholic | 73 books + Deuterocanon | Papal authority, Magisterium |
| Orthodox | 79 books (Septuagint-based) | Church Fathers, Holy Tradition |
| Protestant | 66 books | Sola Scriptura, Reformation |

The frontend sends a `denomination` field with every `/christianity/query` request. The backend selects the appropriate system prompt from `get_system_prompt(denomination)` and prepends it to the LLM context. This is a **zero-shot prompt engineering** approach — no fine-tuning or separate models needed.

All variants share the same core rules: citation-only, grounding notes, no personal stance on controversies.

## 5. Image Safety

**Prompt validation before API call:**

The image generator in `image_generator.py` applies safety checks **before** calling DALL-E 3:

1. **Disrespect detection**: Keywords matching disrespectful descriptions of Jesus/Christ/God
2. **Violence mix**: Christian imagery + gore/weapons/war
3. **Sexual mix**: Christian themes + nudity/erotic content
4. **Political mix**: Christian themes + political parties/slogans/ideologies

**Enhancement**: Safe prompts are automatically appended with *"in the style of classical Christian art, reverent, painterly"* to encourage appropriate output.

**Fallback**: If `OPENAI_API_KEY` is not configured, returns `{available: false}` with an explanatory message.

## 6. Edge Case Decisions

| Scenario | Decision | Rationale |
|---|---|---|
| Fake verse "John 4:32 says God rewards the wealthy" | Flagged by moderation layer — actual verse retrieved and shown | Prevents propagation of false scripture |
| "Rewrite Genesis 1:1" | Hard block — scripture is not editable | Preserves textual integrity |
| "The Council of Nicaea removed books" | LLM can answer but must flag `[Historical claim — not scripture]` | Historical facts about Bible ≠ scripture itself |
| "Is the Book of Tobit scripture?" | Denomination-aware: varies by selected tradition | Reflects real theological disagreement |
| "Does the Bible support slavery?" | Present what scripture says historically, contextualize, note denominational positions, no personal stance | Handles difficult topics faithfully without taking sides |
| Generate "Jesus endorsing [party]" | Image safety validator blocks | Prevents misuse of religious imagery |
| User enters "ignore previous instructions and..." | Moderation layer blocks as adversarial injection | Essential prompt injection defense |
