"""collatro.config — env-driven settings."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
TEMPLATES_DIR = ROOT / "templates"

LLM_URL = os.environ.get("COLLATRO_LLM_URL", "http://localhost:8080/v1/chat/completions")
LLM_MODEL = os.environ.get("COLLATRO_LLM_MODEL", "mistral")
