from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from sportmira.agent import SportMiraAgent
from sportmira.loops.post_match_review import review_match
from sportmira.odds.screenshot_ocr import ocr_screenshot, write_snapshot_json


def _print(text: str) -> None:
    try:
        from rich.console import Console  # type: ignore

        Console().print(text)
    except Exception:
        print(text)


def cmd_analyze(args: argparse.Namespace) -> int:
    agent = SportMiraAgent()
    _package, report, report_path = agent.analyze(
        match=args.match,
        screenshot=args.screenshot,
        odds_url=args.odds_url,
        bankroll=args.bankroll or 0.0,
        unit=args.unit,
        max_bets=args.max_bets,
        language=args.language,
        risk_mode=args.risk_mode,
        task_text=args.text or "",
    )
    _print(report)
    _print(f"\nReport saved: {report_path}")
    return 0


def cmd_parse_odds(args: argparse.Namespace) -> int:
    snapshot = ocr_screenshot(args.screenshot, match_name=args.match, output_json=args.output)
    write_snapshot_json(snapshot, args.output)
    print(json.dumps(snapshot.model_dump(), ensure_ascii=False, indent=2))
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    review = review_match(args.match, args.actual_score, cards=args.cards, red_cards=args.red_cards)
    print(review.model_dump_json(indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sportmira", description="Local-first football betting research agent.")
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="Build a pre-match betting research memo.")
    analyze.add_argument("--match", required=False, help='Match name, e.g. "Korea vs Czechia"')
    analyze.add_argument("--screenshot", required=False, help="Odds screenshot path")
    analyze.add_argument("--odds-url", required=False, help="Public odds page URL")
    analyze.add_argument("--bankroll", type=float, default=0.0)
    analyze.add_argument("--unit", default="u")
    analyze.add_argument("--max-bets", type=int, default=3)
    analyze.add_argument("--language", default="zh")
    analyze.add_argument("--risk-mode", choices=["conservative", "balanced", "aggressive"], default="conservative")
    analyze.add_argument("--text", default="", help="Original natural-language task text")
    analyze.set_defaults(func=cmd_analyze)

    parse_odds = sub.add_parser("parse-odds", help="Parse odds from a screenshot using optional OCR.")
    parse_odds.add_argument("--screenshot", required=True)
    parse_odds.add_argument("--match", required=False)
    parse_odds.add_argument("--output", default="odds_snapshot.json")
    parse_odds.set_defaults(func=cmd_parse_odds)

    review = sub.add_parser("review", help="Store a post-match review.")
    review.add_argument("--match", required=True)
    review.add_argument("--actual-score", required=True)
    review.add_argument("--cards", required=False)
    review.add_argument("--red-cards", required=False)
    review.set_defaults(func=cmd_review)

    return parser


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
