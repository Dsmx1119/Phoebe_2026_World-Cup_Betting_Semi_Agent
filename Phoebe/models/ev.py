from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from sportmira.models.correlation_guard import correlation_group, filter_correlated
from sportmira.models.staking import allocate_stakes
from sportmira.odds.odds_math import break_even_probability, expected_value
from sportmira.schemas import BetRecommendation, BettingCard, ModelOutput, OddsSelection, OddsSnapshot, ProbabilityEstimate


def _key(market: str, selection: str, line: Optional[float]) -> Tuple[str, str, Optional[float]]:
    return market, selection.lower(), line


def _estimate_lookup(model_output: Optional[ModelOutput]) -> Dict[Tuple[str, str, Optional[float]], ProbabilityEstimate]:
    lookup: Dict[Tuple[str, str, Optional[float]], ProbabilityEstimate] = {}
    if not model_output:
        return lookup
    for estimate in model_output.estimates:
        lookup[_key(estimate.market, estimate.selection, estimate.line)] = estimate
    return lookup


def _find_estimate(
    lookup: Dict[Tuple[str, str, Optional[float]], ProbabilityEstimate],
    selection: OddsSelection,
) -> Optional[ProbabilityEstimate]:
    direct = lookup.get(_key(selection.market, selection.selection, selection.line))
    if direct:
        return direct
    if selection.line is not None:
        same_side = [
            est
            for key, est in lookup.items()
            if key[0] == selection.market and key[1] == selection.selection.lower() and key[2] is not None
        ]
        if same_side:
            return sorted(same_side, key=lambda est: abs((est.line or 0.0) - (selection.line or 0.0)))[0]
    return lookup.get(_key(selection.market, selection.selection, None))


def _minimum_edge(selection: OddsSelection, estimate: ProbabilityEstimate) -> float:
    if selection.market == "total_cards":
        return 0.06 if estimate.confidence == "low" else 0.035
    return 0.015


def build_betting_card(
    match_name: str,
    odds_snapshot: Optional[OddsSnapshot],
    model_output: Optional[ModelOutput],
    bankroll: float,
    unit: str = "u",
    max_bets: int = 3,
    risk_mode: str = "conservative",
) -> BettingCard:
    card = BettingCard(match_name, bankroll, unit, max_bets, risk_mode)
    if not odds_snapshot or not odds_snapshot.selections:
        card.no_bet = True
        card.warnings.append("没有可用赔率，SportMira 不会推荐无赔率市场。")
        return card
    lookup = _estimate_lookup(model_output)
    candidates: List[BetRecommendation] = []
    for selection in odds_snapshot.selections:
        estimate = _find_estimate(lookup, selection)
        implied = selection.implied_probability or break_even_probability(selection.odds)
        if not estimate:
            card.rejected.append(
                {
                    "market": selection.market,
                    "selection": selection.selection,
                    "odds": selection.odds,
                    "reason": "MVP 模型暂未覆盖该市场，不能只凭赔率推荐。",
                }
            )
            continue
        edge = expected_value(estimate.probability, selection.odds)
        min_edge = _minimum_edge(selection, estimate)
        if edge < min_edge:
            card.rejected.append(
                {
                    "market": selection.market,
                    "selection": selection.selection,
                    "odds": selection.odds,
                    "model_probability": round(estimate.probability, 4),
                    "reason": f"EV 不足或没有价格优势；该市场最低要求 {min_edge:.1%} EV。",
                }
            )
            continue
        candidates.append(
            BetRecommendation(
                bet=f"{selection.market} {selection.selection}{' ' + str(selection.line) if selection.line is not None else ''}",
                market=selection.market,
                selection=selection.selection,
                odds=selection.odds,
                model_probability=estimate.probability,
                implied_probability=implied,
                edge=edge,
                stake=0.0,
                unit=unit,
                confidence=estimate.confidence,
                reason=f"{estimate.basis}; EV={edge:.2%}",
                main_risk="样本/阵容/赔率变化可能使当前价格优势失效。",
                correlation_group=correlation_group(selection.market, selection.selection, selection.line),
            )
        )
    filtered, warnings = filter_correlated(candidates, max_bets=max_bets, risk_mode=risk_mode)
    card.warnings.extend(warnings)
    card.recommendations = allocate_stakes(filtered, bankroll=bankroll, unit=unit, max_bets=max_bets, risk_mode=risk_mode)
    if not card.recommendations:
        card.no_bet = True
        card.warnings.append("未发现满足 EV、置信度和相关性约束的投注，建议 no bet。")
    return card
