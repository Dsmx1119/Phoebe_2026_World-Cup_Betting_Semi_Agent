from __future__ import annotations

import math
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Iterable, Mapping, Optional, Sequence


TEAM_REPLACEMENTS = {
    "&": " and ",
    "u.s.a.": "usa",
    "united states": "usa",
    "usa": "usa",
    "south korea": "korea republic",
    "korea south": "korea republic",
    "czech republic": "czechia",
}


def normalize_team_name(name: object) -> str:
    if name is None:
        return ""
    text = unicodedata.normalize("NFKD", str(name))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    for old, new in TEAM_REPLACEMENTS.items():
        text = text.replace(old, new)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def fuzzy_team_score(left: object, right: object) -> float:
    left_norm = normalize_team_name(left)
    right_norm = normalize_team_name(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0
    left_tokens = set(left_norm.split())
    right_tokens = set(right_norm.split())
    token_score = len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))
    seq_score = SequenceMatcher(None, left_norm, right_norm).ratio()
    return max(token_score, seq_score)


def match_pair_score(home: object, away: object, candidate_home: object, candidate_away: object) -> float:
    same_order = (fuzzy_team_score(home, candidate_home) + fuzzy_team_score(away, candidate_away)) / 2.0
    swapped_order = (fuzzy_team_score(home, candidate_away) + fuzzy_team_score(away, candidate_home)) / 2.0
    return max(same_order, swapped_order)


def safe_float(value: object) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    try:
        text = str(value).strip().replace("%", "")
        if not text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def parse_handicap_line(value: object) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        parsed = safe_float(value)
        return parsed
    text = str(value).strip()
    match = re.search(r"([+-]?\d+(?:\.(?:0|00|25|5|50|75))?)", text)
    if not match:
        return None
    return safe_float(match.group(1))


def decimal_implied_probability(decimal_odds: object) -> Optional[float]:
    odds = safe_float(decimal_odds)
    if odds is None or odds <= 1.0:
        return None
    return 1.0 / odds


def no_vig_probabilities(decimal_odds: Sequence[object]) -> list[Optional[float]]:
    implied = [decimal_implied_probability(odds) for odds in decimal_odds]
    if any(value is None for value in implied):
        return [None for _ in implied]
    total = sum(value for value in implied if value is not None)
    if total <= 0:
        return [None for _ in implied]
    return [(value / total) if value is not None else None for value in implied]


def expected_value(model_probability: object, decimal_odds: object) -> Optional[float]:
    probability = safe_float(model_probability)
    odds = safe_float(decimal_odds)
    if probability is None or odds is None or probability < 0 or probability > 1 or odds <= 1:
        return None
    return probability * odds - 1.0


def probability_edge(model_probability: object, decimal_odds: object) -> Optional[float]:
    probability = safe_float(model_probability)
    implied = decimal_implied_probability(decimal_odds)
    if probability is None or implied is None:
        return None
    return probability - implied


def asian_handicap_expected_value(
    selection: str,
    home_handicap_line: object,
    decimal_odds: object,
    home_win_probability: object,
    draw_probability: object,
    away_win_probability: object,
) -> Optional[float]:
    """Return net EV for common match-level Asian Handicap lines.

    The line is expressed from the home team's perspective. With only 1X2
    probabilities, exact EV is available for -0.5, -0.25, 0, +0.25 and +0.5.
    Wider handicaps need score-margin probabilities and intentionally return
    None here instead of pretending precision.
    """

    line = parse_handicap_line(home_handicap_line)
    odds = safe_float(decimal_odds)
    home_prob = safe_float(home_win_probability)
    draw_prob = safe_float(draw_probability)
    away_prob = safe_float(away_win_probability)
    if line is None or odds is None or home_prob is None or draw_prob is None or away_prob is None or odds <= 1:
        return None

    selection_norm = selection.lower()
    if selection_norm == "away":
        return asian_handicap_expected_value("home", -line, odds, away_prob, draw_prob, home_prob)
    if selection_norm != "home":
        return None

    rounded_line = round(line, 2)
    win_profit = odds - 1.0
    if rounded_line == -0.5:
        return home_prob * win_profit - (draw_prob + away_prob)
    if rounded_line == -0.25:
        return home_prob * win_profit - 0.5 * draw_prob - away_prob
    if rounded_line == 0.0:
        return home_prob * win_profit - away_prob
    if rounded_line == 0.25:
        return home_prob * win_profit + 0.5 * draw_prob * win_profit - away_prob
    if rounded_line == 0.5:
        return (home_prob + draw_prob) * win_profit - away_prob
    return None


def first_present(row: Mapping[str, object], names: Iterable[str]) -> object:
    lower_to_actual = {key.lower(): key for key in row.keys()}
    for name in names:
        actual = lower_to_actual.get(name.lower())
        if actual is None:
            continue
        value = row.get(actual)
        if value is not None and str(value).lower() != "nan":
            return value
    return None


def round_or_none(value: object, digits: int = 4) -> Optional[float]:
    parsed = safe_float(value)
    if parsed is None:
        return None
    return round(parsed, digits)


def compact_match_summary(row: Mapping[str, object]) -> str:
    home = first_present(row, ["home_team", "home", "match_home"]) or "home"
    away = first_present(row, ["away_team", "away", "match_away"]) or "away"
    parts = [f"{home} vs {away}"]
    home_xg = round_or_none(first_present(row, ["home_xg", "france_recent_xg_average"]))
    away_xg = round_or_none(first_present(row, ["away_xg", "brazil_recent_xg_average"]))
    if home_xg is not None or away_xg is not None:
        parts.append(f"xG {home_xg if home_xg is not None else 'NA'}-{away_xg if away_xg is not None else 'NA'}")
    ah_line = round_or_none(first_present(row, ["asian_handicap_line_float", "asian_handicap_line"]))
    if ah_line is not None:
        parts.append(f"AH {ah_line:+g}")
    home_prob = round_or_none(first_present(row, ["predicted_home_win_prob", "ml_home_win_prob"]))
    draw_prob = round_or_none(first_present(row, ["predicted_draw_prob", "ml_draw_prob"]))
    away_prob = round_or_none(first_present(row, ["predicted_away_win_prob", "ml_away_win_prob"]))
    if home_prob is not None or draw_prob is not None or away_prob is not None:
        parts.append(f"ML 1X2 {home_prob}/{draw_prob}/{away_prob}")
    home_edge = round_or_none(first_present(row, ["home_win_ev", "home_ev"]))
    away_edge = round_or_none(first_present(row, ["away_win_ev", "away_ev"]))
    if home_edge is not None or away_edge is not None:
        parts.append(f"EV home/away {home_edge}/{away_edge}")
    return "; ".join(parts)
