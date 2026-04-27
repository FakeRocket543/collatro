# Collatro

> collatio (拉丁文：對照) — 事實比對教學工具

斷詞 + NER → 拆解聲明 → 查詢實體背景 → 搜尋來源 → 比對 NER/數字/時間線差異 → 產出 1080×1080 圖卡。

---

## 為什麼做這個？

現有的「假新聞偵測」工具有兩個問題：
1. **分類器不泛化** — 訓練集長什麼樣就只認什麼樣，換個語氣就繞過
2. **只給結論不教方法** — 告訴你「這是假的」，但不教你怎麼自己判斷

Collatro 不做分類，不給結論。它做的是：**把「聲明」和「證據」並排放好，讓你自己看差異在哪。**

這是事實查核的核心方法論：拆解 → 搜尋 → 比對。工具加速這個過程，但判斷永遠是人做的。

---

## 安裝

### 方法一：一鍵安裝（推薦）

```bash
git clone https://github.com/FakeRocket543/collatro.git
cd collatro
python3 setup.py
```

`setup.py` 會自動完成：
- 安裝 mlx-lm（本地 LLM 推論）
- 安裝 playwright + chromium（圖卡截圖）
- 下載 Mistral 8B 模型（首次約 4.5GB）

### 方法二：手動安裝

```bash
git clone https://github.com/FakeRocket543/collatro.git
cd collatro

# 核心依賴
pip install mlx-lm playwright
playwright install chromium

# 選配：精確中文斷詞（不裝會用 jieba）
pip install ckip-transformers

# 選配：jieba（輕量斷詞 fallback）
pip install jieba
```

### 系統需求

| 項目 | 最低 | 建議 |
|------|------|------|
| Python | 3.11 | 3.12 |
| macOS | 13.5 (Ventura) | 14+ (Sonoma) |
| RAM | 8GB（用 3B 模型） | 16GB+（用 8B 模型） |
| 晶片 | Apple Silicon (M1+) | M2/M3 |
| 磁碟 | 5GB（模型快取） | — |

---

## 使用方式

### 1. 互動教學模式（推薦給學生）

```bash
python3 -m src.run --interactive
python3 -m src.run -i --theme violet
```

互動流程：
```
1️⃣  貼上一段文字（新聞、社群貼文、LINE 轉傳）
2️⃣  AI 斷詞 + 辨識實體（人名、機構、地點）
3️⃣  AI 拆解出裡面的事實聲明
4️⃣  你來猜：哪些聲明可能有問題？
5️⃣  搜尋證據，看看實際情況
6️⃣  比對差異：人名、數字、時間線
7️⃣  反思 + 產出圖卡
```

### 2. CLI 模式（一行跑完）

```bash
# 基本
python3 -m src.run "台積電宣布整廠搬遷美國，預計明年完成"

# 指定色系
python3 -m src.run --theme sky "待查核文字"

# 從檔案讀取
python3 -m src.run --file article.txt --theme emerald
```

### 3. HTTP API（給前端或 Postman）

```bash
python3 -m src.serve --port 9001

# 另一個 terminal
curl -X POST http://localhost:9001/api/check \
  -H "Content-Type: application/json" \
  -d '{"text": "台積電宣布...", "theme": "sky"}'
```

### 4. 色系主題

```bash
--theme slate    # 深灰（預設）
--theme sky      # 天空藍
--theme emerald  # 翡翠綠
--theme amber    # 琥珀
--theme violet   # 紫
--theme rose     # 玫瑰
# 或任何 Tailwind CSS 色名（fuchsia, cyan, lime, teal...）
```

讓學生自己選，產出的圖卡是「他的」。

---

## 產出

每次執行會產生：

```
output/
├── <slug>_<timestamp>.json   # 完整結果（聲明、證據、diff、實體）
├── <slug>_<timestamp>.md     # Markdown 摘要（人類可讀）
├── claim_1.png               # 1080×1080 圖卡（每個聲明一張）
├── claim_2.png
└── ...
```

---

## Pipeline 架構

```
text → ingest → decompose → enrich → retrieve → diff → package → render
         │         │           │         │         │       │         │
       CKIP/     LLM       Wikipedia  DuckDuckGo  LLM   JSON+MD  Playwright
       jieba    拆聲明      實體背景   搜尋證據   NER/    存檔     1080×1080
       斷詞/NER  who/what/                       數字/
                 when/number                     時間線
```

