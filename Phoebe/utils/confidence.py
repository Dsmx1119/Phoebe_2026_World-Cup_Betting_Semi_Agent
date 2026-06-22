from __future__ import annotations

from typing import Iterable


SCORES = {"high": 3, "medium": 2, "low": 1, "none": 0}


def combine_confidence(values: Iterable[str]) -> str:
    vals = [SCORES.get(v, 1) for v in values if v]
    if not vals:
        return "low"
    avg = sum(vals) / float(len(vals))
    if avg >= 2.5:
        return "high"
    if avg >= 1.6:
        return "medium"
    return "low"


def downgrade(confidence: str) -> str:
    if confidence == "high":
        return "medium"
    if confidence == "medium":
        return "low"
    return "low"
