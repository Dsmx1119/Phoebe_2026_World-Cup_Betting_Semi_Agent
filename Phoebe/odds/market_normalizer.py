from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Tuple

from sportmira.odds.odds_math import decimal_to_implied_probability, remove_vig
from sportmira.schemas import OddsSelection, OddsSnapshot


def market_group_key(selection: OddsSelection) -> Tuple[str, object]:
    return selection.market, selection.line if selection.line is not None else "none"


def normalize_snapshot(snapshot: OddsSnapshot) -> OddsSnapshot:
    groups: Dict[Tuple[str, object], List[OddsSelection]] = defaultdict(list)
    for selection in snapshot.selections:
        selection.implied_probability = decimal_to_implied_probability(selection.odds)
        groups[market_group_key(selection)].append(selection)
    for selections in groups.values():
        if len(selections) < 2:
            continue
        no_vig = remove_vig([s.implied_probability or decimal_to_implied_probability(s.odds) for s in selections])
        for selection, prob in zip(selections, no_vig):
            selection.no_vig_probability = prob
    return snapshot


def selections_to_table(selections: Iterable[OddsSelection]) -> List[Dict[str, object]]:
    rows = []
    for s in selections:
        rows.append(
            {
                "market": s.market,
                "selection": s.selection,
                "line": s.line,
                "odds": s.odds,
                "implied_probability": s.implied_probability,
                "no_vig_probability": s.no_vig_probability,
                "notes": s.notes,
            }
        )
    return rows
