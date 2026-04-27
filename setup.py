#!/usr/bin/env python3
"""collatro setup — 一鍵安裝所有依賴。"""

import subprocess
import sys


def run(cmd, desc):
    print(f"\n{'─'*40}")
    print(f"⏳ {desc}…")
    print(f"   $ {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"   ❌ 失敗！請手動執行上面的指令。")
        return False
    print(f"   ✅ 完成")
    return True


def main():
    print("🔍 Collatro 環境設定")
    print("=" * 40)

    # Check Python
    v = sys.version_info
    if v < (3, 10):
        print(f"❌ Python {v.major}.{v.minor} 太舊，需要 3.10+")
        print("   brew install python@3.12")
        sys.exit(1)
    print(f"✅ Python {v.major}.{v.minor}.{v.micro}")

    # Install deps (no mlx-lm — agent handles LLM tasks)
    run(f"{sys.executable} -m pip install playwright ckip-transformers", "安裝 playwright + ckip-transformers")
    run("playwright install chromium", "安裝 Chromium 瀏覽器引擎")

    # Optional: jieba as lightweight fallback
    run(f"{sys.executable} -m pip install jieba", "安裝 jieba（輕量斷詞 fallback）")

    # Verify
    print(f"\n{'='*40}")
    print("🎉 設定完成！")
    print()
    print("使用方式：在此目錄打開 AI Agent（OpenCode / Kiro CLI），")
    print("貼一段你想查核的內容，agent 會自動引導你完成查核。")


if __name__ == "__main__":
    main()
