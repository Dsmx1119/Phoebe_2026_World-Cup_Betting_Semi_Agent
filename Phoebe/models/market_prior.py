from __future__ import annotations

from typing import Dict, Optional

from sportmira.schemas import OddsSnapshot


def _selection_key(selection: str) -> str:
    value = selection.strip().lower()
    if value in {"home", "1", "主胜", "主"}:
        return "home"
    if value in {"draw", "x", "平", "平局"}:
        return "draw"
    if value in {"away", "2", "客胜", "客"}:
        return "away"
    if value in {"over", "o", "大"}:
        return "over"
    if value in {"under", "u", "小"}:
        return "under"
    if value in {"yes", "是", "有"}:
        return "yes"
    if value in {"no", "否", "无"}:
        return "no"
    return value


def one_x_two_prior(snapshot: Optional[OddsSnapshot]) -> Dict[str, float]:
    if not snapshot:
        return {}
    priors: Dict[str, float] = {}
    for selection in snapshot.selections:
        if selection.market != "1x2":
            continue
        key = _selection_key(selection.selection)
        if key in {"home", "draw", "away"}:
            priors[key] = selection.no_vig_probability or selection.implied_probability or 0.0
    if {"home", "draw", "away"}.issubset(priors):
        return priors
    return {}


def total_prior(snapshot: Optional[OddsSnapshot], line: float = 2.5) -> Dict[str, float]:
    if not snapshot:
        return {}
    priors: Dict[str, float] = {}
    candidates = [s for s in snapshot.selections if s.market == "total_goals" and s.line == line]
    for selection in candidates:
        key = _selection_key(selection.selection)
        if key in {"over", "under"}:
            priors[key] = selection.no_vig_probability or selection.implied_probability or 0.0
    if {"over", "under"}.issubset(priors):
        return priors
    return {}


def red_card_prior(snapshot: Optional[OddsSnapshot]) -> Dict[str, float]:
    if not snapshot:
        return {}
    priors: Dict[str, float] = {}
    for selection in snapshot.selections:
        if selection.market != "red_card":
            continue
        key = _selection_key(selection.selection)
        if key in {"yes", "no"}:
            priors[key] = selection.no_vig_probability or selection.implied_probability or 0.0
    if {"yes", "no"}.issubset(priors):
        return priors
    return {}
