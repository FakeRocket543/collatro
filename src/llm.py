"""collatro.llm — shared LLM chat interface."""

import json
from urllib.request import urlopen, Request

from src.config import LLM_URL, LLM_MODEL


def chat(messages: list, max_tokens: int = 1024) -> str:
    body = json.dumps({
        "model": LLM_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }).encode()
    req = Request(LLM_URL, data=body, headers={"Content-Type": "application/json"})
    resp = urlopen(req, timeout=120)
    return json.loads(resp.read())["choices"][0]["message"]["content"].strip()
