import unittest

from sportmira.models.correlation_guard import correlation_group, filter_correlated
from sportmira.schemas import BetRecommendation


class CorrelationGuardTests(unittest.TestCase):
    def test_group_under_and_draw(self):
        self.assertEqual(correlation_group("total_goals", "under", 2.5), "low_score_path")
        self.assertEqual(correlation_group("1x2", "draw"), "low_score_path")

    def test_filter_correlated_conservative(self):
        recs = [
            BetRecommendation("Under 2.5", "total_goals", "under", 1.9, 0.56, 0.53, 0.06, 0, correlation_group="low_score_path"),
            BetRecommendation("Draw", "1x2", "draw", 3.1, 0.34, 0.32, 0.05, 0, correlation_group="low_score_path"),
        ]
        selected, warnings = filter_correlated(recs, max_bets=3, risk_mode="conservative")
        self.assertEqual(len(selected), 1)
        self.assertTrue(warnings)

    def test_filter_keeps_only_one_1x2_direction_by_default(self):
        recs = [
            BetRecommendation("Home", "1x2", "home", 2.8, 0.39, 0.36, 0.09, 0),
            BetRecommendation("Draw", "1x2", "draw", 3.5, 0.31, 0.29, 0.08, 0),
            BetRecommendation("Away", "1x2", "away", 3.2, 0.32, 0.31, 0.05, 0),
        ]
        selected, warnings = filter_correlated(recs, max_bets=3, risk_mode="conservative")
        self.assertEqual(len(selected), 1)
        self.assertTrue(any("1X2" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
