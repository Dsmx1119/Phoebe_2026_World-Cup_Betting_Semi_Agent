from __future__ import annotations

from typing import Iterable, List


def decimal_to_implied_probability(decimal_odds: float) -> float:
    if decimal_odds <= 1.0:
        raise ValueError("Decimal odds must be greater than 1.0")
    return 1.0 / decimal_odds


def american_to_decimal(american_odds: float) -> float:
    if american_odds == 0:
        raise ValueError("American odds cannot be zero")
    if american_odds > 0:
        return 1.0 + american_odds / 100.0
    return 1.0 + 100.0 / abs(american_odds)


def decimal_to_american(decimal_odds: float) -> int:
    if decimal_odds <= 1.0:
        raise ValueError("Decimal odds must be greater than 1.0")
    if decimal_odds >= 2.0:
        return int(round((decimal_odds - 1.0) * 100))
    return int(round(-100.0 / (decimal_odds - 1.0)))


def remove_vig(implied_probabilities: Iterable[float]) -> List[float]:
    probs = list(implied_probabilities)
    if not probs:
        return []
    if any(p <= 0 for p in probs):
        raise ValueError("Implied probabilities must be positive")
    total = sum(probs)
    if total <= 0:
        raise ValueError("Probability total must be positive")
    return [p / total for p in probs]


def expected_value(model_probability: float, decimal_odds: float) -> float:
    if model_probability < 0 or model_probability > 1:
        raise ValueError("Model probability must be between 0 and 1")
    if decimal_odds <= 1.0:
        raise ValueError("Decimal odds must be greater than 1.0")
    return model_probability * decimal_odds - 1.0


def break_even_probability(decimal_odds: float) -> float:
    return decimal_to_implied_probability(decimal_odds)


def normalize_probability(value: float) -> float:
    return max(0.0, min(1.0, value))
