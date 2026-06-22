from __future__ import annotations

import math
from typing import Iterable, List, Optional

from sportmira.models.market_prior import one_x_two_prior, red_card_prior
from sportmira.schemas import ModelOutput, OddsSnapshot, ProbabilityEstimate, SourceResult


CARD_TOTAL_LINES = [2.5, 3.5, 4.5, 5.5]


def _poisson_over(lam: float, line: float) -> float:
    cutoff = int(math.floor(line))
    cumulative = sum(math.exp(-lam) * (lam ** k) / math.factorial(k) for k in range(cutoff + 1))
    return max(0.0, min(1.0, 1.0 - cumulative))


def _match_state_card_modifier(odds_snapshot: Optional[OddsSnapshot]) -> tuple[float, str]:
    """Small downgrade for card overs when 1x2 implies a likely non-competitive path."""
    priors = one_x_two_prior(odds_snapshot)
    if not priors:
        return 1.0, ""
    favorite_prob = max(priors.values())
    if favorite_prob >= 0.88:
        return 0.86, "inference: strong-favorite/blowout path can suppress late tactical fouls"
    if favorite_prob >= 0.78:
        return 0.93, "inference: clear-favorite path slightly lowers sustained card pressure"
    return 1.0, ""


def build_cards_estimates(sources: Iterable[SourceResult], odds_snapshot: Optional[OddsSnapshot]) -> List[ProbabilityEstimate]:
    ref_sources = [s for s in sources if s.source_name == "referee_profile"]
    lam = 4.2
    basis = "inference: baseline international card environment"
    confidence = "low"
    if ref_sources and ref_sources[0].data.get("yellow_cards_per_match"):
        try:
            lam = float(ref_sources[0].data["yellow_cards_per_match"])
            basis = "fact+inference: referee card tendency blended into baseline"
            confidence = "medium"
        except Exception:
            pass
    modifier, modifier_basis = _match_state_card_modifier(odds_snapshot)
    if modifier_basis:
        lam *= modifier
        basis = f"{basis}; {modifier_basis}"
        if confidence == "medium":
            confidence = "low"
    estimates: List[ProbabilityEstimate] = []
    for line in CARD_TOTAL_LINES:
        over = _poisson_over(lam, line)
        estimates.append(ProbabilityEstimate("total_cards", "over", over, confidence, basis, line=line))
        estimates.append(ProbabilityEstimate("total_cards", "under", 1.0 - over, confidence, basis, line=line))
    red_prior = red_card_prior(odds_snapshot)
    if red_prior:
        yes = red_prior["yes"] * 0.70 + 0.16 * 0.30
        confidence = "medium"
        basis = "fact+inference: red card market prior blended with baseline"
    else:
        yes = 0.16
    estimates.append(ProbabilityEstimate("red_card", "yes", yes, confidence, basis))
    estimates.append(ProbabilityEstimate("red_card", "no", 1.0 - yes, confidence, basis))
    estimates.append(
        ProbabilityEstimate(
            "team_cards_1x2",
            "draw",
            0.30,
            "low",
            "inference: no reliable team-card split available in MVP",
        )
    )
    return estimates
