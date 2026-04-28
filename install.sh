#!/bin/bash
# ============================================================
# 🚀 W10 查核管線一鍵安裝
# 版本：2026-04-28
# ============================================================
#
# 安裝項目：
#   1. Homebrew
#   2. iTerm2 + 深色主題
#   3. Node.js
#   4. kiro-cli      — Claude（免費）
#   5. OpenAI Codex  — GPT（免費）
#   6. Gemini CLI    — Gemini（免費）
#   7. Collatro      — 查核管線（含 Python 依賴）
#   8. 工作區設定
#
# 用法：
#   curl -fsSL https://172329.xyz/20260428/install.sh | bash
# ============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}✓${NC} $1"; }
warn()  { echo -e "${YELLOW}⚠${NC} $1"; }

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  🦆 W10 查核管線安裝（Collatro）                     ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── 1. Homebrew ──
echo "── 1/8 Homebrew ──"
if ! command -v brew &>/dev/null; then
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" </dev/null
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi
info "Homebrew OK"

# ── 2. 終端機 ──
echo "── 2/8 iTerm2（深色）──"
brew list --cask iterm2 &>/dev/null 2>&1 || brew install --cask iterm2
info "iTerm2 OK"

# ── 3. Node.js ──
echo "── 3/8 Node.js ──"
command -v node &>/dev/null || brew install node
info "Node.js OK ($(node --version))"

# ── 4. kiro-cli ──
echo "── 4/8 kiro-cli（Claude 免費）──"
if ! command -v kiro-cli &>/dev/null; then
    curl -fsSL https://cli.kiro.dev/install | bash 2>/dev/null
    # 確保 ~/.local/bin 在 PATH（kiro-cli 裝在這裡）
    if ! grep -q '.local/bin' ~/.zshrc 2>/dev/null; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
    fi
    export PATH="$HOME/.local/bin:$PATH"
fi
info "kiro-cli OK"

# ── 5. OpenAI Codex CLI ──
echo "── 5/8 OpenAI Codex CLI（GPT 免費）──"
if ! command -v codex &>/dev/null; then
    npm install -g @openai/codex 2>/dev/null || warn "codex 安裝失敗，可稍後手動裝"
fi
command -v codex &>/dev/null && info "codex OK" || warn "codex 跳過"

# ── 6. Gemini CLI ──
echo "── 6/8 Gemini CLI（Gemini 免費）──"
if ! command -v gemini &>/dev/null; then
    npm install -g @google/gemini-cli 2>/dev/null || warn "gemini CLI 安裝失敗"
fi
command -v gemini &>/dev/null && info "gemini OK" || warn "gemini 跳過，可稍後手動裝"

# ── 7. Collatro ──
echo "── 7/8 Collatro（查核管線）──"
COLLATRO_DIR="$HOME/collatro"
if [ ! -d "$COLLATRO_DIR" ]; then
    git clone https://github.com/FakeRocket543/collatro.git "$COLLATRO_DIR" 2>/dev/null
fi
if [ -f "$COLLATRO_DIR/setup.py" ]; then
    cd "$COLLATRO_DIR" && python3 setup.py 2>/dev/null
    cd - >/dev/null
fi
info "Collatro OK（~/collatro）"

# ── 8. 工作區設定 ──
echo "── 8/8 工作區設定 ──"

# kiro-cli 設定（空 MCP，collatro 不需要 MCP server）
mkdir -p ~/.kiro

info "工作區就緒：~/collatro"

# ============================================================
# 完成 — iTerm2 開 3 個 tab，各跑一個 CLI
# ============================================================

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✅ 安裝完成！正在開啟三個 AI 助手…                  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

osascript << 'ASCRIPT'
tell application "iTerm"
    activate
    set newWindow to (create window with default profile)
    tell current session of newWindow
        write text "cd ~/collatro && kiro-cli chat"
    end tell
    tell newWindow
        set tab2 to (create tab with default profile)
        tell current session of tab2
            write text "cd ~/collatro && codex"
        end tell
        set tab3 to (create tab with default profile)
        tell current session of tab3
            write text "cd ~/collatro && gemini"
        end tell
    end tell
end tell
ASCRIPT

info "三個 AI 助手已啟動 🎉"
echo "  每個 tab 會要求登入（開瀏覽器），登入完就能用了。"
echo "  選一個你喜歡的，貼上可疑訊息開始查核。"
echo ""
