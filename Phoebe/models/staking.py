from __future__ import annotations

from typing import Iterable, List

from sportmira.schemas import BetRecommendation


RISK_LIMITS = {
    "conservative": {"single": 0.12, "total": 0.35, "base": 0.04},
    "balanced": {"single": 0.18, "total": 0.45, "base": 0.06},
    "aggressive": {"single": 0.30, "total": 0.65, "base": 0.09},
}


def soft_kelly_fraction(probability: float, decimal_odds: float, softness: float = 0.25) -> float:
    b = decimal_odds - 1.0
    if b <= 0:
        return 0.0
    q = 1.0 - probability
    full = (b * probability - q) / b
    return max(0.0, full * softness)


def allocate_stakes(
    recommendations: Iterable[BetRecommendation],
    bankroll: float,
    unit: str = "u",
    max_bets: int = 3,
    risk_mode: str = "conservative",
) -> List[BetRecommendation]:
    limits = RISK_LIMITS.get(risk_mode, RISK_LIMITS["conservative"])
    ranked = sorted(recommendations, key=lambda rec: (rec.edge, rec.model_probability), reverse=True)[:max_bets]
    if bankroll <= 0:
        for rec in ranked:
            rec.stake = 0.0
        return ranked
    single_cap = bankroll * limits["single"]
    total_cap = bankroll * limits["total"]
    base = bankroll * limits["base"]
    allocated = 0.0
    for rec in ranked:
        confidence_mult = {"high": 1.25, "medium": 1.0, "low": 0.65}.get(rec.confidence, 0.65)
        kelly = soft_kelly_fraction(rec.model_probability, rec.odds)
        suggested = max(base * confidence_mult, bankroll * min(kelly, limits["base"] * 1.5))
        stake = min(single_cap, suggested, max(0.0, total_cap - allocated))
        rec.stake = round(stake, 2)
        allocated += rec.stake
    return [rec for rec in ranked if rec.stake > 0]
