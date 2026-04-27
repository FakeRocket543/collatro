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

根據 Step 1 的輸出，用正常中文報告。每則聲明必須包含：

1. **原文段落**：引用原文中對應的句子
2. **比對結果**：聲明說什麼 vs 證據說什麼
3. **參考資料**：附上搜尋結果的標題和 URL、Wikipedia 連結
4. **判定**：吻合 / 不一致 / 資訊不足

範例格式：

> **聲明：**「王永慶也是因為喝水嗆到，而引發肺炎致死」
>
> **比對：** 多家媒體報導指出王永慶係因心肺衰竭辭世，並非喝水嗆到。
>
> **來源：**
> - [王永慶逝世 - 維基百科](https://zh.wikipedia.org/wiki/...)
> - [台灣事實查核中心報告](https://tfc-taiwan.org.tw/...)
>
> **判定：** ✗ 不一致（死因與公開紀錄矛盾）

最後問使用者怎麼判斷。

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
