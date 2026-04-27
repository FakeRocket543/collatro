# 查核

## 觸發條件

使用者貼了一段要查核的文字。

## 流程（強制依序執行）

### Step 1: 斷詞 + 實體提取 + 詞頻

```bash
python3 -c "
import json, sys
sys.path.insert(0, '.')
from src.ingest import ingest

text = '''{{TEXT}}'''

r = ingest(text)
print(json.dumps({
    'entities': r.get('entities', []),
    'entity_queries': r.get('entity_queries', []),
    'keywords': r.get('keywords', []),
    'word_freq': r.get('word_freq', {}),
}, ensure_ascii=False, indent=2))
"
```

### Step 2: 你自己拆解聲明

根據原文和 Step 1 的實體，列出所有可驗證的事實聲明。每則聲明標出：
- 原文段落（引用）
- 涉及的實體（人/機構/地/數字/時間）

### Step 3: 搜尋證據

對每則聲明的關鍵實體，執行搜尋：

```bash
python3 -c "
import json, sys
sys.path.insert(0, '.')
from src.retrieve import search
from src.enrich import enrich_entity

queries = {{QUERIES}}  # 從 Step 2 決定的查詢詞列表

# Wikidata KG 查詢（人名/機構 — 取得結構化事實）
print('=== Wikidata KG ===')
for name in {{PERSON_ORG_LIST}}:  # Step 1 中 type=person 或 org 的實體
    r = enrich_entity(name)
    if r.get('found'):
        print(json.dumps(r, ensure_ascii=False))

# 搜尋引擎
print()
print('=== 搜尋結果 ===')
for q in queries:
    results = search(q)
    for ev in results[:3]:
        print(json.dumps({'query': q, 'title': ev['title'], 'url': ev['url'], 'snippet': ev['snippet'][:200]}, ensure_ascii=False))
"
```

Wikidata 回傳的結構化事實（出生/死亡日期、死因、職業、國籍等）是硬資料，優先採信。搜尋結果作為補充。

### Step 4: 你自己比對差異

根據搜尋結果，比對每則聲明與證據的差異。重點看：
- NER：人名/機構/地點是否正確
- 數字：金額/人數/比例是否吻合
- 時間線：日期/順序是否正確

### Step 5: 報告

每則聲明的報告格式：

> **聲明：**「原文段落引用」
>
> **比對：** 聲明說 X，證據說 Y
>
> **來源：**
> - [標題](URL)
> - [Wikipedia 頁面](URL)
>
> **判定：** ✓ 吻合 / ✗ 不一致 / ？ 資訊不足

### Step 5.5: 生成圖卡

你自己用 Tailwind CSS 寫一份 HTML 圖卡，然後用 Playwright 截圖。

設計要求：
- **橫式版**（桌面/分享）：寬 1080px，高度自適應，最小 600px
- **直式版**（手機/IG story）：寬 1080px，高度自適應（不要固定 1920，用內容撐高），字體加大 1.3 倍
- 深色背景（用使用者指定的 theme 色系，預設 sky）
- 字體大小規範：
  - 橫式：聲明 text-xl、比對內容 text-base、來源 text-sm
  - 直式：聲明 text-2xl、比對內容 text-lg、來源 text-base
  - KG tags：text-sm（橫式）/ text-base（直式）
- 頂部：Collatro logo + 「事實比對卡」
- 原始聲明區塊（深色卡片）
- KG tags（Wikidata 結構化資料做成彩色 pill badges：出生/死亡/職業/國籍等）
- 判定結果（大字，紅/綠/黃）
- 比對差異（NER/數字/時間 分類標籤 + 聲明 vs 證據）
- 參考來源（標題 + 短 URL，最多 4 筆）
- 底部可放短網址（如果有的話）

兩版都要截圖：

