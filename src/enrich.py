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


# Wikidata 常用屬性
_WD_PROPS = {
    "P569": "出生日期",
    "P570": "死亡日期",
    "P509": "死因",
    "P27": "國籍",
    "P106": "職業",
    "P39": "職位",
    "P108": "任職機構",
    "P159": "總部位置",
    "P17": "所屬國家",
    "P571": "成立日期",
    "P576": "解散日期",
    "P1128": "員工數",
    "P2139": "營收",
}


def _wikidata_facts(qid: str) -> dict:
    """Query Wikidata for structured facts about an entity."""
    key = ("wikidata", qid)
    if key in _cache:
        return _cache[key]
    try:
        url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
        req = Request(url, headers={"User-Agent": "Collatro/0.1"})
        data = json.loads(urlopen(req, timeout=10).read())
        entity = data.get("entities", {}).get(qid, {})
        claims = entity.get("claims", {})

        facts = {}
        for prop_id, label in _WD_PROPS.items():
            if prop_id not in claims:
                continue
            values = []
            for claim in claims[prop_id][:3]:  # max 3 values per prop
                mainsnak = claim.get("mainsnak", {})
                dv = mainsnak.get("datavalue", {})
                if dv.get("type") == "time":
                    values.append(dv["value"]["time"].lstrip("+").split("T")[0])
                elif dv.get("type") == "wikibase-entityid":
                    # Resolve entity label
                    ref_id = dv["value"]["id"]
                    ref_label = _resolve_wd_label(ref_id)
                    if ref_label:
                        values.append(ref_label)
                elif dv.get("type") == "quantity":
                    values.append(dv["value"]["amount"].lstrip("+"))
                elif dv.get("type") == "string":
                    values.append(dv["value"])
            if values:
                facts[label] = values if len(values) > 1 else values[0]

        _cache[key] = facts
        return facts
    except Exception:
        _cache[key] = {}
        return {}


def _resolve_wd_label(qid: str) -> str:
    """Get Chinese label for a Wikidata entity."""
    key = ("wd_label", qid)
    if key in _cache:
        return _cache[key]
    try:
        url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={qid}&props=labels&languages=zh-tw|zh&format=json"
        req = Request(url, headers={"User-Agent": "Collatro/0.1"})
        data = json.loads(urlopen(req, timeout=5).read())
        labels = data.get("entities", {}).get(qid, {}).get("labels", {})
        label = labels.get("zh-tw", labels.get("zh", {})).get("value", "")
        _cache[key] = label
        return label
    except Exception:
        _cache[key] = ""
        return ""


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
    wikidata = {}
    if wiki.get("wikidata_id"):
        wikidata = _wikidata_facts(wiki["wikidata_id"])
    return {
        "name": name,
        "found": True,
        "description": wiki["description"],
        "extract": wiki["extract"],
        "wiki_url": wiki["wiki_url"],
        "wikidata_id": wiki["wikidata_id"],
        "wikidata": wikidata,
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
