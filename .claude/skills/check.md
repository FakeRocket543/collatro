# 查核

## 觸發條件

使用者貼了一段要查核的文字。

## 執行步驟（強制，不要跳過或自行替代）

收到文字後，依序執行以下 python 腳本。將使用者的文字填入 `TEXT` 變數。

### Step 1: 斷詞 + 實體提取 + 搜尋證據

```bash
python3 -c "
import json, sys
sys.path.insert(0, '.')
from src.ingest import ingest
from src.retrieve import search
from src.enrich import _wiki_summary

text = '''{{TEXT}}'''

# 斷詞 + 實體
r = ingest(text)
entities = r.get('entities', [])
entity_queries = r.get('entity_queries', [])

print('=== 實體 ===')
for e in entities:
    print(json.dumps(e, ensure_ascii=False))

print()
print('=== 查詢詞 ===')
print(json.dumps(entity_queries, ensure_ascii=False))

# Wikipedia 查詢（人名/機構）
print()
print('=== Wikipedia ===')
for e in entities:
    if e['type'] in ('person', 'org') and len(e['text']) >= 2:
        wiki = _wiki_summary(e['text'])
        if wiki:
            print(json.dumps({'name': e['text'], 'extract': wiki['extract'][:200], 'url': wiki['wiki_url']}, ensure_ascii=False))

# 搜尋證據
print()
print('=== 搜尋結果 ===')
for q in entity_queries[:3]:
    results = search(q)
    for ev in results[:2]:
        print(json.dumps({'query': q, 'title': ev['title'], 'url': ev['url'], 'snippet': ev['snippet'][:150]}, ensure_ascii=False))
"
```

### Step 2: 報告

根據 Step 1 的輸出，用正常中文報告：

1. 列出關鍵實體（人/機構/地/數字/時間）
2. Wikipedia 查到的背景資訊，附連結
3. 搜尋結果中與聲明相關的證據，附連結
4. 指出聲明與證據之間的矛盾或吻合
5. 問使用者怎麼判斷

### Step 3: 完整查核（如果本地 LLM 可用）

```bash
python3 -m src.run "{{TEXT}}" --theme sky
```

如果成功，用 `open` 打開 output/ 裡的圖卡。
如果 LLM 不可用，跳過此步，Step 2 的報告已足夠。

## 禁止事項

- 不要修改 src/ 下的任何檔案
- 不要安裝額外套件
- 不要用自己的知識替代搜尋結果
- 不要下真假結論
