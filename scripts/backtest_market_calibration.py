from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sportmira.config import Settings
from sportmira.models.market_calibrator import (
    OUTCOMES,
    blend_probabilities,
    fit_market_calibration,
    no_vig_probabilities,
)
from sportmira.models.poisson_goals import build_goals_model
from sportmira.odds.market_normalizer import normalize_snapshot
from sportmira.schemas import OddsSelection, OddsSnapshot
from sportmira.utils.time import utc_now_iso


@dataclass
class MatchRow:
    date: str
    home: str
    away: str
    score: str
    odds: List[float]
    result: str
    source_file: str

    @property
    def match_name(self) -> str:
        return f"{self.home} vs {self.away}"


def _clean_html(value: str) -> str:
    return html.unescape(re.sub("<.*?>", "", value)).strip()


def parse_betexplorer_results(paths: Sequence[Path]) -> List[MatchRow]:
    rows: List[MatchRow] = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for tr in re.findall(r"<tr>(.*?)</tr>", text, flags=re.S):
            if 'class="in-match"' not in tr or "table-main__odds" not in tr:
                continue
            teams = re.search(r'class="in-match"[^>]*><span>(.*?)</span> - <span>(.*?)</span></a>', tr, re.S)
            score = re.search(r'<td class="h-text-center"><a[^>]*>(.*?)</a></td>', tr, re.S)
            date = re.search(r'<td class="h-text-right h-text-no-wrap">([^<]+)</td>', tr)
            odd_tds = re.findall(r'<td class="table-main__odds([^"<>]*)"([^>]*)>(.*?)</td>', tr, re.S)
            if not (teams and score and date and len(odd_tds) >= 3):
                continue
            odds: List[Optional[float]] = []
            colored: List[bool] = []
            for css_class, attrs, inner in odd_tds[:3]:
                match = re.search(r'data-odd="([0-9.]+)"', attrs) or re.search(r'data-odd="([0-9.]+)"', inner)
                odds.append(float(match.group(1)) if match else None)
                colored.append("colored" in css_class)
            if any(odd is None for odd in odds) or True not in colored:
                continue
            rows.append(
                MatchRow(
                    date=date.group(1),
                    home=_clean_html(teams.group(1)),
                    away=_clean_html(teams.group(2)),
                    score=_clean_html(score.group(1)),
                    odds=[float(odds[0]), float(odds[1]), float(odds[2])],
                    result=OUTCOMES[colored.index(True)],
                    source_file=str(path),
                )
            )
    return sorted(rows, key=lambda row: datetime.strptime(row.date, "%d.%m.%Y"))


def sportmira_model_probabilities(row: MatchRow, settings: Settings) -> List[float]:
    snapshot = normalize_snapshot(
        OddsSnapshot(
            match=row.match_name,
            captured_at=utc_now_iso(),
            source_name="BetExplorer",
            source_url=row.source_file,
            selections=[
                OddsSelection("1x2", "home", row.odds[0], source="BetExplorer"),
                OddsSelection("1x2", "draw", row.odds[1], source="BetExplorer"),
                OddsSelection("1x2", "away", row.odds[2], source="BetExplorer"),
            ],
        )
    )
    model = build_goals_model(row.match_name, [], snapshot, settings)
    by_outcome = {estimate.selection: estimate.probability for estimate in model.estimates if estimate.market == "1x2"}
    total = sum(by_outcome[outcome] for outcome in OUTCOMES)
    return [by_outcome[outcome] / total for outcome in OUTCOMES]


def make_samples(rows: Iterable[MatchRow], settings: Settings) -> List[dict]:
    samples = []
    for row in rows:
        samples.append(
            {
                "match": row.match_name,
                "result": row.result,
                "odds": row.odds,
                "model_probabilities": sportmira_model_probabilities(row, settings),
                "market_probabilities": no_vig_probabilities(row.odds),
            }
        )
    return samples


def backtest(
    rows: Sequence[MatchRow],
    samples: Sequence[dict],
    market_alpha: float,
    ev_threshold: float,
    max_odds: float,
    initial_bankroll: float,
    stake_fraction: float,
) -> dict:
    bankroll = initial_bankroll
    bets = []
    for row, sample in zip(rows, samples):
        probabilities = blend_probabilities(
            sample["model_probabilities"],
            sample["market_probabilities"],
            market_alpha,
        )
        candidates = []
        for index, outcome in enumerate(OUTCOMES):
            odds = row.odds[index]
            edge = probabilities[index] * odds - 1.0
            if edge >= ev_threshold and odds <= max_odds:
                candidates.append((edge, probabilities[index], outcome, odds))
        if not candidates:
            continue
        edge, probability, outcome, odds = max(candidates, key=lambda item: (item[0], item[1]))
        stake = round(min(bankroll * 0.05, max(bankroll * stake_fraction, bankroll * min(0.05, edge * 0.04))), 2)
        pnl = stake * (odds - 1.0) if outcome == row.result else -stake
        bankroll = round(bankroll + pnl, 2)
        bets.append(
            {
                "date": row.date,
                "match": row.match_name,
                "score": row.score,
                "selection": outcome,
                "result": row.result,
                "odds": odds,
                "probability": round(probability, 4),
                "edge": round(edge, 4),
                "stake": stake,
                "pnl": round(pnl, 2),
                "bankroll_after": bankroll,
            }
        )
    wins = sum(1 for bet in bets if bet["pnl"] > 0)
    return {
        "initial_bankroll": initial_bankroll,
        "final_bankroll": bankroll,
        "profit": round(bankroll - initial_bankroll, 2),
        "matches": len(rows),
        "bets": len(bets),
        "wins": wins,
        "losses": len(bets) - wins,
        "hit_rate": round(wins / len(bets), 4) if bets else None,
        "total_staked": round(sum(bet["stake"] for bet in bets), 2),
        "avg_odds": round(sum(bet["odds"] for bet in bets) / len(bets), 2) if bets else 0.0,
        "market_alpha": market_alpha,
        "ev_threshold": ev_threshold,
        "max_odds": max_odds,
        "stake_fraction": stake_fraction,
        "top_wins": sorted((bet for bet in bets if bet["pnl"] > 0), key=lambda bet: bet["pnl"], reverse=True)[:8],
        "worst_losses": sorted((bet for bet in bets if bet["pnl"] < 0), key=lambda bet: bet["pnl"])[:8],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest SportMira 1X2 market calibration on BetExplorer HTML snapshots.")
    parser.add_argument("--train-html", nargs="+", required=True, type=Path)
    parser.add_argument("--test-html", nargs="+", required=True, type=Path)
    parser.add_argument("--initial-bankroll", type=float, default=1000.0)
    parser.add_argument("--ev-threshold", type=float, default=0.05)
    parser.add_argument("--max-odds", type=float, default=6.0)
    parser.add_argument("--stake-fraction", type=float, default=0.03)
    args = parser.parse_args()

    settings = Settings()
    train_rows = parse_betexplorer_results(args.train_html)
    test_rows = parse_betexplorer_results(args.test_html)
    train_samples = make_samples(train_rows, settings)
    test_samples = make_samples(test_rows, settings)
    fit = fit_market_calibration(train_samples)
    result = {
        "fit": fit.__dict__,
        "test": backtest(
            test_rows,
            test_samples,
            fit.market_alpha,
            args.ev_threshold,
            args.max_odds,
            args.initial_bankroll,
            args.stake_fraction,
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
