"""Application configuration loaded from environment variables."""

import os
from pathlib import Path

# Project root is the parent of this package folder.
BASE_DIR = Path(__file__).resolve().parent.parent


def _bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me")
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "data/brandguard.db")
    if not os.path.isabs(DATABASE_PATH):
        DATABASE_PATH = str(BASE_DIR / DATABASE_PATH)

    MAX_CONTENT_LENGTH = 100_000
    CONTENT_MAX_CHARS = 10_000

    AI_API_KEY = os.environ.get("AI_API_KEY", "").strip()
    AI_API_BASE = os.environ.get("AI_API_BASE", "https://api.openai.com/v1").rstrip("/")
    AI_MODEL = os.environ.get("AI_MODEL", "gpt-4o-mini")
    try:
        AI_TIMEOUT = int(os.environ.get("AI_TIMEOUT", "15"))
    except (ValueError, TypeError):
        AI_TIMEOUT = 15

    ALLOW_RULE_EDITING = _bool(os.environ.get("ALLOW_RULE_EDITING", "false"))
