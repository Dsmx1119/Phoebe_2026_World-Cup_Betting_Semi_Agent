from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Tuple

from sportmira.config import Settings
from sportmira.models.market_prior import one_x_two_prior, total_prior
from sportmira.schemas import ModelOutput, OddsSnapshot, ProbabilityEstimate, SourceResult
from sportmira.utils.time import utc_now_iso


COMMON_TOTAL_LINES = [1.5, 2.0, 2.25, 2.5, 2.75, 3.5]


def poisson_pmf(lam: float, goals: int) -> float:
    return math.exp(-lam) * (lam ** goals) / math.factorial(goals)


def score_distribution(home_lambda: float, away_lambda: float, max_goals: int = 8) -> Dict[Tuple[int, int], float]:
    distribution: Dict[Tuple[int, int], float] = {}
    for home in range(max_goals + 1):
        for away in range(max_goals + 1):
            distribution[(home, away)] = poisson_pmf(home_lambda, home) * poisson_pmf(away_lambda, away)
    total = sum(distribution.values())
    if total > 0:
        distribution = {score: prob / total for score, prob in distribution.items()}
    return distribution


def _form_lambdas(sources: Iterable[SourceResult]) -> Optional[Tuple[float, float]]:
    form_sources = [s for s in sources if s.source_name == "team_form" and s.data.get("teams")]
    if not form_sources:
        return None
    teams = form_sources[0].data.get("teams", [])
    if len(teams) < 2:
        return None
    try:
        home_for = float(teams[0].get("avg_goals_for", 1.25))
        away_for = float(teams[1].get("avg_goals_for", 1.15))
        home_against = float(teams[0].get("avg_goals_against", 1.15))
        away_against = float(teams[1].get("avg_goals_against", 1.25))
    except Exception:
        return None
    home_lambda = max(0.35, min(3.5, (home_for + away_against) / 2.0))
    away_lambda = max(0.35, min(3.5, (away_for + home_against) / 2.0))
    return home_lambda, away_lambda


def estimate_lambdas(
    sources: Iterable[SourceResult],
    odds_snapshot: Optional[OddsSnapshot],
    settings: Settings,
) -> Tuple[float, float, str]:
    baseline_home = 1.25
    baseline_away = 1.15
    basis_parts = ["inference: neutral baseline xG 1.25/1.15"]
    form = _form_lambdas(sources)
    if form:
        baseline_home = baseline_home * (1.0 - settings.form_weight) + form[0] * settings.form_weight
        baseline_away = baseline_away * (1.0 - settings.form_weight) + form[1] * settings.form_weight
        basis_parts.append("fact+inference: blended available team form")
    one_x_two = one_x_two_prior(odds_snapshot)
    if one_x_two:
        edge = one_x_two["home"] - one_x_two["away"]
        baseline_home += 0.60 * settings.market_weight * edge
        baseline_away -= 0.60 * settings.market_weight * edge
        basis_parts.append("fact: 1x2 no-vig market prior")
    totals = total_prior(odds_snapshot, 2.5)
    if totals:
        target_total = 2.10 + 1.10 * totals["over"]
        current_total = baseline_home + baseline_away
        if current_total > 0:
            factor = target_total / current_total
            baseline_home *= factor
            baseline_away *= factor
        basis_parts.append("fact: total goals market prior")
    return max(0.25, baseline_home), max(0.25, baseline_away), "; ".join(basis_parts)


def total_line_probability(distribution: Dict[Tuple[int, int], float], line: float, side: str) -> float:
    # Asian quarter/whole lines are approximated as win probability for the direction.
    if side == "over":
        return sum(prob for (home, away), prob in distribution.items() if home + away > line)
    return sum(prob for (home, away), prob in distribution.items() if home + away < line)


def build_goals_model(
    match_name: str,
    sources: Iterable[SourceResult],
    odds_snapshot: Optional[OddsSnapshot],
    settings: Settings,
) -> ModelOutput:
    home_lambda, away_lambda, basis = estimate_lambdas(sources, odds_snapshot, settings)
    distribution = score_distribution(home_lambda, away_lambda)
    home_win = sum(prob for (home, away), prob in distribution.items() if home > away)
    draw = sum(prob for (home, away), prob in distribution.items() if home == away)
    away_win = sum(prob for (home, away), prob in distribution.items() if home < away)
    confidence = "medium" if odds_snapshot and odds_snapshot.selections else "low"
    estimates: List[ProbabilityEstimate] = [
        ProbabilityEstimate("1x2", "home", home_win, confidence, basis),
        ProbabilityEstimate("1x2", "draw", draw, confidence, basis),
        ProbabilityEstimate("1x2", "away", away_win, confidence, basis),
    ]
    for line in COMMON_TOTAL_LINES:
        estimates.append(
            ProbabilityEstimate("total_goals", "over", total_line_probability(distribution, line, "over"), confidence, basis, line=line)
        )
        estimates.append(
            ProbabilityEstimate("total_goals", "under", total_line_probability(distribution, line, "under"), confidence, basis, line=line)
        )
    likely = sorted(distribution.items(), key=lambda item: item[1], reverse=True)[:8]
    return ModelOutput(
        match=match_name,
        generated_at=utc_now_iso(),
        estimates=estimates,
        likely_scorelines=[
            {"score": f"{home}-{away}", "probability": round(prob, 4)}
            for (home, away), prob in likely
        ],
        notes=[
            f"inference: Poisson lambdas home={home_lambda:.2f}, away={away_lambda:.2f}",
            "quarter/whole total lines are simplified as directional win probabilities for MVP.",
        ],
    )
