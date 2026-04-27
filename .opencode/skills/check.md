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
- 寬度固定 1080px，高度自適應內容
- 深色背景（用使用者指定的 theme 色系，預設 sky）
- 頂部：Collatro logo + 「事實比對卡」
- 原始聲明區塊（深色卡片）
- KG tags（Wikidata 結構化資料做成彩色 pill badges：出生/死亡/職業/國籍等）
- 判定結果（大字，紅/綠/黃）
- 比對差異（NER/數字/時間 分類標籤 + 聲明 vs 證據）
- 參考來源（標題 + 短 URL，最多 4 筆）
- 底部可放短網址（如果有的話）

截圖指令：

```bash
python3 -c "
from playwright.sync_api import sync_playwright
from pathlib import Path

html = '''{{你生成的完整 HTML}}'''

Path('output').mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1080, 'height': 800})
    page.set_content(html, wait_until='networkidle')
    height = page.evaluate('document.body.scrollHeight')
    page.set_viewport_size({'width': 1080, 'height': height})
    page.screenshot(path='output/card.png', clip={'x': 0, 'y': 0, 'width': 1080, 'height': height})
    browser.close()
    print('圖卡已存：output/card.png')
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

### Step 7: 發布報告（使用者同意後）

1. 確認 repo 有 `gh-pages` branch，沒有就建立：
```bash
git checkout --orphan gh-pages
git rm -rf .
echo "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Collatro Reports</title></head><body><h1>Collatro 查核報告</h1></body></html>" > index.html
git add index.html
git commit -m "init gh-pages"
git push -u origin gh-pages
git checkout main
```

2. 把 output 裡的 HTML 報告複製到 gh-pages branch 並 push：
```bash
git checkout gh-pages
cp ../output/報告檔名.html ./
git add .
git commit -m "add: 查核報告 YYYY-MM-DD"
git push
git checkout main
```

3. 產生短網址：
```bash
python3 -c "
from urllib.request import urlopen
from urllib.parse import quote
url = 'https://使用者帳號.github.io/collatro/報告檔名.html'
short = urlopen(f'https://is.gd/create.php?format=simple&url={quote(url)}').read().decode()
print(f'短網址：{short}')
"
```

4. 告訴使用者：
> 報告已發布：
> - 完整報告：https://xxx.github.io/collatro/報告名.html
> - 短網址：https://is.gd/xxxxx
>
> 可以把短網址貼回群組，讓其他人也看到查核結果。

## 禁止事項

- 不要修改 src/ 下的任何檔案
- 不要安裝額外套件
- 不要跳過搜尋步驟直接用自己的知識下結論
- 不要下真假結論——帶使用者看證據
- 全程使用繁體中文
