"""Rank and summarize candidate items into the final digest — one Gemini call per beat.

Reads pipeline/.staging/fetched.json (from fetch.py) plus the last few days of
/data/digests/*.json for cross-day dedup context. Writes the result to
pipeline/.staging/ranked.json so it can be inspected before publish.py ever
touches the real archive.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

MODEL = "gemini-3.5-flash-lite"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
TAVILY_URL = "https://api.tavily.com/search"
GROQ_MODEL = "qwen/qwen3.6-27b"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

FETCHED_PATH = Path(__file__).parent / ".staging" / "fetched.json"
RANKED_PATH = Path(__file__).parent / ".staging" / "ranked.json"
ARCHIVE_DIR = Path(__file__).parent.parent / "data" / "digests"
IST = timezone(timedelta(hours=5, minutes=30))

BEATS = ["AI", "Design", "Voice AI"]
MAX_ITEMS_PER_BEAT = 3
DEDUP_LOOKBACK_DAYS = 3

# Fallback web search query per beat — only used when the curated sources
# return 0 candidates for that beat on a given day.
WEB_SEARCH_QUERIES = {
    "AI": "AI news last 24 hours",
    "Design": "UX design news last 24 hours",
    "Voice AI": "voice AI conversational AI news last 24 hours",
}

# Hard truncation ceilings — a safety net only. The prompt already asks for
# tighter soft targets; this just guarantees the layout never breaks on an
# outlier the model doesn't follow instructions on.
HEADLINE_MAX = 70
FIELD_MAX = 250

PERSONALIZATION_BLURB = (
    "I'm targeting 'AI builder' roles — doing product management, product design, "
    "and development myself using AI tools, with no handoffs between those functions. "
    "I'm hands-on building a voice agent right now and believe voice is the next major "
    "interface paradigm, so I want to stay aggressively current on anything I can "
    "actually try or apply — new tools, techniques, and patterns — not just read about. "
    "Prioritize practical/actionable developments over pure research unless a paper has "
    "clear, immediate product implications."
)

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "selections": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "index": {"type": "INTEGER"},
                    "what": {"type": "STRING"},
                    "why": {"type": "STRING"},
                    "impact": {"type": "STRING"},
                    "practical": {"type": "BOOLEAN"},
                },
                "required": ["index", "what", "why", "impact", "practical"],
            },
        }
    },
    "required": ["selections"],
}

# Same shape as RESPONSE_SCHEMA, in standard lowercase JSON Schema for Groq/OpenAI-style APIs
GROQ_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "selections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "what": {"type": "string"},
                    "why": {"type": "string"},
                    "impact": {"type": "string"},
                    "practical": {"type": "boolean"},
                },
                "required": ["index", "what", "why", "impact", "practical"],
            },
        }
    },
    "required": ["selections"],
}


def load_fetched():
    if not FETCHED_PATH.exists():
        raise FileNotFoundError(f"{FETCHED_PATH} not found — run fetch.py first")
    return json.loads(FETCHED_PATH.read_text())


def load_recent_titles(beat):
    """Titles already published for this beat in the last few days, for dedup."""
    if not ARCHIVE_DIR.exists():
        return []
    files = sorted(ARCHIVE_DIR.glob("*.json"), reverse=True)[:DEDUP_LOOKBACK_DAYS]
    titles = []
    for f in files:
        try:
            data = json.loads(f.read_text())
            for item in data.get("beats", {}).get(beat, []):
                titles.append(item.get("title", ""))
        except (json.JSONDecodeError, KeyError):
            continue
    return titles


def truncate(text, limit):
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def build_prompt(beat, candidates, recent_titles):
    candidate_lines = [
        f'[{i}] "{c["title"]}" — {c["source"]} — {c.get("summary", "")[:300]}'
        for i, c in enumerate(candidates)
    ]
    candidates_block = "\n".join(candidate_lines)
    recent_block = (
        "\n".join(f"- {t}" for t in recent_titles)
        if recent_titles
        else "(none — this is a fresh archive)"
    )

    return f"""You are curating the "{beat}" section of a daily digest for a reader with this background:

{PERSONALIZATION_BLURB}

CANDIDATE ITEMS (published in the last 25 hours):
{candidates_block}

