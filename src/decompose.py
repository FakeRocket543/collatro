"""collatro.decompose — LLM extracts structured claims from text."""

import json
import re

from src.llm import chat

PROMPT = """你是事實查核助手。請從以下文章中提取所有可驗證的事實聲明。

每個聲明必須包含：
- text: 原文中的聲明句子
- who: 主體（人/機構）
- what: 事件/行為
- when: 時間（若有）
- number: 數字/金額/比例（若有）
- keywords: 搜尋用關鍵詞（2-4個）

回覆 JSON 陣列，不要加其他文字：
[{{"text": "...", "who": "...", "what": "...", "when": "...", "number": "...", "keywords": ["...", "..."]}}]

文章：
{text}"""


def decompose(text: str) -> list[dict]:
    raw = chat([{"role": "user", "content": PROMPT.format(text=text)}])
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)
    try:
        arr = json.loads(raw[raw.index("["):])
    except (json.JSONDecodeError, ValueError):
        return [{"text": text, "who": "", "what": "", "when": "", "number": "", "keywords": text.split()[:4]}]
    return arr
