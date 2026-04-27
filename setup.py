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
    if v < (3, 11):
        print(f"❌ Python {v.major}.{v.minor} 太舊，需要 3.11+")
        print("   brew install python@3.12")
        sys.exit(1)
    print(f"✅ Python {v.major}.{v.minor}.{v.micro}")

    # Install deps
    run(f"{sys.executable} -m pip install mlx-lm playwright", "安裝 mlx-lm + playwright")
    run("playwright install chromium", "安裝 Chromium 瀏覽器引擎")

    # Pre-download model
    print(f"\n{'─'*40}")
    print("⏳ 下載 LLM 模型（首次約 4.5GB，請耐心等待）…")
    try:
        from mlx_lm import load
        load("mlx-community/Ministral-8B-Instruct-2412-4bit")
        print("   ✅ 模型就緒")
    except ImportError:
        print("   → mlx-lm 未安裝（可能不是 Apple Silicon），LLM 步驟可在 Claude Code 中由 AI 代勞")
    except Exception as e:
        print(f"   ⚠️  模型下載失敗：{e}")
        print("   → 重跑此腳本或手動執行：")
        print('   python3 -c "from mlx_lm import load; load(\'mlx-community/Ministral-8B-Instruct-2412-4bit\')"')

    # Verify
    print(f"\n{'='*40}")
    print("🎉 設定完成！試試看：")
    print('   python3 -m src.run -i')
    print('   python3 -m src.run --theme sky "測試文字"')


if __name__ == "__main__":
    main()
