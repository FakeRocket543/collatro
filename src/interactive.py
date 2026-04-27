"""collatro.interactive — 互動問答模式，引導學生逐步完成事實查核。"""

import sys

from src.decompose import decompose
from src.enrich import enrich, extract_entities
from src.retrieve import retrieve
from src.diff import diff
from src.package import package, save
from src.render import render


def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        ans = input(f"\n💬 {prompt}{suffix}\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n👋 掰掰！")
        sys.exit(0)
    return ans or default


def _pause(msg: str = "按 Enter 繼續…"):
    try:
        input(f"\n⏎ {msg}")
    except (EOFError, KeyboardInterrupt):
        print("\n👋 掰掰！")
        sys.exit(0)


def interactive_mode(theme: str = "slate"):
    print("=" * 60)
    print("🔍 Collatro 互動模式 — 事實比對教學")
    print("=" * 60)
    print("\n這個工具會帶你一步步完成事實查核：")
    print("  1️⃣  貼上一段文字（新聞、社群貼文、LINE 轉傳）")
    print("  2️⃣  AI 拆解出裡面的事實聲明")
    print("  3️⃣  你來猜：哪些聲明可能有問題？")
    print("  4️⃣  搜尋證據，看看實際情況")
    print("  5️⃣  比對差異：人名、數字、時間線")
    print("  6️⃣  產出圖卡，記錄你的查核結果")

    # Step 1: Input
    text = _ask("請貼上你想查核的文字（一段新聞、貼文、或轉傳訊息）：")
    if not text:
        print("❌ 沒有輸入文字，結束。")
        return

    print(f"\n📝 收到！共 {len(text)} 字。")

    # Step 2: Decompose
    _pause("接下來 AI 會拆解這段文字裡的事實聲明…")
    print("\n⏳ 拆解中…")
    claims = decompose(text)
    print(f"\n✅ 找到 {len(claims)} 則可驗證的聲明：\n")
    for i, c in enumerate(claims, 1):
        print(f"  {i}. {c['text']}")
        if c.get("who"):
            print(f"     👤 主體：{c['who']}")
        if c.get("number"):
            print(f"     🔢 數字：{c['number']}")
        if c.get("when"):
            print(f"     📅 時間：{c['when']}")

    # Step 3: Student guesses
    print("\n" + "─" * 40)
    print("🤔 在看到證據之前，你覺得哪些聲明可能有問題？")
    print("   （輸入編號，用逗號分隔，例如：1,3）")
    guess = _ask("你的猜測：", "跳過")
    if guess != "跳過":
        print(f"   📌 記住你的猜測：{guess}")

    # Step 4: Enrich + Retrieve
    _pause("現在來搜尋證據…")
    print("\n⏳ 查詢實體背景…")
    entities = extract_entities(claims)
    enrich_result = None
    if entities:
        enrich_result = enrich(entities)
        found = [e["name"] for e in enrich_result.get("entities", []) if e.get("found")]
        if found:
            print(f"   Wikipedia 找到：{', '.join(found)}")

    print("\n⏳ 搜尋每則聲明的證據…")
    claims = retrieve(claims)
    for i, c in enumerate(claims, 1):
        n = len(c.get("evidence", []))
        print(f"   {i}. [{n} 筆證據] {c['text'][:40]}")
        for e in c.get("evidence", [])[:2]:
            print(f"      📎 {e['title'][:50]}")

    # Step 5: Diff
    _pause("接下來比對聲明和證據的差異…")
    print("\n⏳ 比對 NER / 數字 / 時間線…")
    claims = diff(claims)

    print("\n" + "=" * 60)
    print("📊 比對結果：")
    print("=" * 60)
    for i, c in enumerate(claims, 1):
        d = c.get("diff", {})
        verdict = d.get("verdict", "?")
        icon = {"match": "✅", "mismatch": "❌", "insufficient": "❓"}.get(verdict, "❓")
        print(f"\n{icon} 聲明 {i}：{c['text'][:50]}")
        for item in d.get("ner", []):
            print(f"   🏷️  NER 不一致：聲明說「{item['claim_says']}」，證據說「{item['evidence_says']}」")
        for item in d.get("numbers", []):
            print(f"   🔢 數字不一致：聲明說「{item['claim_says']}」，證據說「{item['evidence_says']}」")
        for item in d.get("timeline", []):
            print(f"   📅 時間不一致：聲明說「{item['claim_says']}」，證據說「{item['evidence_says']}」")
        if not d.get("ner") and not d.get("numbers") and not d.get("timeline"):
            if verdict == "match":
                print("   ✓ 與證據吻合")
            else:
                print("   ？ 證據不足以判斷")

    # Step 6: Reflection
    print("\n" + "─" * 40)
    if guess != "跳過":
        print(f"🔙 你之前猜的是：{guess}")
        print("   跟實際結果比，你猜對了嗎？")
    reflection = _ask("你的心得或觀察（選填）：", "跳過")

    # Step 7: Save + Render
    print("\n⏳ 儲存結果 + 產生圖卡…")
    pkg = package(text, claims, enrich_result)
    if reflection != "跳過":
        pkg["student_reflection"] = reflection
    save(pkg)
    paths = render(claims, theme=theme)
    print(f"\n🎉 完成！圖卡已存到：")
    for p in paths:
        print(f"   📸 {p}")

    print("\n" + "=" * 60)
    print("💡 思考題：")
    print("   • 這段文字的問題出在哪？是數字錯、人名錯、還是時間被嫁接？")
    print("   • 如果你要轉傳這則訊息，你會怎麼修改？")
    print("   • 原始來源是誰？他有什麼動機？")
    print("=" * 60)
