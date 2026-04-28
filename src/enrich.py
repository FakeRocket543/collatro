"""collatro.enrich — Wikipedia/Wikidata entity lookup for claim context (async parallel)."""

import asyncio
from collections import Counter
from urllib.parse import quote

import aiohttp


# ── Cache ──
_cache: dict = {}


# ── Config ──
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


# ── Async API Client ──
class WikiAPIClient:
    """Async Wikipedia/Wikidata API client with connection pooling."""

    BASE_WIKI = "https://zh.wikipedia.org/api/rest_v1"
    BASE_WIKIDATA = "https://www.wikidata.org"
    HEADERS = {"User-Agent": "Collatro/0.1"}
    TIMEOUT = 10

    def __init__(self, session: aiohttp.ClientSession | None = None):
        self._session = session
        self._owned = False

    async def __aenter__(self):
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.TIMEOUT)
            self._session = aiohttp.ClientSession(timeout=timeout, headers=self.HEADERS)
            self._owned = True
        return self

    async def __aexit__(self, *_):
        if self._owned and self._session:
            await self._session.close()

    async def get_json(self, url: str) -> dict | None:
        """Fetch JSON from URL with error handling."""
        if not self._session:
            raise RuntimeError("WikiAPIClient used outside context manager")
        try:
            async with self._session.get(url) as resp:
                resp.raise_for_status()
                return await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return None


# ── Async Fetch Functions ──

async def _wiki_summary_async(api: WikiAPIClient, name: str) -> dict | None:
    """Fetch Wikipedia summary."""
    key = ("summary", name)
    if key in _cache:
        return _cache[key]

    url = f"{api.BASE_WIKI}/page/summary/{quote(name)}"
    data = await api.get_json(url)
    if not data:
        _cache[key] = None
        return None

    result = {
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "extract": data.get("extract", "")[:200],
        "wikidata_id": data.get("wikibase_item", ""),
        "wiki_url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
    }
    _cache[key] = result
    return result


async def _wikidata_facts_async(api: WikiAPIClient, qid: str) -> dict:
    """Query Wikidata for structured facts."""
    key = ("wikidata", qid)
    if key in _cache:
        return _cache[key]

    url = f"{api.BASE_WIKIDATA}/wiki/Special:EntityData/{qid}.json"
    data = await api.get_json(url)
    if not data:
        _cache[key] = {}
        return {}

    entity = data.get("entities", {}).get(qid, {})
    claims = entity.get("claims", {})

    facts = {}
    for prop_id, label in _WD_PROPS.items():
        if prop_id not in claims:
            continue
        values = []
        for claim in claims[prop_id][:3]:
            mainsnak = claim.get("mainsnak", {})
            dv = mainsnak.get("datavalue", {})
            if dv.get("type") == "time":
                values.append(dv["value"]["time"].lstrip("+").split("T")[0])
            elif dv.get("type") == "wikibase-entityid":
                ref_id = dv["value"]["id"]
                ref_label = await _resolve_wd_label_async(api, ref_id)
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


async def _resolve_wd_label_async(api: WikiAPIClient, qid: str) -> str:
    """Get Chinese label for Wikidata entity."""
    key = ("wd_label", qid)
    if key in _cache:
        return _cache[key]

    url = f"{api.BASE_WIKIDATA}/w/api.php?action=wbgetentities&ids={qid}&props=labels&languages=zh-tw|zh&format=json"
    data = await api.get_json(url)
    if not data:
        _cache[key] = ""
        return ""

    labels = data.get("entities", {}).get(qid, {}).get("labels", {})
    label = labels.get("zh-tw", labels.get("zh", {})).get("value", "")
    _cache[key] = label
    return label


async def _wiki_categories_async(api: WikiAPIClient, name: str) -> list[str]:
    """Fetch Wikipedia categories."""
    key = ("cats", name)
    if key in _cache:
        return _cache[key]

    url = (
        f"{api.BASE_WIKI}/w/api.php?"
        f"action=query&titles={quote(name)}&prop=categories"
        f"&cllimit=20&clshow=!hidden&format=json"
    )
    data = await api.get_json(url)
    if not data:
        _cache[key] = []
        return []

    pages = data.get("query", {}).get("pages", {})
    cats = []
    for page in pages.values():
        for c in page.get("categories", []):
            title = c["title"].replace("Category:", "").replace("分類:", "")
            cats.append(title)
    _cache[key] = cats
    return cats


async def enrich_entity_async(api: WikiAPIClient, name: str) -> dict:
    """Fetch all data for a single entity in parallel."""
    if len(name) < 2:
        return {"name": name, "found": False}

    # 並行抓取 wiki summary + wikidata facts + categories
    wiki, wikidata_id, cats = await asyncio.gather(
        _wiki_summary_async(api, name),
        _get_wikidata_id_from_summary(api, name),
        _wiki_categories_async(api, name),
        return_exceptions=True
    )

    # 處理異常結果
    if isinstance(wiki, BaseException):
        wiki = None
    if isinstance(cats, BaseException):
        cats = []
    if isinstance(wikidata_id, BaseException):
        wikidata_id = None

    if not wiki:
        return {"name": name, "found": False}

    wikidata = {}
    if wikidata_id:
        wikidata = await _wikidata_facts_async(api, wikidata_id)

    return {
        "name": name,
        "found": True,
        "description": wiki.get("description", "") if wiki else "",
        "extract": wiki.get("extract", "") if wiki else "",
        "wiki_url": wiki.get("wiki_url", "") if wiki else "",
        "wikidata_id": wikidata_id or "",
        "wikidata": wikidata,
        "categories": cats if cats else [],
    }


async def _get_wikidata_id_from_summary(api: WikiAPIClient, name: str) -> str | None:
    """Helper to get Wikidata ID from summary."""
    wiki = await _wiki_summary_async(api, name)
    if wiki:
        return wiki.get("wikidata_id", "")
    return None


# ── Public Sync API (保持相容性) ──

def enrich(entities: list[str]) -> dict:
    """Enrich entity list with Wikipedia. Returns {entities: [...], all_categories: {...}}"""
    if not entities:
        return {"entities": [], "all_categories": {}}

    # 運行 async 版本
    results, all_cats = asyncio.run(_enrich_async(entities))

    return {
        "entities": results,
        "all_categories": dict(Counter(all_cats).most_common(15)),
    }


async def _enrich_async(entities: list[str]) -> tuple[list[dict], list[str]]:
    """Async implementation of enrich."""
    filtered = [name for name in entities if len(name) >= 2]

    async with WikiAPIClient() as api:
        # 並行處理所有實體，限制同時請求數
        semaphore = asyncio.Semaphore(8)

        async def bounded_enrich(name: str):
            async with semaphore:
                return await enrich_entity_async(api, name)

        tasks = [bounded_enrich(name) for name in filtered]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # 處理結果
    valid_results = []
    all_cats = []
    for r in results:
        if isinstance(r, BaseException):
            continue
        if r.get("found"):
            all_cats.extend(r.get("categories", []))
        valid_results.append(r)

    return valid_results, all_cats


# ── Legacy Functions (保持相容性) ──

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


def enrich_entity(name: str) -> dict:
    """Sync wrapper for enrich_entity_async."""
    if len(name) < 2:
        return {"name": name, "found": False}
    return asyncio.run(_enrich_entity_single_async(name))


async def _enrich_entity_single_async(name: str) -> dict:
    """Async implementation for single entity."""
    async with WikiAPIClient() as api:
        return await enrich_entity_async(api, name)