### 為什麼是這個順序？

1. **ingest 最先** — 斷詞 + NER 提取實體，給後續 enrich 用。不斷詞就不知道「賴清德」是一個人名。
2. **decompose 第二** — 一段文字可能包含多個聲明，必須先拆開才能逐一驗證。
3. **enrich 在 retrieve 之前** — 先知道實體是什麼（賴清德是總統、台積電是半導體公司），搜尋時才能組出好的 query。
4. **retrieve 在 diff 之前** — 必須先有證據，才能比對。
5. **diff 在 render 之前** — 比對結果是圖卡的內容來源。
6. **package 和 render 並行** — 一個存檔，一個出圖，互不依賴。

---

## 模組詳解

### `src/ingest.py` — 斷詞 + NER
```
輸入：文字
輸出：{ws, pos, keywords, entities, backend}
三層 fallback：MLX CKIP → ckip-transformers → jieba
```
**為什麼要斷詞？** 中文沒有空格，不斷詞就不能辨識「賴清德」是一個詞還是三個字。NER 從詞性標記中提取人名(Nb)、機構(Nc)、地點(Ncd)。

### `src/llm.py` — LLM 推論（三層 fallback）
```
Tier 1: mlx-lm (in-process, Apple Silicon 原生，最快)
Tier 2: llama-server subprocess (自動啟動，用完殺掉)
Tier 3: 外部 server (連老師的機器)
```
**為什麼三層？** 學生環境不一致。有 Apple Silicon 的用 Tier 1，沒有的連老師 server (Tier 3)。

### `src/decompose.py` — 聲明拆解
```
輸入：文字
輸出：[{text, who, what, when, number, keywords}]
```
**為什麼用 LLM？** 自然語言的聲明邊界無法用規則切割。「台積電宣布搬遷美國，預計明年完成」裡有兩個聲明，只有語言模型能正確拆開。

**為什麼要結構化輸出？** diff 步驟需要 who/what/when/number 來做精確比對。

### `src/enrich.py` — Wikipedia 實體查詢
```
輸入：實體名稱列表
輸出：{entities: [{name, description, categories, wiki_url}]}
```
**為什麼用 Wikipedia 而不是 LLM？** LLM 會幻覺。Wikipedia 是可驗證的事實來源。

### `src/retrieve.py` — 證據搜尋
```
輸入：claims（帶 keywords）
輸出：claims + evidence（每個 claim 附 3 筆搜尋結果）
```
**為什麼用 DuckDuckGo？** 免費、不需要 API key、不追蹤用戶。

### `src/diff.py` — 結構化比對
```
輸入：claims + evidence
輸出：claims + diff（{ner, numbers, timeline, verdict, summary}）
```
**三個面向：**
- **NER**：人名/機構有沒有被張冠李戴
- **數字**：金額/人數/比例有沒有被改
- **時間線**：事件順序有沒有被倒置或嫁接

這三個覆蓋 80% 以上的事實錯誤類型。

### `src/package.py` — 結果打包
```
輸出：JSON（完整資料）+ Markdown（人類可讀）
```

### `src/render.py` — 圖卡渲染
```
Tailwind CSS HTML → Playwright screenshot → 1080×1080 PNG
```
**為什麼 Tailwind + Playwright？** 中文排版好、改色系只要換一個字、品質等同瀏覽器。

### `src/interactive.py` — 互動教學模式
**為什麼要學生先猜？** 教育心理學的 POE 模式（預測-觀察-解釋）。先預測再看結果，學習效果比直接看答案好。

### `src/serve.py` — HTTP API

---

## 依賴說明

| 套件 | 用途 | 為什麼選它 | 必要？ |
|------|------|-----------|--------|
| `mlx-lm` | 本地 LLM 推論 | Apple Silicon 原生，純 pip install | 選配（可連外部 server） |
| `playwright` | HTML → PNG 截圖 | 中文排版好、比 Pillow 強 | 必要（產圖卡） |
| `ckip-transformers` | 精確中文斷詞 + NER | 學術級、詞性標記準確 | 選配（fallback 到 jieba） |
| `jieba` | 輕量中文斷詞 | 免模型下載、2 秒裝完 | 選配（CKIP 的 fallback） |

