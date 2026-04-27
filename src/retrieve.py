"""collatro.retrieve — DuckDuckGo search for each claim."""

import re
from html import unescape
from urllib.parse import quote_plus, unquote
from urllib.request import urlopen, Request

DDG_URL = "https://html.duckduckgo.com/html/"
MAX_RESULTS = 3


def _duckduckgo(query: str) -> list[dict]:
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


def retrieve(claims: list[dict]) -> list[dict]:
    """Search evidence for each claim. Returns claims enriched with 'evidence' list."""
    for claim in claims:
        query = " ".join(claim.get("keywords", [])) or claim.get("text", "")
        claim["evidence"] = _duckduckgo(query)
    return claims
