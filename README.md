# Collatro

> collatio (拉丁文：對照) — 事實比對教學工具

拆解文章聲明 → 查詢實體背景 → 搜尋原始來源 → 比對 NER/數字/時間線差異 → 產出 1080×1080 圖卡。

## Quick Start

```bash
# 1. 安裝 Playwright
pip install playwright && playwright install chromium

# 2. 啟動 LLM（Mistral 3B/8B Q8）
llama-server -m mistral-*.gguf --port 8080 -ngl 99 &

# 3. 跑
python -m src.run "台積電宣布整廠搬遷美國，預計明年完成"

# 4. 互動教學模式
python -m src.run --interactive
```

## Pipeline

```
text → decompose → enrich → retrieve → diff → package → render
        │            │         │          │       │         │
      LLM 拆解   Wikipedia  DuckDuckGo  LLM    JSON+MD  Playwright
      who/what/   實體背景   搜尋證據    NER/    存檔     1080×1080
      when/number                       數字/            PNG
                                        時間線
```

## 使用方式

### CLI 模式
```bash
python -m src.run "待查核文字"
python -m src.run --file article.txt
python -m src.run --theme sky "待查核文字"
```

### 互動教學模式（推薦給學生）
```bash
python -m src.run --interactive
python -m src.run -i --theme violet
```

引導學生逐步完成：
1. 貼上可疑文字
2. AI 拆解聲明
3. 學生先猜哪些有問題
4. 搜尋證據
5. 比對差異
6. 反思 + 產出圖卡

### HTTP API
```bash
python -m src.serve --port 9001
curl -X POST http://localhost:9001/api/check \
  -H "Content-Type: application/json" \
  -d '{"text": "...", "theme": "sky"}'
```

## 色系主題

```bash
--theme slate    # 深灰（預設）
--theme sky      # 天空藍
--theme emerald  # 翡翠綠
--theme amber    # 琥珀
--theme violet   # 紫
--theme rose     # 玫瑰
# 或任何 Tailwind CSS 色名
```

## 環境變數

| 變數 | 預設 | 說明 |
|------|------|------|
| `COLLATRO_LLM_URL` | `http://localhost:8080/v1/chat/completions` | LLM API |
| `COLLATRO_LLM_MODEL` | `mistral` | 模型名稱 |

## 產出

- `output/<slug>_<timestamp>.json` — 完整結果（聲明、證據、diff、實體）
- `output/<slug>_<timestamp>.md` — Markdown 摘要
- `output/claim_N.png` — 1080×1080 圖卡

## 與 Anseropolis 的關係

| | Collatro | Anseropolis |
|---|---|---|
| 定位 | 事實比對教學 | 謠言偵測 + 查核 |
| 核心問題 | 「這跟來源對不對得上？」 | 「這是不是謠言？」 |
| 謠言庫 | 無 | 4125 篇 TFC |
| 語言指紋 | 無 | 有（含國台辦偵測） |
| 可疑度評分 | 無 | 0-100 |
| 適合 | 初學者 | 進階 |

## License

MIT
