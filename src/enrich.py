"""collatro.enrich — Wikipedia/Wikidata entity lookup for claim context."""

import json
import time
from urllib.request import urlopen, Request
from urllib.parse import quote
from collections import Counter

_cache = {}


def _wiki_summary(name: str) -> dict | None:
    key = ("summary", name)
    if key in _cache:
        return _cache[key]
    try:
        url = f"https://zh.wikipedia.org/api/rest_v1/page/summary/{quote(name)}"
        req = Request(url, headers={"User-Agent": "Collatro/0.1"})
        data = json.loads(urlopen(req, timeout=10).read())
        result = {
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "extract": data.get("extract", "")[:200],
            "wikidata_id": data.get("wikibase_item", ""),
            "wiki_url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
        }
        _cache[key] = result
        return result
    except Exception:
        _cache[key] = None
        return None


def _wiki_categories(name: str) -> list[str]:
    key = ("cats", name)
    if key in _cache:
        return _cache[key]
    try:
        url = (
            f"https://zh.wikipedia.org/w/api.php?"
            f"action=query&titles={quote(name)}&prop=categories"
            f"&cllimit=20&clshow=!hidden&format=json"
        )
        req = Request(url, headers={"User-Agent": "Collatro/0.1"})
        data = json.loads(urlopen(req, timeout=10).read())
        pages = data.get("query", {}).get("pages", {})
        cats = []
        for page in pages.values():
            for c in page.get("categories", []):
                title = c["title"].replace("Category:", "").replace("分類:", "")
                cats.append(title)
        _cache[key] = cats
        return cats
    except Exception:
        _cache[key] = []
        return []


def enrich_entity(name: str) -> dict:
    wiki = _wiki_summary(name)
    if not wiki:
        return {"name": name, "found": False}
    cats = _wiki_categories(name)
    return {
        "name": name,
        "found": True,
        "description": wiki["description"],
        "extract": wiki["extract"],
        "wiki_url": wiki["wiki_url"],
        "categories": cats,
    }


def enrich(entities: list[str]) -> dict:
    """Enrich entity list with Wikipedia. Returns {entities: [...], all_categories: {...}}"""
    results = []
    all_cats = []
    for name in entities:
        if len(name) < 2:
            continue
        r = enrich_entity(name)
        results.append(r)
        if r.get("found"):
            all_cats.extend(r.get("categories", []))
        time.sleep(0.15)
    return {
        "entities": results,
        "all_categories": dict(Counter(all_cats).most_common(15)),
    }


def extract_entities(claims: list[dict]) -> list[str]:
    """Extract entity names from claims' who fields."""
    seen = set()
    entities = []
    for c in claims:
        for field in ("who",):
            val = c.get(field, "")
            if val and val not in seen and len(val) >= 2:
                seen.add(val)
                entities.append(val)
    return entities[:8]
