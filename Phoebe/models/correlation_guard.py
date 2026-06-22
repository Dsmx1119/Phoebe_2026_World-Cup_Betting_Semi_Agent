from __future__ import annotations

from collections import defaultdict
from typing import Iterable, List, Optional, Tuple

from sportmira.schemas import BetRecommendation


def correlation_group(market: str, selection: str, line: Optional[float] = None) -> str:
    selection_lower = selection.lower()
    if market == "total_goals" and selection_lower == "under":
        return "low_score_path"
    if market == "1x2" and selection_lower == "draw":
        return "low_score_path"
    if market == "correct_score":
        return "scoreline_path"
    if market == "total_goals" and selection_lower == "over":
        return "open_game_path"
    if market == "red_card" and selection_lower == "yes":
        return "chaos_cards_path"
    if market in {"total_cards", "team_cards_1x2"}:
        return "cards_path"
    if market in {"corners", "fouls"}:
        return f"{market}_path"
    return f"{market}_{selection_lower}"


def filter_correlated(
    recommendations: Iterable[BetRecommendation],
    max_bets: int,
    risk_mode: str = "conservative",
) -> Tuple[List[BetRecommendation], List[str]]:
    warnings: List[str] = []
    max_per_group = 2 if risk_mode == "aggressive" else 1
    selected: List[BetRecommendation] = []
    group_counts = defaultdict(int)
    one_x_two_selected = False
    for rec in sorted(recommendations, key=lambda item: item.edge, reverse=True):
        if risk_mode != "aggressive" and rec.market == "1x2":
            if one_x_two_selected:
                warnings.append(f"互斥保护：跳过 {rec.bet}，同一场 1X2 默认只保留一个方向。")
                continue
            one_x_two_selected = True
        group = rec.correlation_group or correlation_group(rec.market, rec.selection)
        if group_counts[group] >= max_per_group:
            warnings.append(f"相关性保护：跳过 {rec.bet}，避免过度集中在 {group}。")
            continue
        selected.append(rec)
        group_counts[group] += 1
        if len(selected) >= max_bets:
            break
    if len(group_counts) == 1 and len(selected) > 1 and risk_mode != "aggressive":
        warnings.append("投注路径过于集中，默认保守模式已限制同一路径敞口。")
    return selected, warnings
