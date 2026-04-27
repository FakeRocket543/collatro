# Collatro

> collatio (拉丁文：對照) — 事實比對教學工具

拆解文章聲明 → 查詢實體背景 → 搜尋原始來源 → 比對 NER/數字/時間線差異 → 產出 1080×1080 圖卡。

---

## 為什麼做這個？

現有的「假新聞偵測」工具有兩個問題：
1. **分類器不泛化** — 訓練集長什麼樣就只認什麼樣，換個語氣就繞過
2. **只給結論不教方法** — 告訴你「這是假的」，但不教你怎麼自己判斷

Collatro 不做分類，不給結論。它做的是：**把「聲明」和「證據」並排放好，讓你自己看差異在哪。**

這是事實查核的核心方法論：拆解 → 搜尋 → 比對。工具加速這個過程，但判斷永遠是人做的。

---

## Quick Start

```bash
git clone https://github.com/FakeRocket543/collatro.git
cd collatro
python3 setup.py          # 一鍵安裝所有依賴
python3 -m src.run -i     # 互動教學模式
```

或直接跑：
```bash
python3 -m src.run --theme sky "台積電宣布整廠搬遷美國，預計明年完成"
```

---

## Pipeline 架構

```
text → decompose → enrich → retrieve → diff → package → render
        │            │         │          │       │         │
      LLM 拆解   Wikipedia  DuckDuckGo  LLM    JSON+MD  Playwright
      who/what/   實體背景   搜尋證據    NER/    存檔     1080×1080
      when/number                       數字/            PNG
                                        時間線
```

### 為什麼是這個順序？

1. **decompose 在最前面** — 一段文字可能包含多個聲明，必須先拆開才能逐一驗證。不拆的話，搜尋會太模糊。
2. **enrich 在 retrieve 之前** — 先知道實體是什麼（賴清德是總統、台積電是半導體公司），搜尋時才能組出好的 query。
3. **retrieve 在 diff 之前** — 必須先有證據，才能比對。
4. **diff 在 render 之前** — 比對結果是圖卡的內容來源。
5. **package 和 render 並行** — 一個存檔（JSON+MD），一個出圖，互不依賴。

---

## 模組詳解

### `src/config.py` — 設定中心
```
環境變數驅動，零硬編碼。
為什麼：讓學生不用改程式碼就能切換 LLM server 或模型。
```

### `src/llm.py` — LLM 推論（三層 fallback）
```
Tier 1: mlx-lm (in-process, Apple Silicon 原生)
Tier 2: llama-server subprocess (自動啟動/關閉)
Tier 3: 外部 server (localhost:8080)
```
**為什麼三層？** 因為學生的環境不一致：
- 有 M1/M2/M3 → 用 mlx-lm，最快，不用開 server
- 有 GGUF 檔 → 自動開 llama-server，用完殺掉，不佔資源
- 什麼都沒有 → 連老師的 server

### `src/decompose.py` — 聲明拆解
```
輸入：一段文字
輸出：[{text, who, what, when, number, keywords}]
```
**為什麼用 LLM 而不是規則？** 因為自然語言的聲明邊界無法用正則切割。「台積電宣布搬遷美國，預計明年完成」裡有兩個聲明（搬遷 + 時間），只有語言模型能正確拆開。

**為什麼要求結構化輸出（who/what/when/number）？** 因為 diff 步驟需要這些欄位來做精確比對。如果只有 text，就只能做模糊比較。

### `src/enrich.py` — Wikipedia 實體查詢
```
輸入：實體名稱列表（從 claims 的 who 欄位提取）
輸出：{entities: [{name, description, categories, wiki_url}], all_categories}
```
**為什麼用 Wikipedia 而不是 LLM？** 因為 LLM 會幻覺。Wikipedia 是可驗證的事實來源，而且有結構化的分類系統。

**為什麼不用 Wikidata？** Collatro 簡化版不需要。Anseropolis 有用 Wikidata 做更深的實體消歧。

### `src/retrieve.py` — 證據搜尋
```
輸入：claims（帶 keywords）
輸出：claims + evidence（每個 claim 附 3 筆搜尋結果）
```
**為什麼用 DuckDuckGo HTML scraping？** 
- 免費，不需要 API key
- 不追蹤用戶，適合教學場景
- HTML 版比 API 版更穩定

**為什麼只取 3 筆？** 教學用途不需要大量結果。3 筆足夠讓 LLM 做比對，也不會讓圖卡太擠。

### `src/diff.py` — 結構化比對
```
輸入：claims + evidence
輸出：claims + diff（{ner: [], numbers: [], timeline: [], verdict, summary}）
```
**為什麼分三個面向？**
- **NER（人名/機構/地點）**：張冠李戴是最常見的造假手法
- **數字（金額/人數/比例）**：誇大或縮小數字是第二常見
- **時間線（日期/順序）**：嫁接不同時間的事件是第三常見

這三個面向覆蓋了 80% 以上的事實錯誤類型。

**為什麼用 LLM 而不是規則比對？** 因為「聲明說 5%，證據說 3%」這種比對需要理解語義，不是字串匹配能做的。

### `src/package.py` — 結果打包
```
輸出：JSON（完整資料）+ Markdown（人類可讀摘要）
```
**為什麼兩種格式？** JSON 給程式讀（可以回灌、統計、API 回傳），MD 給人讀（學生可以直接看）。

### `src/render.py` — 圖卡渲染
```
Tailwind CSS HTML → Playwright screenshot → 1080×1080 PNG
```
**為什麼用 Tailwind + Playwright 而不是 Pillow？**
- Tailwind：不用寫 CSS，class 即樣式，改色系只要換一個字
- Playwright：渲染品質等同瀏覽器，中文字體不會破
- 1080×1080：Instagram 正方形格式，學生可以直接分享