**設計原則：最少依賴。** 核心只需要 mlx-lm（或外部 server）+ playwright。斷詞是選配加分。

---

## 環境變數

| 變數 | 預設 | 說明 |
|------|------|------|
| `COLLATRO_LLM_URL` | `http://localhost:8080/v1/chat/completions` | LLM API 位址 |
| `COLLATRO_LLM_MODEL` | `mistral` | 模型名稱 |
| `COLLATRO_MLX_MODEL` | `mlx-community/Ministral-8B-Instruct-2412-4bit` | mlx-lm 模型 ID |
| `COLLATRO_GGUF` | （空） | GGUF 檔路徑（Tier 2 用） |
| `COLLATRO_CKIP_DIR` | （空） | MLX CKIP 模型目錄 |
| `COLLATRO_CKIP_BATCH_PY` | （空） | ckip_batch.py 路徑 |

---

## 與其他工具的比較

### 台灣現有工具

| 工具 | 做法 | 優點 | 限制 |
|------|------|------|------|
| **Cofacts 真的假的** | LINE bot + 群眾協作資料庫 | 即時回覆、社群驅動、開源 | 依賴志工回覆速度；只能查「已被回報過的」 |
| **MyGoPen** | LINE bot + 編輯團隊 | 品質穩定 | 人力有限、非開源 |
| **美玉姨** | LINE bot + 串接 Cofacts | 長輩友善 | 受限於 Cofacts 資料庫 |
| **TFC** | 記者手動查核 | IFCN 認證、權威性高 | 產量低、選題偏差、無 API |

### 國際開源 pipeline

| 工具 | 架構 | 優點 | 限制 |
|------|------|------|------|
| **Loki** (1.1k⭐) | decompose → worthiness → query → evidence → verify | 最完整端到端、多模態 | 英文 only、依賴 OpenAI + Serper（付費） |
| **SAFE** (Google) | 拆聲明 → Google Search → LLM 判定 | 論文級品質 | 閉源 |
| **ClaimBuster** | ML 判斷 check-worthiness | 學術標竿 | 只做第一步，不做完整查核 |
| **OpenFactCheck** | 統一評估框架 | 可比較不同方法 | 偏學術，非生產工具 |

### Collatro 的定位

| | Cofacts | Loki | **Collatro** |
|---|---|---|---|
| 中文支援 | ✓ | ✗ | ✓ |
| 需要 API key | ✗ | ✓ | ✗ |
| 本地推論 | ✗ | ✗ | ✓ |
| 斷詞 + NER | ✗ | ✗ | ✓ (CKIP/jieba) |
| 結構化 diff | ✗ | ✗ | ✓ (NER/數字/時間線) |
| 教學導向 | ✗ | ✗ | ✓ (互動模式) |
| 視覺化輸出 | ✗ | ✗ | ✓ (1080×1080 圖卡) |
| 群眾協作 | ✓ | ✗ | ✗ |

**Collatro 不是要取代 Cofacts 或 Loki。** 它們解決不同問題：
- Cofacts：「長輩收到謠言怎麼辦」→ 即時回覆
- Loki：「如何自動化查核」→ 端到端 pipeline
- **Collatro：「怎麼教學生自己查核」→ 方法論教學**

---

## 與 Anseropolis 的關係

Collatro 是 [Anseropolis](https://github.com/FakeRocket543/anseropolis) 的教學簡化版。

| | Collatro | Anseropolis |
|---|---|---|
| 核心問題 | 「這跟來源對不對得上？」 | 「這是不是謠言？」 |
| 謠言庫比對 | 無 | ✓（4125 篇 TFC 報告） |
| 語言指紋偵測 | 無 | ✓（含國台辦敘事偵測） |
| 可疑度評分 | 無 | ✓（0-100 四維加權） |
| 斷詞 + NER | ✓ | ✓ |
| 結構化 diff | ✓ | ✓ |
| Wikipedia 實體 | ✓ | ✓ |
| 圖卡輸出 | ✓ | ✓ |
| 互動教學 | ✓ | ✓ |
| 適合 | 初學者（學方法） | 進階（學偵測） |

**教學建議：先用 Collatro 學會「拆解 → 搜尋 → 比對」，再用 Anseropolis 學「謠言有什麼語言特徵」。**

---

## License

MIT
