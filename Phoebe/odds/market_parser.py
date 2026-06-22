from __future__ import annotations

import re
from typing import Iterable, List, Optional, Tuple

from sportmira.odds.odds_math import american_to_decimal
from sportmira.schemas import OddsSelection, OddsSnapshot
from sportmira.utils.time import utc_now_iso
from sportmira.utils.text import normalize_space


MARKET_KEYWORDS = [
    ("1x2", ["胜平负", "1x2", "moneyline", "match winner", "独赢"]),
    ("1x2_2up", ["1x2 (2up)", "2up", "2 up"]),
    ("draw_no_bet", ["平局返还", "draw no bet", "dnb"]),
    ("double_chance", ["双胜彩", "double chance"]),
    ("asian_handicap", ["亚洲盘", "asian handicap", "handicap", "让球"]),
    ("total_goals", ["进球", "total goals", "over under", "over/under", "大小球"]),
    ("total_cards", ["红黄牌总数", "total cards", "cards over under", "牌数"]),
    ("team_cards_1x2", ["红黄牌 1x2", "team cards 1x2", "cards 1x2"]),
    ("red_card", ["有人被罚下场", "red card yes no", "red card", "罚下"]),
    ("corners", ["角球", "corners", "corner"]),
    ("fouls", ["犯规", "fouls", "foul"]),
    ("correct_score", ["correct score", "比分"]),
]

SELECTION_ALIASES = {
    "draw": {"draw", "x", "平", "平局"},
    "home": {"home", "主", "主胜", "1"},
    "away": {"away", "客", "客胜", "2"},
    "over": {"over", "o", "大", "大于"},
    "under": {"under", "u", "小", "小于"},
    "yes": {"yes", "是", "有"},
    "no": {"no", "否", "无"},
}

NUMBER_RE = re.compile(r"(?<![\w.])([+-]?\d+(?:\.\d+)?)(?![\w.])")


def detect_market(text: str) -> Optional[str]:
    lowered = normalize_space(text).lower()
    for market, aliases in MARKET_KEYWORDS:
        if any(alias.lower() in lowered for alias in aliases):
            return market
    return None


def normalize_selection(selection: str, home_team: Optional[str] = None, away_team: Optional[str] = None) -> str:
    raw = normalize_space(selection)
    lowered = raw.lower()
    for normalized, aliases in SELECTION_ALIASES.items():
        if lowered in aliases:
            return normalized
    if home_team and lowered == home_team.lower():
        return "home"
    if away_team and lowered == away_team.lower():
        return "away"
    return raw or "unknown"


def _number_value(raw: str) -> float:
    value = float(raw)
    if (raw.startswith("+") or raw.startswith("-")) and abs(value) >= 100:
        return american_to_decimal(value)
    return value


def _decimal_odds_from_raw(raw: str) -> Optional[float]:
    try:
        value = _number_value(raw)
    except Exception:
        return None
    if value <= 1.0 or value > 100.0:
        return None
    return round(value, 4)


def _strip_market_words(text: str) -> str:
    cleaned = text
    for _, aliases in MARKET_KEYWORDS:
        for alias in aliases:
            cleaned = re.sub(re.escape(alias), " ", cleaned, flags=re.IGNORECASE)
    return normalize_space(cleaned)


def _parse_over_under(line: str, market: str) -> List[OddsSelection]:
    selections: List[OddsSelection] = []
    patterns = [
        (r"(?:over|o|大|大于)\s*([0-9]+(?:\.[0-9]+)?)?\s*([0-9]+(?:\.[0-9]+)?)", "over"),
        (r"(?:under|u|小|小于)\s*([0-9]+(?:\.[0-9]+)?)?\s*([0-9]+(?:\.[0-9]+)?)", "under"),
    ]
    for pattern, selection in patterns:
        for match in re.finditer(pattern, line, flags=re.IGNORECASE):
            line_raw = match.group(1)
            odds_raw = match.group(2)
            odds = _decimal_odds_from_raw(odds_raw)
            if odds is None:
                continue
            line_value = float(line_raw) if line_raw else None
            selections.append(OddsSelection(market=market, selection=selection, odds=odds, line=line_value))
    return selections