ALREADY COVERED IN THE LAST {DEDUP_LOOKBACK_DAYS} DAYS (deprioritize a candidate above if it's substantially the same story):
{recent_block}

TASK:
Select the top {MAX_ITEMS_PER_BEAT} candidates. Fewer is fine and expected if fewer are genuinely worth including — never force-fill with filler. Rank by, combined:
- Source authority (major labs / top publications)
- Relevance to the reader's background above
- Novelty (skip stories substantially the same as something already covered recently)
- Tie-break: a practical/try-able item (a tool, API, or launch the reader can actually use) beats a prestigious-but-theoretical item when scores are otherwise close

For each selected item, write:
- "what": what happened, one sentence, under 150 characters
- "why": why it matters, one sentence, under 150 characters
- "impact": how it impacts the reader's work specifically, one short phrase, under 100 characters
- "practical": true if this is something the reader could actually try/use, false if it's primarily informational/research

Return "index" as the candidate's number from the list above. Do not invent items that aren't in the candidate list."""


def web_search_fallback(beat):
    """Only called when the curated sources returned 0 candidates for this beat.
    One bounded Tavily search — not a loop, not agentic decision-making — just
    a wider net cast for a single day's gap in the curated source list.
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        print(f"  · {beat}: 0 candidates and TAVILY_API_KEY not set, skipping fallback")
        return []
    try:
        resp = requests.post(
            TAVILY_URL,
            json={
                "api_key": api_key,
                "query": WEB_SEARCH_QUERIES[beat],
                "topic": "news",
                "search_depth": "advanced",
                "time_range": "day",
                "max_results": 8,
            },
            timeout=30,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
    except Exception as e:
        print(f"  ✗ {beat}: Tavily fallback search failed: {e}", file=sys.stderr)
        return []

    candidates = []
    for r in results:
        url = r.get("url", "")
        domain = urlparse(url).netloc.removeprefix("www.")
        candidates.append({
            "title": r.get("title", "").strip(),
            "source": domain or "Web search",
            "url": url,
            "summary": r.get("content", ""),
        })
    print(f"  · {beat}: 0 curated candidates, found {len(candidates)} via web search fallback")
    return candidates


def call_gemini(prompt):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": RESPONSE_SCHEMA,
        },
    }
    resp = requests.post(f"{API_URL}?key={api_key}", json=payload, timeout=60)
    resp.raise_for_status()
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


def call_groq(prompt):
    """Fallback LLM if the Gemini call itself fails (outage, rate limit, etc.) —
    same prompt, same schema shape, different provider. Not used otherwise.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set")
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt + "\n\nRespond with ONLY the JSON object, no other text."}],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "selections_response", "schema": GROQ_RESPONSE_SCHEMA},
        },
        # Qwen3.6 is a reasoning model — it spends tokens thinking before the
        # final JSON, so a low default budget truncates before valid JSON
        # ever gets produced. Confirmed by testing: 400 json_validate_failed
        # with an empty failed_generation at the default limit.
        "max_completion_tokens": 4000,
    }
    resp = requests.post(
        GROQ_URL, headers={"Authorization": f"Bearer {api_key}"}, json=payload, timeout=60
    )
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"]
    return json.loads(text)


def rank_beat(beat, candidates):
    if not candidates:
        candidates = web_search_fallback(beat)
        if not candidates:
            return []

    recent_titles = load_recent_titles(beat)
    prompt = build_prompt(beat, candidates, recent_titles)

    try:
        result = call_gemini(prompt)
    except Exception as e:
        print(f"  ✗ {beat}: Gemini call failed ({e}), trying Groq/Qwen fallback", file=sys.stderr)
        try:
            result = call_groq(prompt)
            print(f"  ✓ {beat}: Groq fallback succeeded")
        except Exception as e2:
            print(f"  ✗ {beat}: Groq fallback also failed: {e2}", file=sys.stderr)
            return []

    items = []
    for sel in result.get("selections", [])[:MAX_ITEMS_PER_BEAT]:
        idx = sel.get("index")
        if not isinstance(idx, int) or not (0 <= idx < len(candidates)):
            continue
        candidate = candidates[idx]
        items.append({
            "title": truncate(candidate["title"], HEADLINE_MAX),
            "source": candidate["source"],
            "url": candidate["url"],
            "what": truncate(sel.get("what", ""), FIELD_MAX),
            "why": truncate(sel.get("why", ""), FIELD_MAX),
            "impact": truncate(sel.get("impact", ""), FIELD_MAX),
            "practical": bool(sel.get("practical", False)),
        })
    print(f"  ✓ {beat}: {len(items)} selected from {len(candidates)} candidates")
    return items


def main():
    fetched = load_fetched()
    print("Ranking and summarizing...\n")

    digest = {"date": datetime.now(IST).date().isoformat(), "beats": {}}
    for beat in BEATS:
        candidates = fetched.get(beat, [])
        digest["beats"][beat] = rank_beat(beat, candidates)

    RANKED_PATH.parent.mkdir(parents=True, exist_ok=True)
    RANKED_PATH.write_text(json.dumps(digest, indent=2))
    print(f"\nWritten to {RANKED_PATH}")


if __name__ == "__main__":
    main()
