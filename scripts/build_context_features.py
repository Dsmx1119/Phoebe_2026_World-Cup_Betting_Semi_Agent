from __future__ import annotations

import argparse
import json
import logging
import sys
from importlib import import_module
from pathlib import Path
from typing import Optional, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sportmira.context_strategy import (  # noqa: E402
    asian_handicap_expected_value,
    compact_match_summary,
    decimal_implied_probability,
    expected_value,
    first_present,
    no_vig_probabilities,
    normalize_team_name,
    parse_handicap_line,
    probability_edge,
    round_or_none,
)


LOGGER = logging.getLogger("context_features")
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


def read_csv(path: Path):
    require_pandas()
    LOGGER.info("Reading %s", path)
    return pd.read_csv(path)


def first_existing_column(frame, names: Sequence[str]) -> Optional[str]:
    lower_to_actual = {column.lower(): column for column in frame.columns}
    for name in names:
        actual = lower_to_actual.get(name.lower())
        if actual:
            return actual
    return None


def add_normalized_team_keys(frame):
    for column, output in [
        (first_existing_column(frame, ["home_team", "home", "fd_home_team"]), "home_team_norm"),
        (first_existing_column(frame, ["away_team", "away", "fd_away_team"]), "away_team_norm"),
    ]:
        if column:
            frame[output] = frame[column].apply(normalize_team_name)
    return frame


def merge_predictions(features, predictions):
    if predictions is None or predictions.empty:
        return features

    predictions = add_normalized_team_keys(predictions.copy())
    if "match_date" in features.columns:
        features["merge_match_day"] = pd.to_datetime(features["match_date"], errors="coerce").dt.date
    elif "match_day" in features.columns:
        features["merge_match_day"] = pd.to_datetime(features["match_day"], errors="coerce").dt.date
    else:
        features["merge_match_day"] = None

    prediction_date_col = first_existing_column(predictions, ["match_date", "match_day", "date"])
    if prediction_date_col:
        predictions["merge_match_day"] = pd.to_datetime(predictions[prediction_date_col], errors="coerce").dt.date
        keys = ["merge_match_day", "home_team_norm", "away_team_norm"]
    else:
        keys = ["home_team_norm", "away_team_norm"]

    prediction_cols = [
        column
        for column in predictions.columns
        if column in keys
        or column
        in {
            "predicted_home_win_prob",
            "predicted_draw_prob",
            "predicted_away_win_prob",
            "predicted_over_25_prob",
            "predicted_under_25_prob",
            "model_version",
        }
    ]
    merged = features.merge(predictions[prediction_cols], on=keys, how="left", suffixes=("", "_prediction"))
    LOGGER.info("Merged predictions on keys=%s", keys)
    return merged


def coalesce_columns(frame, target: str, candidates: Sequence[str]):
    if target in frame.columns:
        return frame
    column = first_existing_column(frame, candidates)
    if column:
        frame[target] = frame[column]
    return frame


