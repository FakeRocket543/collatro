#!/bin/bash
# ============================================================
# 🚀 W10 查核管線一鍵安裝
# 版本：2026-04-28
# ============================================================
#
# 安裝項目：
#   1. Homebrew
#   2. 終端機（Ghostty / iTerm2）+ 深色主題
#   3. Node.js
#   4. kiro-cli      — Claude（免費）
#   5. OpenAI Codex  — GPT（免費）
#   6. Gemini CLI    — Gemini（免費）
#   7. Collatro      — 查核管線
#   8. 工作區 + MCP 設定
#
# 用法：
#   curl -fsSL https://172329.xyz/shuj_2026/20260428_install.sh | bash
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
echo "── 2/8 終端機（深色）──"
echo ""
echo "  選一個終端機："
echo "    1) Ghostty   — 超快、GPU 加速、原生 macOS（推薦）"
echo "    2) iTerm2    — 功能最多、最多人用"
echo "    3) 跳過      — 用內建 Terminal.app"
echo ""
read -p "  輸入 1、2 或 3（預設 1）：" TERM_CHOICE < /dev/tty
TERM_CHOICE=${TERM_CHOICE:-1}

TERM_APP=""

case "$TERM_CHOICE" in
    2)
        brew list --cask iterm2 &>/dev/null 2>&1 || brew install --cask iterm2
        TERM_APP="iTerm"
        info "iTerm2 OK"
        ;;
    3)
        TERM_APP=""
        ;;
    *)
        brew list --cask ghostty &>/dev/null 2>&1 || brew install --cask ghostty
        # Ghostty 深色設定
        GHOSTTY_DIR="$HOME/.config/ghostty"
        mkdir -p "$GHOSTTY_DIR"
        if [ ! -f "$GHOSTTY_DIR/config" ] || ! grep -q "課程設定" "$GHOSTTY_DIR/config" 2>/dev/null; then
            cat > "$GHOSTTY_DIR/config" << 'EOF'
# 課程設定
theme = catppuccin-mocha
font-size = 16
window-padding-x = 12
window-padding-y = 12
macos-option-as-alt = true
confirm-close-surface = false
EOF
        fi
        TERM_APP="Ghostty"
        info "Ghostty OK（深色 catppuccin-mocha）"
        ;;
esac

# Terminal.app 也改深色
defaults write com.apple.Terminal "Default Window Settings" -string "Pro" 2>/dev/null
defaults write com.apple.Terminal "Startup Window Settings" -string "Pro" 2>/dev/null
info "Terminal.app 深色 OK"

# ── 3. Node.js ──
echo "── 3/8 Node.js ──"
command -v node &>/dev/null || brew install node
info "Node.js OK ($(node --version))"

# ── 4. kiro-cli ──
echo "── 4/8 kiro-cli（Claude 免費）──"
if ! command -v kiro-cli &>/dev/null; then
    curl -fsSL https://cli.kiro.dev/install | bash 2>/dev/null
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
WORKSPACE="$COLLATRO_DIR"

# MCP 設定
ZHTW_BIN=$(command -v zhtw-mcp 2>/dev/null || echo "$HOME/.local/bin/zhtw-mcp")
PYTHON_BIN=$(command -v python3.13 || command -v python3)

cat > "$WORKSPACE/.mcp.json" << MCPEOF
{
  "mcpServers": {
    "zhtw-mcp": {
      "command": "$ZHTW_BIN",
      "args": []
    }
  }
}
MCPEOF

# kiro-cli 設定
mkdir -p ~/.kiro
cp "$WORKSPACE/.mcp.json" ~/.kiro/mcp.json 2>/dev/null

info "工作區就緒：~/collatro"

# ============================================================
# 完成
# ============================================================

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✅ 全部裝好了！                                     ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║                                                      ║"
echo "║  👉 下一步：                                         ║"
echo "║                                                      ║"
echo "║    cd ~/collatro                                     ║"
echo "║                                                      ║"
echo "║  選一個 AI 助手：                                    ║"
echo "║    kiro-cli chat               ← Claude 免費         ║"
echo "║    codex                       ← GPT 免費            ║"
echo "║    gemini                      ← Gemini 免費         ║"
echo "║                                                      ║"
echo "║  進去後貼上一則你覺得可疑的訊息，AI 會帶你查核。     ║"
echo "║                                                      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# 自動打開終端機
if [ "$TERM_APP" = "Ghostty" ]; then
    open -a Ghostty
elif [ "$TERM_APP" = "iTerm" ]; then
    osascript << ASCRIPT
tell application "iTerm"
    activate
    set newWindow to (create window with default profile)
    tell current session of newWindow
        write text "cd ~/collatro && echo '👉 貼上一則可疑訊息，開始查核'"
    end tell
end tell
ASCRIPT
fi

echo "cd ~/collatro" | pbcopy
info "已複製到剪貼簿：cd ~/collatro"
echo "  👉 重開終端機後貼上（Cmd+V）就能開始"
echo ""
