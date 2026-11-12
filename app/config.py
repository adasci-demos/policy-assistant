import os
from pathlib import Path

TOP_K = 1

MODEL_NAME = os.environ.get("MODEL_NAME", "")
# Empty means "use the SDK default endpoint".
MODEL_BASE_URL = os.environ.get("MODEL_BASE_URL") or None
# Optional, for local reasoning models (e.g. "none" for qwen3 on Ollama). Empty = not sent.
MODEL_REASONING_EFFORT = os.environ.get("MODEL_REASONING_EFFORT") or None

ROOT = Path(__file__).resolve().parent.parent
POLICY_DIR = ROOT / "data" / "policy"
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "answer_v3.txt"

REFUSAL = "I can't find that in the Harbourline policy."