def engineer_features(frame):
    frame = add_normalized_team_keys(frame.copy())
    mappings = {
        "asian_handicap_line": ["asian_handicap_line", "handicap_line", "ah_line", "AHh", "BbAHh"],
        "home_ah_odds": ["home_ah_odds", "home_water", "AHH", "BbAHH", "B365AHH"],
        "away_ah_odds": ["away_ah_odds", "away_water", "AHA", "BbAHA", "B365AHA"],
        "b365_close_home": ["b365_close_home", "B365CH", "B365H"],
        "b365_close_draw": ["b365_close_draw", "B365CD", "B365D"],
        "b365_close_away": ["b365_close_away", "B365CA", "B365A"],
        "b365_close_over_25": ["b365_close_over_25", "B365C>2.5", "B365>2.5"],
        "b365_close_under_25": ["b365_close_under_25", "B365C<2.5", "B365<2.5"],
        "predicted_home_win_prob": ["predicted_home_win_prob", "ml_home_win_prob", "home_win_prob"],
        "predicted_draw_prob": ["predicted_draw_prob", "ml_draw_prob", "draw_prob"],
        "predicted_away_win_prob": ["predicted_away_win_prob", "ml_away_win_prob", "away_win_prob"],
        "predicted_over_25_prob": ["predicted_over_25_prob", "ml_over_25_prob", "over_25_prob"],
    }
    for target, candidates in mappings.items():
        frame = coalesce_columns(frame, target, candidates)

    if "asian_handicap_line" in frame.columns:
        frame["asian_handicap_line_float"] = frame["asian_handicap_line"].apply(parse_handicap_line)
    else:
        frame["asian_handicap_line_float"] = None

    for column in ["home_ah_odds", "away_ah_odds", "b365_close_home", "b365_close_draw", "b365_close_away", "b365_close_over_25", "b365_close_under_25"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame["home_ah_implied_prob"] = frame.get("home_ah_odds", pd.Series([None] * len(frame))).apply(decimal_implied_probability)
    frame["away_ah_implied_prob"] = frame.get("away_ah_odds", pd.Series([None] * len(frame))).apply(decimal_implied_probability)
    no_vig_pairs = frame.apply(lambda row: no_vig_probabilities([row.get("home_ah_odds"), row.get("away_ah_odds")]), axis=1)
    frame["home_ah_no_vig_prob"] = no_vig_pairs.apply(lambda values: values[0] if values else None)
    frame["away_ah_no_vig_prob"] = no_vig_pairs.apply(lambda values: values[1] if len(values) > 1 else None)
    frame["home_ah_ev"] = frame.apply(
        lambda row: asian_handicap_expected_value(
            "home",
            row.get("asian_handicap_line_float"),
            row.get("home_ah_odds"),
            row.get("predicted_home_win_prob"),
            row.get("predicted_draw_prob"),
            row.get("predicted_away_win_prob"),
        ),
        axis=1,
    )
    frame["away_ah_ev"] = frame.apply(
        lambda row: asian_handicap_expected_value(
            "away",
            row.get("asian_handicap_line_float"),
            row.get("away_ah_odds"),
            row.get("predicted_home_win_prob"),
            row.get("predicted_draw_prob"),
            row.get("predicted_away_win_prob"),
        ),
        axis=1,
    )

    ev_specs = [
        ("home_win", "predicted_home_win_prob", "b365_close_home"),
        ("draw", "predicted_draw_prob", "b365_close_draw"),
        ("away_win", "predicted_away_win_prob", "b365_close_away"),
        ("over_25", "predicted_over_25_prob", "b365_close_over_25"),
    ]
    if "predicted_under_25_prob" not in frame.columns and "predicted_over_25_prob" in frame.columns:
        frame["predicted_under_25_prob"] = 1.0 - pd.to_numeric(frame["predicted_over_25_prob"], errors="coerce")
    ev_specs.append(("under_25", "predicted_under_25_prob", "b365_close_under_25"))
    for prefix, probability_col, odds_col in ev_specs:
        if probability_col not in frame.columns or odds_col not in frame.columns:
            frame[f"{prefix}_ev"] = None
            frame[f"{prefix}_prob_edge"] = None
            continue
        frame[f"{prefix}_ev"] = frame.apply(lambda row: expected_value(row.get(probability_col), row.get(odds_col)), axis=1)
        frame[f"{prefix}_prob_edge"] = frame.apply(lambda row: probability_edge(row.get(probability_col), row.get(odds_col)), axis=1)

    frame["llm_context_summary"] = frame.apply(lambda row: compact_match_summary(row.to_dict()), axis=1)
    return frame


def write_jsonl(frame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for _, row in frame.iterrows():
            payload = {
                "match": {
                    "home": first_present(row.to_dict(), ["home_team", "home", "fd_home_team"]),
                    "away": first_present(row.to_dict(), ["away_team", "away", "fd_away_team"]),
                    "date": str(first_present(row.to_dict(), ["match_date", "match_day", "fd_match_date"])),
                },
                "features": {key: round_or_none(row.get(key)) for key in frame.columns if key.endswith(("_ev", "_prob_edge", "_prob", "_float"))},
                "summary": row.get("llm_context_summary"),
            }
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    LOGGER.info("Wrote JSONL context summaries to %s", path)


def parse_args():
    parser = argparse.ArgumentParser(description="Convert raw football data into LLM/RAG-friendly features.")
    parser.add_argument("--input", required=True, type=Path, help="Raw merged CSV, e.g. world_cup_model_data.csv")
    parser.add_argument("--output", default=Path("world_cup_model_features.csv"), type=Path)
    parser.add_argument("--predictions-csv", type=Path, help="Optional ML/XGBoost prediction CSV with predicted_* probability columns")
    parser.add_argument("--jsonl-output", type=Path, help="Optional JSONL summaries for retrieval indexing")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)
    try:
        features = read_csv(args.input)
        predictions = read_csv(args.predictions_csv) if args.predictions_csv else None
        if predictions is not None:
            features = merge_predictions(add_normalized_team_keys(features), predictions)
        features = engineer_features(features)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        features.to_csv(args.output, index=False)
        LOGGER.info("Wrote engineered features to %s rows=%d", args.output, len(features))
        if args.jsonl_output:
            write_jsonl(features, args.jsonl_output)
        return 0
    except Exception:
        LOGGER.exception("Feature engineering failed.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
