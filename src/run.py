"""collatro.run — CLI: decompose → enrich → retrieve → diff → package → render"""

import argparse
import sys
import time

from src.decompose import decompose
from src.enrich import enrich, extract_entities
from src.retrieve import retrieve
from src.diff import diff
from src.package import package, save
from src.render import render, RECOMMENDED_THEMES


def run(text: str, theme: str = "slate") -> list:
    print(f"📝 輸入（{len(text)} 字）| 主題：{theme}")
    t0 = time.time()

    print("1/6 拆解聲明…")
    claims = decompose(text)
    print(f"    → {len(claims)} 則聲明")

    print("2/6 查詢實體背景…")
    entities = extract_entities(claims)
    enrich_result = None
    if entities:
        enrich_result = enrich(entities)
        found = [e["name"] for e in enrich_result.get("entities", []) if e.get("found")]
        print(f"    → 找到 {len(found)} 個：{', '.join(found[:5])}")
    else:
        print("    → 無實體")

    print("3/6 搜尋證據…")
    claims = retrieve(claims)
    for c in claims:
        print(f"    → [{len(c.get('evidence',[]))} 筆] {c['text'][:40]}")

    print("4/6 比對差異…")
    claims = diff(claims)
    for c in claims:
        v = c.get("diff", {}).get("verdict", "?")
        print(f"    → [{v}] {c['text'][:40]}")

    print("5/6 儲存結果…")
    pkg = package(text, claims, enrich_result)
    md_path = save(pkg)
    print(f"    → {md_path}")

    print("6/6 產生圖片…")
    paths = render(claims, theme=theme)
    for p in paths:
        print(f"    → {p}")

    elapsed = round(time.time() - t0, 1)
    print(f"✓ 完成（{elapsed}s）")
    return claims


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
