import unittest

from sportmira.models.cards_model import build_cards_estimates
from sportmira.schemas import OddsSelection, OddsSnapshot, SourceResult
from sportmira.utils.time import utc_now_iso


def referee_source(cards_per_match=5.47):
    return SourceResult(
        source_name="referee_profile",
        source_url="test",
        accessed_at=utc_now_iso(),
        data={"yellow_cards_per_match": cards_per_match},
        confidence="medium",
    )


def one_x_two_snapshot(home_prob, draw_prob, away_prob):
    return OddsSnapshot(
        match="A vs B",
        captured_at=utc_now_iso(),
        source_name="test",
        source_url="test",
        selections=[
            OddsSelection("1x2", "home", 1.0 / home_prob, no_vig_probability=home_prob),
            OddsSelection("1x2", "draw", 1.0 / draw_prob, no_vig_probability=draw_prob),
            OddsSelection("1x2", "away", 1.0 / away_prob, no_vig_probability=away_prob),
        ],
    )


class CardsModelTests(unittest.TestCase):
    def test_includes_low_card_total_line(self):
        estimates = build_cards_estimates([referee_source()], None)
        card_lines = {estimate.line for estimate in estimates if estimate.market == "total_cards"}
        self.assertIn(2.5, card_lines)

    def test_strong_favorite_downgrades_card_over_confidence(self):
        balanced = build_cards_estimates([referee_source()], one_x_two_snapshot(0.42, 0.28, 0.30))
        lopsided = build_cards_estimates([referee_source()], one_x_two_snapshot(0.91, 0.06, 0.03))
        balanced_over = next(e for e in balanced if e.market == "total_cards" and e.selection == "over" and e.line == 3.5)
        lopsided_over = next(e for e in lopsided if e.market == "total_cards" and e.selection == "over" and e.line == 3.5)
        self.assertLess(lopsided_over.probability, balanced_over.probability)
        self.assertEqual(lopsided_over.confidence, "low")


if __name__ == "__main__":
    unittest.main()