```bash
python3 -c "
from playwright.sync_api import sync_playwright
from pathlib import Path

html_wide = '''{{橫式 HTML}}'''
html_tall = '''{{直式 HTML}}'''

Path('output').mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch()

    # 橫式
    page = browser.new_page(viewport={'width': 1080, 'height': 800})
    page.set_content(html_wide, wait_until='networkidle')
    h = page.evaluate('document.body.scrollHeight')
    page.set_viewport_size({'width': 1080, 'height': h})
    page.screenshot(path='output/card_wide.png', clip={'x': 0, 'y': 0, 'width': 1080, 'height': h})

    # 直式（寬度較窄，字體較大，高度自適應）
    page = browser.new_page(viewport={'width': 1080, 'height': 800})
    page.set_content(html_tall, wait_until='networkidle')
    h2 = page.evaluate('document.body.scrollHeight')
    page.set_viewport_size({'width': 1080, 'height': h2})
    page.screenshot(path='output/card_mobile.png', clip={'x': 0, 'y': 0, 'width': 1080, 'height': h2})

    browser.close()
    print('圖卡已存：output/card_wide.png（桌面版）')
    print('圖卡已存：output/card_mobile.png（手機版）')
"
```

截圖完用 `open output/card.png` 打開給使用者看。

每則聲明一張圖卡，或整合成一張總覽卡，視內容量決定。

### Step 6: 收尾

報告完所有聲明後：

1. **總結手法類型**：這段內容用了什麼手法？
   - 數字灌水（誇大金額/人數）
   - 時間嫁接（舊聞配新日期）
   - 張冠李戴（移花接木）
   - 名人背書（借用權威人物增加可信度）
   - 混合真假（用真實資訊包裝錯誤細節）
   - 情緒操控（用恐懼/憤怒驅動轉傳）

2. **問使用者**：「根據這些比對，你怎麼判斷這段內容？下次看到類似的轉傳，你會注意什麼？」

3. **問是否發布**：「要把這份查核報告發布到網路上嗎？我可以幫你產生一個短網址，方便分享。」

### Step 7: 生成 Slides 報告 + 發布（使用者同意後）

你自己用 Tailwind CSS 生成一份多頁 slides 式 HTML 報告。結構：

```html
<!-- 用 scroll-snap 做成可左右滑的 slides -->
<div class="snap-x snap-mandatory overflow-x-auto flex">
  <!-- Slide 1: 原文 -->
  <section class="snap-center min-w-full">
    原文全文，用 <mark> 高亮標記實體（人=藍、機構=紫、數字=橙、時間=綠、地點=青）
  </section>
  <!-- Slide 2~N: 每則聲明 -->
  <section class="snap-center min-w-full">
    聲明 → KG tags → 比對結果 → 來源連結
  </section>
  <!-- 最後一頁: 總結 -->
  <section class="snap-center min-w-full">
    手法類型 + 整體判定 + 所有來源彙整
  </section>
</div>
```

設計要求：
- 每頁 100vh 高，深色背景，大字
- 底部加頁碼指示器（dots）
- 手機友善（touch scroll）
- 頂部固定 Collatro logo
- 最後一頁放短網址 QR code（如果有）

生成後存到 `output/report.html`，然後：

1. 確認 repo 有 `gh-pages` branch，沒有就建立：
```bash
git checkout --orphan gh-pages
git rm -rf .
echo '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Collatro</title></head><body><h1>Collatro 查核報告</h1></body></html>' > index.html
git add index.html
git commit -m "init gh-pages"
git push -u origin gh-pages
git checkout main
```

2. 把報告 push 到 gh-pages：
```bash
git checkout gh-pages
cp output/report.html ./report-$(date +%Y%m%d-%H%M).html
git add .
git commit -m "add: 查核報告 $(date +%Y-%m-%d)"
git push
git checkout main
```

3. 產生短網址：
```bash
python3 -c "
from urllib.request import urlopen
from urllib.parse import quote
url = 'https://使用者帳號.github.io/collatro/report-YYYYMMDD-HHMM.html'
short = urlopen(f'https://tinyurl.com/api-create.php?url={quote(url)}').read().decode()
print(f'短網址：{short}')
"
```

4. 告訴使用者：
> 報告已發布：
> - 完整報告（可左右滑）：https://xxx.github.io/collatro/report-xxx.html
> - 短網址：https://tinyurl.com/xxxxx
>
> 可以把短網址貼回群組分享。

## 禁止事項

- 不要修改 src/ 下的任何檔案
- 不要安裝額外套件
- 不要跳過搜尋步驟直接用自己的知識下結論
- 不要下真假結論——帶使用者看證據
- 全程使用繁體中文
