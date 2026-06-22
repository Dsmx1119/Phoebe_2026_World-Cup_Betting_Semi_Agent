from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass
class Settings:
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("SPORTMIRA_OLLAMA_MODEL", "qwen2.5:7b-instruct")
    enable_web: bool = _env_bool("SPORTMIRA_ENABLE_WEB", True)
    http_timeout: float = _env_float("SPORTMIRA_HTTP_TIMEOUT", 12.0)
    db_path: Path = Path(os.getenv("SPORTMIRA_DB_PATH", ".sportmira/sportmira.sqlite"))
    cache_dir: Path = Path(os.getenv("SPORTMIRA_CACHE_DIR", ".sportmira/cache"))
    default_language: str = os.getenv("SPORTMIRA_DEFAULT_LANGUAGE", "zh")
    risk_mode: str = os.getenv("SPORTMIRA_RISK_MODE", "conservative")
    market_weight: float = _env_float("SPORTMIRA_MARKET_WEIGHT", 0.60)
    form_weight: float = _env_float("SPORTMIRA_FORM_WEIGHT", 0.25)
    news_weight: float = _env_float("SPORTMIRA_NEWS_WEIGHT", 0.15)

    def ensure_dirs(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
