# Collatro — 貼上就查

<div align="center">
  <img src="assets/collatro_logo.webp" alt="Collatro Logo" width="300"/>
</div>

> **collatro** (拉丁文雙關語)
> 1. *collatio*: 對照、比對
> 2. *collatro*: 對著...狂吠、齊聲抨擊
> 
> **Collatro — 像看門鵝一樣的事實比對工具**

CKIP 斷詞 → 實體提取 → Wikidata KG → 搜尋引擎比對 → Slides 報告 + 圖卡。

---

## 快速開始

```bash
git clone https://github.com/FakeRocket543/collatro.git
cd collatro
python3 setup.py
```

安裝完成後，在 collatro 目錄裡打開 AI Agent（OpenCode / Kiro CLI / Claude Code），貼一段你想查核的內容，agent 會自動引導完成查核。

---

## 為什麼做這個？

現有的「假新聞偵測」工具有兩個問題：
1. **分類器不泛化** — 訓練集長什麼樣就只認什麼樣，換個語氣就繞過
2. **只給結論不教方法** — 告訴你「這是假的」，但不教你怎麼自己判斷

Collatro 不做分類，不給結論。它做的是：**把「聲明」和「證據」並排放好，讓你自己看差異在哪。**

---

## 架構

```
輸入文字
  ↓
CKIP 斷詞 + 實體提取（人/機構/地/時/事/數字）
  ↓
Wikidata KG 查詢（結構化事實：出生/死亡/職業/國籍/死因）
  ↓
搜尋引擎比對（Searxng 優先，DuckDuckGo fallback）
  ↓
Agent 拆解聲明 + 比對差異（NER/數字/時間線）
  ↓
產出：三種圖卡 + Slides HTML 報告 + GitHub Pages 短網址
```

## 圖卡輸出

每則聲明自動生成三種尺寸：

| 格式 | 尺寸 | 用途 |
|------|------|------|
| 橫式 | 1080×auto（最小 600px） | 桌面分享、Facebook、Twitter |
| Reels | 1080×1920 | IG Story、Reels、TikTok |
| 正方形 | 1080×1080 | IG Post、LINE 群組 |

輸出檔案：`output/claim_1.png`、`claim_1_reels.png`、`claim_1_square.png`

## 特色

- **Wikidata KG** — 結構化事實優先採信，不靠 LLM 記憶
- **可追溯** — 每個判定都附來源連結，任何人可驗證
- **不下結論** — 工具呈現差異，判斷由人做
- **Agent 驅動** — 使用者只需貼文字和回答問題，其他全自動
- **三種圖卡** — 橫式 / Reels / 正方形，一次生成全平台適用
- **GitHub Pages 發布** — 一鍵產生短網址，貼回群組

## 選配

| 項目 | 用途 | 設定 |
|------|------|------|
| Searxng | 更好的搜尋（不限流、繁中優先） | `export COLLATRO_SEARXNG_URL=http://localhost:8888` |
| 本地 LLM | 離線拆解聲明 | 預設 3B，`export COLLATRO_MLX_MODEL=mlx-community/Ministral-3-8B-Instruct-2512-8bit` 升級 8B |

不裝選配也能用——Agent 自己處理拆解和比對。

## 系統需求

- macOS（Apple Silicon）或 Linux
- Python 3.10+
- AI Agent（OpenCode / Kiro CLI / Claude Code）

## 授權

MIT
