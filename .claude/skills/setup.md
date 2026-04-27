# Collatro 環境設定 Skill

## 觸發條件

當學生第一次使用 Collatro，或遇到 ImportError / 環境問題時，執行以下引導。

## 自動設定流程

請依序執行以下步驟，每步確認成功後再繼續：

### 1. 確認 Python 版本
```bash
python3 --version
```
需要 3.11+。如果不夠，請學生用 `brew install python@3.12`。

### 2. 安裝依賴
```bash
pip install mlx-lm playwright
```

### 3. 安裝瀏覽器引擎（給 Playwright 截圖用）
```bash
playwright install chromium
```

### 4. 下載 LLM 模型（首次約 4.5GB，之後不用重下）
```bash
python3 -c "from mlx_lm import load; load('mlx-community/Ministral-8B-Instruct-2412-4bit')"
```
這步會花 2-5 分鐘，取決於網速。下載完後模型會快取在 `~/.cache/huggingface/`。

### 5. 驗證
```bash
cd /path/to/collatro
python3 -m src.run "測試：台積電市值超過10兆美元"
```
如果看到 `✓ 完成` 和 `output/claim_1.png`，就成功了。

## 常見問題

- **pip 找不到 mlx-lm**：確認用的是 `pip3` 或 `python3 -m pip install mlx-lm`
- **mlx-lm 安裝失敗**：需要 macOS 13.5+ 和 Apple Silicon (M1/M2/M3)
- **playwright install 卡住**：等它下載完，或重跑
- **模型下載中斷**：重跑第 4 步，會從斷點續傳
- **記憶體不足 (8GB Mac)**：改用小模型 `COLLATRO_MLX_MODEL=mlx-community/Ministral-3B-Instruct-2512-4bit`

## 如果 mlx-lm 無法使用

不需要外部 server。在 Claude Code 中操作時，AI 會直接代勞 LLM 步驟（decompose、diff），學生仍然可以完成完整流程。