def _parse_yes_no(line: str, market: str) -> List[OddsSelection]:
    selections: List[OddsSelection] = []
    for pattern, selection in [
        (r"(?:yes|是|有)\s*([0-9]+(?:\.[0-9]+)?)", "yes"),
        (r"(?:no|否|无)\s*([0-9]+(?:\.[0-9]+)?)", "no"),
    ]:
        for match in re.finditer(pattern, line, flags=re.IGNORECASE):
            odds = _decimal_odds_from_raw(match.group(1))
            if odds is not None:
                selections.append(OddsSelection(market=market, selection=selection, odds=odds))
    return selections


def _parse_labeled_pairs(line: str, market: str, home_team: Optional[str], away_team: Optional[str]) -> List[OddsSelection]:
    selections: List[OddsSelection] = []
    cleaned = _strip_market_words(line)
    matches = list(NUMBER_RE.finditer(cleaned))
    if not matches:
        return selections
    previous_end = 0
    pairs: List[Tuple[str, str]] = []
    for match in matches:
        label = cleaned[previous_end:match.start()].strip(" :-|,，")
        raw = match.group(1)
        previous_end = match.end()
        odds = _decimal_odds_from_raw(raw)
        if odds is not None and label:
            pairs.append((label, raw))
    for label, raw in pairs:
        odds = _decimal_odds_from_raw(raw)
        if odds is None:
            continue
        selection = normalize_selection(label, home_team=home_team, away_team=away_team)
        selections.append(OddsSelection(market=market, selection=selection, odds=odds))
    return selections


def _parse_handicap(line: str, market: str, home_team: Optional[str], away_team: Optional[str]) -> List[OddsSelection]:
    selections: List[OddsSelection] = []
    cleaned = _strip_market_words(line)
    pattern = re.compile(r"(.+?)\s+([+-]\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)")
    for match in pattern.finditer(cleaned):
        label = match.group(1).strip(" :-|,，")
        line_value = float(match.group(2))
        odds = _decimal_odds_from_raw(match.group(3))
        if odds is None:
            continue
        selections.append(
            OddsSelection(
                market=market,
                selection=normalize_selection(label, home_team=home_team, away_team=away_team),
                odds=odds,
                line=line_value,
            )
        )
    return selections


def parse_odds_text(
    text: str,
    match_name: Optional[str] = None,
    home_team: Optional[str] = None,
    away_team: Optional[str] = None,
    source_name: str = "text",
    source_url: str = "user_input",
    ocr_confidence: Optional[float] = None,
) -> OddsSnapshot:
    raw_text = text or ""
    current_market: Optional[str] = None
    selections: List[OddsSelection] = []
    warnings: List[str] = []
    for raw_line in raw_text.splitlines():
        line = normalize_space(raw_line)
        if not line:
            continue
        detected = detect_market(line)
        if detected:
            current_market = detected
        market = detected or current_market
        if not market:
            continue
        parsed: List[OddsSelection] = []
        if market in {"total_goals", "total_cards", "corners", "fouls"}:
            parsed.extend(_parse_over_under(line, market))
        if market == "red_card":
            parsed.extend(_parse_yes_no(line, market))
        if market in {"asian_handicap", "draw_no_bet"}:
            parsed.extend(_parse_handicap(line, market, home_team, away_team))
        if not parsed:
            parsed.extend(_parse_labeled_pairs(line, market, home_team, away_team))
        selections.extend(parsed)
    if not selections:
        warnings.append("未能从文本中识别可用赔率；请确认 OCR 文本或手动输入盘口。")
    return OddsSnapshot(
        match=match_name,
        captured_at=utc_now_iso(),
        source_name=source_name,
        source_url=source_url,
        selections=selections,
        ocr_confidence=ocr_confidence,
        raw_text=raw_text,
        warnings=warnings,
    )


def flatten_market_text(lines: Iterable[str]) -> str:
    return "\n".join(normalize_space(line) for line in lines if normalize_space(line))
