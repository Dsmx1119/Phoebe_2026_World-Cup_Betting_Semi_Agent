from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from sportmira.config import Settings


USER_AGENT = "SportMira/0.1 local-first research bot (+no automated betting)"


def cache_key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def robots_allowed(url: str, user_agent: str = USER_AGENT, timeout: float = 5.0) -> bool:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return False
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = RobotFileParser()
    parser.set_url(robots_url)
    try:
        parser.read()
        return parser.can_fetch(user_agent, url)
    except Exception:
        return True


def load_cached(settings: Settings, url: str, max_age_seconds: int = 3600) -> Optional[Dict[str, object]]:
    path = Path(settings.cache_dir) / f"{cache_key(url)}.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if time.time() - float(payload.get("cached_at_epoch", 0)) > max_age_seconds:
        return None
    return payload


def save_cached(settings: Settings, url: str, text: str, status_code: int) -> None:
    path = Path(settings.cache_dir) / f"{cache_key(url)}.json"
    payload = {
        "url": url,
        "status_code": status_code,
        "text": text,
        "cached_at_epoch": time.time(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def fetch_public_url(settings: Settings, url: str) -> Dict[str, object]:
    cached = load_cached(settings, url)
    if cached:
        cached["from_cache"] = True
        return cached
    if not settings.enable_web:
        return {"url": url, "status_code": 0, "text": "", "error": "web disabled", "from_cache": False}
    try:
        import requests  # type: ignore
    except Exception:
        return {"url": url, "status_code": 0, "text": "", "error": "requests not installed", "from_cache": False}
    if not robots_allowed(url):
        return {"url": url, "status_code": 0, "text": "", "error": "robots.txt disallows fetch", "from_cache": False}
    try:
        response = requests.get(url, timeout=settings.http_timeout, headers={"User-Agent": USER_AGENT})
    except Exception as exc:
        return {"url": url, "status_code": 0, "text": "", "error": str(exc), "from_cache": False}
    text = response.text or ""
    save_cached(settings, url, text, response.status_code)
    return {"url": url, "status_code": response.status_code, "text": text, "from_cache": False}
