"""collatro.retrieve — 搜尋證據（Searxng 優先，DuckDuckGo fallback）。"""

import json
import os
import re
from html import unescape
from urllib.parse import quote_plus, unquote
from urllib.request import urlopen, Request
from urllib.error import URLError

SEARXNG_URL = os.environ.get("COLLATRO_SEARXNG_URL", "")  # e.g. http://localhost:8888
DDG_URL = "https://html.duckduckgo.com/html/"
MAX_RESULTS = 5


def _searxng(query: str) -> list[dict]:
    """Query Searxng JSON API."""
    url = f"{SEARXNG_URL}/search?q={quote_plus(query)}&format=json&categories=general&language=zh-TW"
    req = Request(url, headers={"User-Agent": "Collatro/0.1"})
    data = json.loads(urlopen(req, timeout=15).read())
    results = []
    for r in data.get("results", [])[:MAX_RESULTS]:
        results.append({
            "url": r.get("url", ""),
            "title": r.get("title", ""),
            "snippet": r.get("content", "")[:300],
        })
    return results


def _duckduckgo(query: str) -> list[dict]:
    """Fallback: scrape DuckDuckGo HTML."""
    req = Request(f"{DDG_URL}?q={quote_plus(query)}", headers={"User-Agent": "Mozilla/5.0"})
    html = urlopen(req, timeout=15).read().decode("utf-8", errors="replace")
    results = []
    for m in re.finditer(
        r'class="result__a"[^>]*href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>'
        r'.*?class="result__snippet"[^>]*>(?P<snippet>.*?)</(?:td|div|span)',
        html, re.DOTALL,
    ):
        u = unescape(m.group("url"))
        real = re.search(r"uddg=([^&]+)", u)
        if real:
            u = unquote(real.group(1))
        title = re.sub(r"<[^>]+>", "", unescape(m.group("title")))
        snippet = re.sub(r"<[^>]+>", "", unescape(m.group("snippet")))[:300]
        results.append({"url": u, "title": title, "snippet": snippet})
        if len(results) >= MAX_RESULTS:
            break
    return results


def search(query: str) -> list[dict]:
    """Search with Searxng if available, otherwise DuckDuckGo."""
    if SEARXNG_URL:
        try:
            return _searxng(query)
        except (URLError, OSError, json.JSONDecodeError):
            pass
    return _duckduckgo(query)


def retrieve(claims: list[dict]) -> list[dict]:
    """Search evidence for each claim. Returns claims enriched with 'evidence' list."""
    for claim in claims:
        query = " ".join(claim.get("keywords", [])) or claim.get("text", "")
        claim["evidence"] = search(query)
    return claims