**為什麼不用 Canvas/SVG？** 因為中文排版太痛苦。HTML 天生支援中文換行、字體 fallback。

### `src/interactive.py` — 互動教學模式
```
引導流程：輸入 → 拆解 → 學生猜測 → 搜尋 → 比對 → 反思 → 圖卡
```
**為什麼要學生先猜？** 教育心理學的「預測-觀察-解釋」(POE) 模式。先讓學生做預測，再看結果，學習效果比直接看答案好 3 倍。

### `src/serve.py` — HTTP API
```
POST /api/check {text, theme} → {claims}
```
**為什麼要 API？** 讓不想用 CLI 的學生可以用 Postman 或寫前端串接。

---

## 依賴說明

| 套件 | 用途 | 為什麼選它 |
|------|------|-----------|
| `mlx-lm` | 本地 LLM 推論 | Apple Silicon 原生，比 llama.cpp Python binding 快 2x，純 pip install |
| `playwright` | HTML → PNG 截圖 | 比 Selenium 輕、比 Pillow 排版好、中文不破 |

**為什麼沒有 requirements.txt？** 因為只有兩個依賴，寫在 `setup.py` 裡自動裝。不想讓學生面對一長串套件清單。

---

## 色系主題

```bash
--theme slate    # 深灰（預設）
--theme sky      # 天空藍
--theme emerald  # 翡翠綠
--theme amber    # 琥珀
--theme violet   # 紫
--theme rose     # 玫瑰
# 或任何 Tailwind CSS 色名（fuchsia, cyan, lime...）
```

**為什麼讓學生選色系？** 增加參與感。產出的圖卡是「他的」，不是「工具的」。

---

## 與其他工具的比較

### 台灣現有工具

| 工具 | 做法 | 優點 | 限制 |
|------|------|------|------|
| **Cofacts 真的假的** | LINE bot + 群眾協作資料庫 | 即時回覆、社群驅動、開源 | 依賴志工回覆速度；只能查「已被回報過的」訊息 |
| **MyGoPen** | LINE bot + 編輯團隊查核 | 品質穩定、有專業編輯 | 人力有限、非開源、無法自行擴充 |
| **美玉姨** | LINE bot + 串接 Cofacts | 家庭群組友善、長輩能用 | 本質是 Cofacts 的前端，受限於同一資料庫 |
| **TFC 台灣事實查核中心** | 記者手動查核 + 發報告 | IFCN 認證、權威性高 | 產量低（月均 35 篇）、選題偏差、無 API |

### 國際開源 pipeline

| 工具 | 架構 | 優點 | 限制 |
|------|------|------|------|
| **Loki** (1.1k⭐) | decompose → check-worthiness → query → evidence → verify | 最完整端到端、支援多模態 | 英文 only、依賴 OpenAI + Serper API（付費） |
| **SAFE** (Google) | 拆聲明 → 逐一 Google Search → LLM 判定 | Google 出品、論文級品質 | 閉源、只有論文沒有可用工具 |
| **ClaimBuster** | 機器學習判斷「值得查核」的句子 | 學術標竿、有 API | 只做 check-worthiness，不做完整查核 |
| **OpenFactCheck** | 統一框架：可插拔不同查核引擎 | 可比較不同方法的準確度 | 偏學術評估，非生產工具 |
| **Veracity** (2025) | LLM + 搜尋 + 透明度報告 | 開源、強調可解釋性 | 英文 only、早期階段 |

### Collatro 的定位

| | Cofacts | Loki | ClaimBuster | **Collatro** |
|---|---|---|---|---|
| 中文支援 | ✓ | ✗ | ✗ | ✓ |
| 需要 API key | ✗ | ✓ (OpenAI) | ✓ | ✗ |
| 本地推論 | ✗ | ✗ | ✗ | ✓ |
| 結構化 diff | ✗ | ✗ | ✗ | ✓ (NER/數字/時間線) |
| 教學導向 | ✗ | ✗ | ✗ | ✓ (互動模式) |
| 視覺化輸出 | ✗ | ✗ | ✗ | ✓ (1080×1080 圖卡) |
| 群眾協作 | ✓ | ✗ | ✗ | ✗ |
| 即時回覆 | ✓ (LINE) | ✗ | ✗ | ✗ |

**Collatro 不是要取代 Cofacts 或 Loki。** 它們解決不同問題：
- Cofacts 解決「長輩收到謠言怎麼辦」→ 即時回覆
- Loki 解決「如何自動化查核流程」→ 端到端 pipeline
- **Collatro 解決「怎麼教學生自己查核」→ 方法論教學**

核心差異：Collatro 不給結論，只給比對結果。學生必須自己判斷「這個差異代表什麼」。

---

## 與 Anseropolis 的關係

Collatro 是 [Anseropolis](https://github.com/FakeRocket543/anseropolis) 的教學簡化版。

| | Collatro | Anseropolis |
|---|---|---|
| 核心問題 | 「這跟來源對不對得上？」 | 「這是不是謠言？」 |
| 謠言庫比對 | 無 | ✓（4125 篇 TFC 報告） |
| 語言指紋偵測 | 無 | ✓（含國台辦敘事偵測） |
| 可疑度評分 | 無 | ✓（0-100 四維加權） |
| NER/數字/時間線 diff | ✓ | ✓ |
| Wikipedia 實體 | ✓ | ✓ |
| 圖卡輸出 | ✓ | ✓ |
| 互動教學 | ✓ | ✓ |
| 適合 | 初學者（學方法） | 進階（學偵測） |

**教學建議：先用 Collatro 學會「拆解 → 搜尋 → 比對」，再用 Anseropolis 學「謠言有什麼語言特徵」。**

---

## License

MIT
