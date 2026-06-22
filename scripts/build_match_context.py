from __future__ import annotations

import argparse
import json
import logging
import sys
from importlib import import_module
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sportmira.context_strategy import (  # noqa: E402
    asian_handicap_expected_value,
    compact_match_summary,
    expected_value,
    fuzzy_team_score,
    normalize_team_name,
    parse_handicap_line,
    probability_edge,
    round_or_none,
)


LOGGER = logging.getLogger("match_context")
pd = None


def require_pandas() -> None:
    global pd
    if pd is not None:
        return
    try:
        pd = import_module("pandas")
    except ImportError as exc:
        raise RuntimeError("Missing pandas. Install with: python -m pip install -e .") from exc


def configure_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def numeric_mean(series) -> Optional[float]:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return None
    return round(float(values.mean()), 4)


def best_column(frame, names):
    lower_to_actual = {column.lower(): column for column in frame.columns}
    for name in names:
        actual = lower_to_actual.get(name.lower())
        if actual:
            return actual
    return None


def team_recent_rows(frame, team: str, limit: int):
    team_norm = normalize_team_name(team)
    home_col = best_column(frame, ["home_team_norm"])
    away_col = best_column(frame, ["away_team_norm"])
    if home_col is None or away_col is None:
        home_name = best_column(frame, ["home_team", "home", "fd_home_team"])
        away_name = best_column(frame, ["away_team", "away", "fd_away_team"])
        mask = frame.apply(
            lambda row: max(fuzzy_team_score(team_norm, row.get(home_name, "")), fuzzy_team_score(team_norm, row.get(away_name, ""))) >= 0.82,
            axis=1,
        )
    else:
        mask = (frame[home_col] == team_norm) | (frame[away_col] == team_norm)
    rows = frame[mask].copy()
    date_col = best_column(rows, ["match_date", "match_day", "fd_match_date"])
    if date_col:
        rows["_sort_date"] = pd.to_datetime(rows[date_col], errors="coerce")
        rows = rows.sort_values("_sort_date", ascending=False)
    return rows.head(limit)


def side_values_for_team(rows, team: str, home_col: str, away_col: str):
    values = []
    team_norm = normalize_team_name(team)
    for _, row in rows.iterrows():
        is_home = row.get("home_team_norm") == team_norm
        col = home_col if is_home else away_col
        if col in row.index:
            values.append(row[col])
    return pd.Series(values)


def team_recent_summary(frame, team: str, limit: int) -> dict:
    rows = team_recent_rows(frame, team, limit)
    return {
        "matches_used": int(len(rows)),
        "xg_average": numeric_mean(side_values_for_team(rows, team, "home_xg", "away_xg")),
        "shots_average": numeric_mean(side_values_for_team(rows, team, "home_total_shots", "away_total_shots")),
        "attacking_third_pass_success_rate_avg": numeric_mean(
            side_values_for_team(rows, team, "home_attacking_third_pass_success_rate", "away_attacking_third_pass_success_rate")
        ),
        "defensive_interceptions_average": numeric_mean(
            side_values_for_team(rows, team, "home_defensive_interceptions", "away_defensive_interceptions")
        ),
        "cards_average": numeric_mean(
            side_values_for_team(rows, team, "home_yellow_cards", "away_yellow_cards")
            + 2 * side_values_for_team(rows, team, "home_red_cards", "away_red_cards")
        ),
    }


def find_best_match_row(frame, home: str, away: str):
    home_norm = normalize_team_name(home)
    away_norm = normalize_team_name(away)
    scores = []
    for index, row in frame.iterrows():
        row_home = row.get("home_team_norm", normalize_team_name(row.get("home_team", "")))
        row_away = row.get("away_team_norm", normalize_team_name(row.get("away_team", "")))
        same = (fuzzy_team_score(home_norm, row_home) + fuzzy_team_score(away_norm, row_away)) / 2.0
        swapped = (fuzzy_team_score(home_norm, row_away) + fuzzy_team_score(away_norm, row_home)) / 2.0
        scores.append((max(same, swapped), index))
    if not scores:
        return None, 0.0
    score, index = max(scores, key=lambda item: item[0])
    if score < 0.82:
        return None, score
    return frame.loc[index], score


def value_or_row(cli_value, row, names):
    if cli_value is not None:
        return cli_value
    if row is None:
        return None
    for name in names:
        if name in row.index and pd.notna(row[name]):
            return row[name]
    return None


