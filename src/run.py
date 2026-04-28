"""collatro.run — CLI: ingest‖decompose → fuse → enrich → retrieve → diff → package → render"""

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from src.ingest import ingest
from src.decompose import decompose
from src.fuse import fuse
from src.enrich import enrich
from src.retrieve import retrieve
from src.diff import diff
from src.package import package, save
from src.render import render, RECOMMENDED_THEMES


def run(text: str, theme: str = "slate") -> list:
    print(f"📝 輸入（{len(text)} 字）| 主題：{theme}")
    t0 = time.time()

    # ── 步驟 1+2 並行：NER 與 LLM 同時跑 ──
    print("1/7 斷詞+NER ‖ LLM拆解聲明（並行）…")
    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_ingest = pool.submit(ingest, text)
        fut_decompose = pool.submit(decompose, text)
        ingest_result = fut_ingest.result()
        claims = fut_decompose.result()
    print(f"    → NER 後端：{ingest_result['backend']}，關鍵詞：{' '.join(ingest_result['keywords'][:5])}")
    print(f"    → LLM：{len(claims)} 則聲明")

    # ── 步驟 3：Agent 融合定奪 ──
    print("2/7 Agent 融合（NER + LLM → 最終查詢）…")
    fused = fuse(ingest_result, claims)
    fused_entities = fused.get("entities", [])
    fused_claims = fused.get("claims", [])
    print(f"    → 實體 {len(fused_entities)} 個，聲明 {len(fused_claims)} 則")

    # 用 fused 結果更新 claims 的 keywords
    _patch_claims_with_fused(claims, fused_claims)

    print("3/7 查詢實體背景…")
    entities = [e.get("text", "") if isinstance(e, dict) else str(e) for e in fused_entities]
    entities = [e for e in entities if len(e) >= 2][:8]
    enrich_result = None
    if entities:
        enrich_result = enrich(entities)
        found = [e["name"] for e in enrich_result.get("entities", []) if e.get("found")]
        print(f"    → 找到 {len(found)} 個：{', '.join(found[:5])}")
    else:
        print("    → 無實體")

    print("4/7 搜尋證據…")
    claims = retrieve(claims)
    for c in claims:
        print(f"    → [{len(c.get('evidence',[]))} 筆] {c['text'][:40]}")

    print("5/7 比對差異…")
    claims = diff(claims)
    for c in claims:
        v = c.get("diff", {}).get("verdict", "?")
        print(f"    → [{v}] {c['text'][:40]}")

    print("6/7 儲存結果…")
    pkg = package(text, claims, enrich_result)
    pkg["ingest"] = {"keywords": ingest_result["keywords"], "entities": ingest_result["entities"]}
    pkg["fused"] = fused
    md_path = save(pkg)
    print(f"    → {md_path}")

    print("7/7 產生圖片…")
    paths = render(claims, theme=theme)
    for p in paths:
        print(f"    → {p}")

    elapsed = round(time.time() - t0, 1)
    print(f"✓ 完成（{elapsed}s）")
    return claims


def _patch_claims_with_fused(claims: list[dict], fused_claims: list[dict]):
    """Update claims' keywords with fused search_queries when available."""
    for i, fc in enumerate(fused_claims):
        if i < len(claims) and fc.get("search_queries"):
            claims[i]["keywords"] = fc["search_queries"]


def main():
    parser = argparse.ArgumentParser(description="Collatro — 事實比對教學工具")
    parser.add_argument("text", nargs="?", help="待查核文字")
    parser.add_argument("--file", "-f", help="從檔案讀取")
    parser.add_argument("--theme", "-t", default="slate",
                        help=f"色系主題（推薦：{', '.join(RECOMMENDED_THEMES)}，或任何 Tailwind 色名）")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="互動問答模式，引導學生逐步完成查核")
    args = parser.parse_args()

    if args.interactive:
        from src.interactive import interactive_mode
        interactive_mode(theme=args.theme)
        return

    if args.file:
        from pathlib import Path
        text = Path(args.file).read_text(encoding="utf-8").strip()
    elif args.text:
        text = args.text
    else:
        parser.print_help()
        sys.exit(1)

    run(text, theme=args.theme)


if __name__ == "__main__":
    main()
