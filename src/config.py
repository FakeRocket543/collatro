"""collatro.config — env-driven settings."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
TEMPLATES_DIR = ROOT / "templates"

# LLM (Tier 3 fallback: external server)
LLM_URL = os.environ.get("COLLATRO_LLM_URL", "http://localhost:8080/v1/chat/completions")
LLM_MODEL = os.environ.get("COLLATRO_LLM_MODEL", "mistral")

# Tier 1: mlx-lm model ID (auto-downloaded from HuggingFace)
# COLLATRO_MLX_MODEL=mlx-community/Ministral-8B-Instruct-2412-4bit

# Tier 2: llama-server subprocess (path to .gguf file)
# COLLATRO_GGUF=/path/to/Ministral-3-3B-Instruct-2512-Q8_0.gguf

# Search engine (Searxng preferred, DuckDuckGo fallback)
# COLLATRO_SEARXNG_URL=http://localhost:8888