def build_context(args) -> dict:
    require_pandas()
    frame = pd.read_csv(args.features_csv)
    if "home_team_norm" not in frame.columns and "home_team" in frame.columns:
        frame["home_team_norm"] = frame["home_team"].apply(normalize_team_name)
    if "away_team_norm" not in frame.columns and "away_team" in frame.columns:
        frame["away_team_norm"] = frame["away_team"].apply(normalize_team_name)

    best_row, score = find_best_match_row(frame, args.home, args.away)
    home_summary = team_recent_summary(frame, args.home, args.recent_matches)
    away_summary = team_recent_summary(frame, args.away, args.recent_matches)

    ah_line = parse_handicap_line(value_or_row(args.asian_handicap_line, best_row, ["asian_handicap_line_float", "asian_handicap_line"]))
    home_ah_odds = value_or_row(args.home_water, best_row, ["home_ah_odds", "home_water"])
    away_ah_odds = value_or_row(args.away_water, best_row, ["away_ah_odds", "away_water"])
    over_25_odds = value_or_row(args.over_25_odds, best_row, ["b365_close_over_25", "over_2_5_goals_odds"])

    pred_home = value_or_row(args.predicted_home_win_prob, best_row, ["predicted_home_win_prob", "ml_home_win_prob"])
    pred_draw = value_or_row(args.predicted_draw_prob, best_row, ["predicted_draw_prob", "ml_draw_prob"])
    pred_away = value_or_row(args.predicted_away_win_prob, best_row, ["predicted_away_win_prob", "ml_away_win_prob"])
    pred_over = value_or_row(args.predicted_over_25_prob, best_row, ["predicted_over_25_prob", "ml_over_25_prob"])

    context = {
        "match_info": {
            "home": args.home,
            "away": args.away,
            "stage": args.stage,
            "match_date": args.match_date,
        },
        "historical_stats": {
            f"{normalize_team_name(args.home).replace(' ', '_')}_recent_xG_average": home_summary["xg_average"],
            f"{normalize_team_name(args.away).replace(' ', '_')}_recent_xG_average": away_summary["xg_average"],
            "home_recent": home_summary,
            "away_recent": away_summary,
            "referee_cards_per_match_avg": round_or_none(value_or_row(args.referee_cards_per_match_avg, best_row, ["referee_cards_per_match_avg"])),
        },
        "market_odds": {
            "asian_handicap_line": ah_line,
            "home_water_odds": round_or_none(home_ah_odds),
            "away_water_odds": round_or_none(away_ah_odds),
            "over_2_5_goals_odds": round_or_none(over_25_odds),
        },
        "ml_model_prediction": {
            f"predicted_{normalize_team_name(args.home).replace(' ', '_')}_win_prob": round_or_none(pred_home),
            "predicted_draw_prob": round_or_none(pred_draw),
            f"predicted_{normalize_team_name(args.away).replace(' ', '_')}_win_prob": round_or_none(pred_away),
            "predicted_over_2_5_prob": round_or_none(pred_over),
        },
        "engineered_edges": {
            "home_asian_handicap_ev": asian_handicap_expected_value("home", ah_line, home_ah_odds, pred_home, pred_draw, pred_away),
            "away_asian_handicap_ev": asian_handicap_expected_value("away", ah_line, away_ah_odds, pred_home, pred_draw, pred_away),
            "over_2_5_ev": expected_value(pred_over, over_25_odds),
            "home_prob_edge_vs_ah_water": probability_edge(pred_home, home_ah_odds),
            "away_prob_edge_vs_ah_water": probability_edge(pred_away, away_ah_odds),
        },
        "retrieval_metadata": {
            "features_csv": str(args.features_csv),
            "best_historical_match_score": round(score, 4),
            "recent_matches_per_team": args.recent_matches,
            "context_rule": "Only current-match row plus recent-team aggregates are injected; raw CSV rows are not sent to the LLM.",
        },
    }
    if best_row is not None:
        context["retrieved_match_summary"] = compact_match_summary(best_row.to_dict())
    return context


def parse_args():
    parser = argparse.ArgumentParser(description="Build one-match JSON context for LLM/RAG prompt injection.")
    parser.add_argument("--features-csv", required=True, type=Path)
    parser.add_argument("--home", required=True)
    parser.add_argument("--away", required=True)
    parser.add_argument("--stage")
    parser.add_argument("--match-date")
    parser.add_argument("--recent-matches", type=int, default=5)
    parser.add_argument("--asian-handicap-line")
    parser.add_argument("--home-water", type=float)
    parser.add_argument("--away-water", type=float)
    parser.add_argument("--over-25-odds", type=float)
    parser.add_argument("--predicted-home-win-prob", type=float)
    parser.add_argument("--predicted-draw-prob", type=float)
    parser.add_argument("--predicted-away-win-prob", type=float)
    parser.add_argument("--predicted-over-25-prob", type=float)
    parser.add_argument("--referee-cards-per-match-avg", type=float)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)
    try:
        context = build_context(args)
        text = json.dumps(context, ensure_ascii=False, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text + "\n", encoding="utf-8")
            LOGGER.info("Wrote match context to %s", args.output)
        print(text)
        return 0
    except Exception:
        LOGGER.exception("Match context build failed.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
