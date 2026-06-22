from __future__ import annotations

from typing import Optional

from sportmira.odds.market_normalizer import normalize_snapshot
from sportmira.odds.market_parser import parse_odds_text
from sportmira.odds.screenshot_ocr import ocr_screenshot


def parse_text_odds(text: str, match_name: Optional[str] = None):
    return normalize_snapshot(parse_odds_text(text, match_name=match_name))


def parse_screenshot_odds(path: str, match_name: Optional[str] = None):
    return ocr_screenshot(path, match_name=match_name, output_json="odds_snapshot.json")
