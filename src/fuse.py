"""collatro.fuse — Agent 融合：合併 NER 實體 + LLM 聲明，去重產出最終查詢詞。

流程：
  NER (ingest) 產出 entities + keywords
  LLM (decompose) 產出 claims（含 who/what/keywords）
  → fuse() 用 LLM agent 合併兩路結果，去重、補漏、定奪最終查詢清單
"""

import json
import re

from src.llm import chat

FUSE_PROMPT = """你是事實查核融合助手。你收到兩路提取結果：

【NER 實體】（自動斷詞提取，可能有噪音）
{ner_entities}

【LLM 聲明】（語言模型提取的可驗證聲明）
{llm_claims}

請執行：
1. 合併兩路的人名、機構、時間、數字、事件，去除重複和噪音（如單字、虛詞）
2. 為每則聲明補充最佳搜尋關鍵詞（中英文皆可），優先使用專有名詞的英文原名
3. 輸出 JSON：
{{
  "entities": [{{"text": "...", "type": "person|org|time|number|event|place", "en": "英文名(若有)"}}],
  "claims": [{{"text": "原文聲明", "search_queries": ["查詢1", "查詢2"]}}]
}}

只回覆 JSON，不加其他文字。"""


def fuse(ingest_result: dict, claims: list[dict]) -> dict:
    """Merge NER entities + LLM claims via agent, return unified entities + search queries."""
    # 準備 NER 實體摘要
    ner_entities = []
    for e in ingest_result.get("entities", []):
        if isinstance(e, dict):
            ner_entities.append(f"[{e.get('type','')}] {e.get('text','')}")
        else:
            ner_entities.append(str(e))
    ner_str = "\n".join(ner_entities[:20]) or "（無）"

    # 準備 LLM 聲明摘要
    claim_lines = []
    for c in claims:
        parts = [c.get("text", "")]
        if c.get("who"):
            parts.append(f"主體:{c['who']}")
        if c.get("number"):
            parts.append(f"數字:{c['number']}")
        if c.get("keywords"):
            parts.append(f"詞:{','.join(c['keywords'])}")
        claim_lines.append(" | ".join(parts))
    claims_str = "\n".join(claim_lines[:15]) or "（無）"

    prompt = FUSE_PROMPT.format(ner_entities=ner_str, llm_claims=claims_str)
    raw = chat([{"role": "user", "content": prompt}], max_tokens=1500)

    # Parse JSON
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)
    try:
        result = json.loads(raw[raw.index("{"):])
    except (json.JSONDecodeError, ValueError):
        # Fallback: 直接用 LLM claims 的 keywords 作為查詢
        return _fallback(ingest_result, claims)

    # 確保結構完整
    if "entities" not in result:
        result["entities"] = []
    if "claims" not in result:
        result["claims"] = []
    return result


def _fallback(ingest_result: dict, claims: list[dict]) -> dict:
    """Fallback when agent fusion fails — merge mechanically."""
    entities = []
    seen = set()
    for e in ingest_result.get("entities", []):
        text = e.get("text", "") if isinstance(e, dict) else str(e)
        if len(text) >= 2 and text not in seen:
            seen.add(text)
            entities.append({"text": text, "type": e.get("type", "unknown") if isinstance(e, dict) else "unknown"})

    fused_claims = []
    for c in claims:
        queries = c.get("keywords", [])
        if c.get("who") and len(c["who"]) >= 2:
            queries = [c["who"]] + queries
        fused_claims.append({"text": c.get("text", ""), "search_queries": queries[:4]})

    return {"entities": entities[:15], "claims": fused_claims}
