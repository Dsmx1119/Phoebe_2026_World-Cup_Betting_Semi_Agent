from __future__ import annotations

import re
from typing import Tuple


VS_RE = re.compile(r"\s+(?:vs\.?|v\.?|versus|对|vs|VS)\s+", re.IGNORECASE)


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def slugify(text: str) -> str:
    text = normalize_space(text).lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", text)
    return text.strip("-") or "sportmira"


def parse_match_name(raw_match: str) -> Tuple[str, str]:
    cleaned = normalize_space(raw_match)
    parts = VS_RE.split(cleaned, maxsplit=1)
    if len(parts) == 2 and parts[0] and parts[1]:
        return parts[0].strip(), parts[1].strip()
    return cleaned or "Unknown Team A", "Unknown Team B"
