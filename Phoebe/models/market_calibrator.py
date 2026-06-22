from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Mapping, Sequence


OUTCOMES = ("home", "draw", "away")


def normalize_probabilities(values: Sequence[float]) -> List[float]:
    clipped = [max(1e-9, float(value)) for value in values]
    total = sum(clipped)
    if total <= 0:
        return [1.0 / len(clipped)] * len(clipped)
    return [value / total for value in clipped]


def no_vig_probabilities(decimal_odds: Sequence[float]) -> List[float]:
    implied = [1.0 / float(odds) for odds in decimal_odds]
    return normalize_probabilities(implied)


def blend_probabilities(
    model_probabilities: Sequence[float],
    market_probabilities: Sequence[float],
    market_alpha: float,
) -> List[float]:
    alpha = min(1.0, max(0.0, market_alpha))
    blended = [
        alpha * market + (1.0 - alpha) * model
        for model, market in zip(model_probabilities, market_probabilities)
    ]
    return normalize_probabilities(blended)


def multiclass_log_loss(samples: Iterable[Mapping[str, object]], market_alpha: float) -> float:
    total = 0.0
    count = 0
    outcome_to_index = {outcome: index for index, outcome in enumerate(OUTCOMES)}
    for sample in samples:
        result = str(sample["result"]).lower()
        index = outcome_to_index[result]
        probs = blend_probabilities(
            sample["model_probabilities"],  # type: ignore[arg-type]
            sample["market_probabilities"],  # type: ignore[arg-type]
            market_alpha,
        )
        total -= math.log(max(1e-12, probs[index]))
        count += 1
    if count == 0:
        return 0.0
    return total / count


@dataclass(frozen=True)
class CalibrationFit:
    market_alpha: float
    train_log_loss: float
    model_log_loss: float
    market_log_loss: float
    sample_size: int


def fit_market_calibration(samples: Sequence[Mapping[str, object]], grid_steps: int = 100) -> CalibrationFit:
    if not samples:
        return CalibrationFit(1.0, 0.0, 0.0, 0.0, 0)

    candidates = [step / grid_steps for step in range(grid_steps + 1)]
    best_alpha = min(candidates, key=lambda alpha: multiclass_log_loss(samples, alpha))
    return CalibrationFit(
        market_alpha=best_alpha,
        train_log_loss=multiclass_log_loss(samples, best_alpha),
        model_log_loss=multiclass_log_loss(samples, 0.0),
        market_log_loss=multiclass_log_loss(samples, 1.0),
        sample_size=len(samples),
    )
