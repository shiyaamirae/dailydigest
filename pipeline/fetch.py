"""Fetch candidate items from all AI24 sources, filtered to a 25-hour lookback window.

Writes the combined, beat-grouped result to pipeline/.staging/fetched.json for
rank_summarize.py to consume. Each source fails independently — a broken scraper
or a down feed is logged and skipped, never crashes the whole run.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

LOOKBACK_HOURS = 25
STAGING_PATH = Path(__file__).parent / ".staging" / "fetched.json"
# Browser-style UA rather than a self-identifying bot string — several sources
# (VoiceBot.ai in particular) sit behind Cloudflare bot protection and 403 a
# generic "...Bot/1.0" UA outright.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

RSS_SOURCES = [
    {"beat": "AI", "source": "OpenAI", "url": "https://openai.com/news/rss.xml"},
    {"beat": "AI", "source": "Google DeepMind", "url": "https://deepmind.google/blog/feed/basic/"},
    {"beat": "AI", "source": "Latent Space", "url": "https://www.latent.space/feed"},
    {"beat": "Design", "source": "Nielsen Norman Group", "url": "https://www.nngroup.com/feed/rss/"},
    {"beat": "Design", "source": "Smashing Magazine", "url": "https://www.smashingmagazine.com/feed/"},
    {"beat": "Design", "source": "UX Collective", "url": "https://uxdesign.cc/feed"},
    {"beat": "Design", "source": "UX Planet", "url": "https://uxplanet.org/feed"},
    {"beat": "Voice AI", "source": "Deepgram", "url": "https://deepgram.com/blog.xml"},
]

ARXIV_CATEGORIES = ["cs.AI", "cs.CL"]


def cutoff_time():
    return datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)


def get_entry_date(entry):
    for key in ("published_parsed", "updated_parsed"):
        val = entry.get(key)
        if val:
            return datetime(*val[:6], tzinfo=timezone.utc)
    return None


def clean_summary(html_summary):
    if not html_summary:
        return ""
    text = BeautifulSoup(html_summary, "html.parser").get_text()
    return " ".join(text.split())[:500]


def safe_parse_date(text):
    if not text:
        return None
    try:
        dt = dateparser.parse(text, fuzzy=True)
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, OverflowError):
        return None


def fetch_rss(source):
    items = []
    try:
        resp = requests.get(source["url"], timeout=20, headers=HEADERS)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        if feed.bozo and not feed.entries:
            raise ValueError(str(feed.bozo_exception))
        cutoff = cutoff_time()
        for entry in feed.entries:
            published = get_entry_date(entry)
            if published is None or published < cutoff:
                continue
            items.append({
                "beat": source["beat"],
                "source": source["source"],
                "title": entry.get("title", "").strip(),
                "url": entry.get("link", ""),
                "published": published.isoformat(),
                "summary": clean_summary(entry.get("summary", "")),
            })
    except Exception as e:
        print(f"  ✗ {source['source']}: {e}", file=sys.stderr)
    return items


def fetch_arxiv():
    items = []
    try:
        query = "+OR+".join(f"cat:{c}" for c in ARXIV_CATEGORIES)
        url = (
            "http://export.arxiv.org/api/query?"
            f"search_query={query}&sortBy=submittedDate&sortOrder=descending&max_results=100"
        )
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        cutoff = cutoff_time()
        for entry in feed.entries:
            published = get_entry_date(entry)
            if published is None or published < cutoff:
                continue
            items.append({
                "beat": "AI",
                "source": "arXiv",
                "title": entry.get("title", "").strip().replace("\n", " "),
                "url": entry.get("link", ""),
                "published": published.isoformat(),
                "summary": clean_summary(entry.get("summary", "")),
            })
    except Exception as e:
        print(f"  ✗ arXiv: {e}", file=sys.stderr)
    return items


def _fetch_anthropic_style(page_url, href_prefix, beat, source_name):
    """Anthropic's /news and /research pages share the same FeaturedGrid markup:
    <a href="{href_prefix}..."><h2-4>title</h2-4>...<time>date</time></a>.
    """
    items = []
    try:
        resp = requests.get(page_url, timeout=20, headers=HEADERS)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        cutoff = cutoff_time()
        seen_urls = set()
        for link in soup.select(f'a[href^="{href_prefix}"]'):
            href = link.get("href", "")
            full_url = urljoin("https://www.anthropic.com", href)
            if full_url in seen_urls:
                continue
            heading = link.find(["h2", "h3", "h4"])
            time_tag = link.find("time")
            if not heading or not time_tag:
                continue
            date_text = time_tag.get("datetime") or time_tag.get_text(strip=True)
            published = safe_parse_date(date_text)
            if published is None or published < cutoff:
                continue
            seen_urls.add(full_url)
            items.append({
                "beat": beat,
                "source": source_name,
                "title": heading.get_text(strip=True),
                "url": full_url,
                "published": published.isoformat(),
                "summary": "",
            })
    except Exception as e:
        print(f"  ✗ {source_name}: {e}", file=sys.stderr)
    return items


def fetch_anthropic():
    return _fetch_anthropic_style(
        "https://www.anthropic.com/news", "/news/", "AI", "Anthropic"
    )


def fetch_anthropic_research():
    return _fetch_anthropic_style(
        "https://www.anthropic.com/research", "/research/", "AI", "Anthropic Research"
    )


def fetch_rasa():
    items = []
    try:
        resp = requests.get("https://rasa.com/blog/", timeout=20, headers=HEADERS)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        cutoff = cutoff_time()
        seen_urls = set()
        for card in soup.select("div.blog-card"):
            link = card.find("a", href=True)
            heading = card.find("h3")
            date_div = card.find("div", class_="blog-meta")
            if not link or not heading or not date_div:
                continue
            full_url = urljoin("https://rasa.com", link["href"])
            if full_url in seen_urls:
                continue
            published = safe_parse_date(date_div.get_text(strip=True))
            if published is None or published < cutoff:
                continue
            seen_urls.add(full_url)
            items.append({
                "beat": "Voice AI",
                "source": "Rasa",
                "title": heading.get_text(strip=True),
                "url": full_url,
                "published": published.isoformat(),
                "summary": "",
            })
    except Exception as e:
        print(f"  ✗ Rasa: {e}", file=sys.stderr)
    return items


def fetch_elevenlabs():
    items = []
    try:
        resp = requests.get("https://elevenlabs.io/blog", timeout=20, headers=HEADERS)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        cutoff = cutoff_time()
        seen_urls = set()
        for h2 in soup.select("h2"):
            link = h2.find("a")
            if not link or not link.get("href"):
                continue
            full_url = urljoin("https://elevenlabs.io", link["href"])
            if full_url in seen_urls:
                continue
            # date lives in a <time datetime="..."> inside the following <dl>
            dl = h2.find_next("dl")
            time_tag = dl.find("time") if dl else None
            date_text = time_tag.get("datetime") if time_tag else None
            published = safe_parse_date(date_text) if date_text else None
            if published is None or published < cutoff:
                continue
            seen_urls.add(full_url)
            items.append({
                "beat": "Voice AI",
                "source": "ElevenLabs",
                "title": link.get_text(strip=True),
                "url": full_url,
                "published": published.isoformat(),
                "summary": "",
            })
    except Exception as e:
        print(f"  ✗ ElevenLabs: {e}", file=sys.stderr)
    return items


def fetch_rain_agency():
    items = []
    try:
        resp = requests.get(
            "https://www.rainagency.com/insights-updates/", timeout=20, headers=HEADERS
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        cutoff = cutoff_time()
        seen_urls = set()
        # title links are <a> tags wrapping an h2 (featured) or h3 (regular list)
        for link in soup.find_all("a", href=True):
            heading = link.find(["h2", "h3"])
            if not heading:
                continue
            href = link["href"]
            if "/insights-updates/" not in href:
                continue
            full_url = href if href.startswith("http") else urljoin(
                "https://www.rainagency.com", href
            )
            if full_url in seen_urls:
                continue
            # date is a sibling element (class containing "date") within a nearby
            # ancestor card, not literal text preceding the link
            date_text = None
            ancestor = link
            for _ in range(4):
                ancestor = ancestor.parent
                if ancestor is None:
                    break
                date_el = ancestor.find(
                    lambda tag: tag.has_attr("class")
                    and any("date" in c.lower() for c in tag["class"])
                )
                if date_el:
                    date_text = date_el.get_text(strip=True)
                    break
            published = safe_parse_date(date_text) if date_text else None
            if published is None or published < cutoff:
                continue
            seen_urls.add(full_url)
            items.append({
                "beat": "Voice AI",
                "source": "Rain.agency",
                "title": heading.get_text(strip=True),
                "url": full_url,
                "published": published.isoformat(),
                "summary": "",
            })
    except Exception as e:
        print(f"  ✗ Rain.agency: {e}", file=sys.stderr)
    return items


def main():
    print(f"Fetching items published in the last {LOOKBACK_HOURS}h...\n")
    all_items = []

    for source in RSS_SOURCES:
        items = fetch_rss(source)
        print(f"  {'✓' if items else '·'} {source['source']}: {len(items)} items")
        all_items.extend(items)

    arxiv_items = fetch_arxiv()
    print(f"  {'✓' if arxiv_items else '·'} arXiv: {len(arxiv_items)} items")
    all_items.extend(arxiv_items)

    for fetcher, name in [
        (fetch_anthropic, "Anthropic"),
        (fetch_anthropic_research, "Anthropic Research"),
        (fetch_elevenlabs, "ElevenLabs"),
        (fetch_rain_agency, "Rain.agency"),
        (fetch_rasa, "Rasa"),
    ]:
        items = fetcher()
        print(f"  {'✓' if items else '·'} {name}: {len(items)} items")
        all_items.extend(items)

    by_beat = {}
    for item in all_items:
        by_beat.setdefault(item["beat"], []).append(item)

    STAGING_PATH.parent.mkdir(parents=True, exist_ok=True)
    STAGING_PATH.write_text(json.dumps(by_beat, indent=2))

    print(f"\nTotal: {len(all_items)} items across {len(by_beat)} beat(s)")
    for beat, items in by_beat.items():
        print(f"  {beat}: {len(items)}")
    print(f"\nWritten to {STAGING_PATH}")


if __name__ == "__main__":
    main()
