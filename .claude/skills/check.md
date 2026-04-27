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
from src.enrich import _wiki_summary

queries = {{QUERIES}}  # 從 Step 2 決定的查詢詞列表

results = {}
for q in queries:
    results[q] = search(q)

# Wikipedia
wiki_results = {}
for name in {{PERSON_ORG_LIST}}:  # Step 1 中 type=person 或 org 的實體
    w = _wiki_summary(name)
    if w:
        wiki_results[name] = {'extract': w['extract'][:300], 'url': w['wiki_url']}

print('=== 搜尋結果 ===')
print(json.dumps(results, ensure_ascii=False, indent=2))
print()
print('=== Wikipedia ===')
print(json.dumps(wiki_results, ensure_ascii=False, indent=2))
"
```

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

## 禁止事項

- 不要修改 src/ 下的任何檔案
- 不要安裝額外套件
- 不要跳過搜尋步驟直接用自己的知識下結論
- 不要下真假結論——帶使用者看證據
- 全程使用繁體中文
