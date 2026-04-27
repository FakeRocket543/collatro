"""collatro.ingest — 斷詞 + NER（三層 fallback：MLX CKIP → ckip-transformers → jieba）"""

import os
import importlib.util
from pathlib import Path

_ckip_pipeline = None
_ckip_backend = None  # "mlx" | "transformers" | "jieba" | "none"

CKIP_MODEL_DIR = os.environ.get("COLLATRO_CKIP_DIR") or None
CKIP_BATCH_PY = os.environ.get("COLLATRO_CKIP_BATCH_PY") or None


def _load_ckip():
    global _ckip_pipeline, _ckip_backend
    if _ckip_backend is not None:
        return

    # Tier 1: MLX CKIP
    if CKIP_MODEL_DIR and CKIP_BATCH_PY:
        try:
            ckip_path = Path(CKIP_BATCH_PY)
            if ckip_path.exists():
                spec = importlib.util.spec_from_file_location("ckip_batch", ckip_path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                _ckip_pipeline = mod.CKIPBatchProcessor(CKIP_MODEL_DIR)
                _ckip_backend = "mlx"
                return
        except Exception:
            pass

    # Tier 2: ckip-transformers
    try:
        from ckip_transformers.nlp import CkipWordSegmenter, CkipPosTagger
        _ckip_pipeline = {
            "ws": CkipWordSegmenter(model="bert-base"),
            "pos": CkipPosTagger(model="bert-base"),
        }
        _ckip_backend = "transformers"
        return
    except (ImportError, Exception):
        pass

    # Tier 3: jieba
    try:
        import jieba
        import jieba.posseg
        _ckip_pipeline = jieba
        _ckip_backend = "jieba"
        return
    except ImportError:
        pass

    _ckip_backend = "none"


def ingest(text: str) -> dict:
    """Segment text and extract keywords + entities."""
    _load_ckip()

    if _ckip_backend == "mlx":
        result = _ckip_pipeline.process(text)
        ws = result.get("ws", [])
        pos = result.get("pos", [])
    elif _ckip_backend == "transformers":
        ws_result = _ckip_pipeline["ws"]([text])
        pos_result = _ckip_pipeline["pos"]([text])
        ws = ws_result[0]
        pos = pos_result[0]
    elif _ckip_backend == "jieba":
        import jieba.posseg
        pairs = list(jieba.posseg.cut(text))
        ws = [w for w, _ in pairs]
        pos = [p for _, p in pairs]
    else:
        ws = list(text)
        pos = ["X"] * len(ws)

    # 重點實體提示器（CEUR-WS 2025 Claim Rewriting 方法）
    from src.highlight import extract_entities, entity_queries
    hl_entities = extract_entities(ws, pos)
    hl_queries = entity_queries(hl_entities)

    # Keywords: nouns + verbs, length >= 2
    keyword_tags = {"n", "v", "Na", "Nb", "Nc", "Ncd", "VA", "VB", "VC", "VD", "nr", "nt", "ns", "vn"}
    keywords = [w for w, p in zip(ws, pos) if p in keyword_tags and len(w) >= 2]
    seen = set()
    keywords = [k for k in keywords if not (k in seen or seen.add(k))]

    # 詞頻統計（過濾單字和標點）
    from collections import Counter
    word_freq = Counter(w for w, p in zip(ws, pos) if len(w) >= 2 and p not in {"COMMACATEGORY", "PERIODCATEGORY", "COLONCATEGORY", "SEMICOLONCATEGORY", "EXCLAMATIONCATEGORY", "QUESTIONCATEGORY", "PARENTHESISCATEGORY", "DASHCATEGORY", "x", "w"})

    return {
        "ws": ws,
        "pos": pos,
        "keywords": keywords[:10],
        "entities": hl_entities,
        "entity_queries": hl_queries,
        "word_freq": dict(word_freq.most_common(20)),
        "backend": _ckip_backend,
    }
