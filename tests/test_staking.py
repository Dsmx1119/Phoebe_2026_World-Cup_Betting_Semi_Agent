import unittest

from sportmira.models.staking import allocate_stakes
from sportmira.schemas import BetRecommendation


class StakingTests(unittest.TestCase):
    def test_allocate_max_three(self):
        recs = [
            BetRecommendation("A", "1x2", "home", 2.1, 0.55, 0.48, 0.15, 0),
            BetRecommendation("B", "total_goals", "under", 1.9, 0.56, 0.53, 0.06, 0),
            BetRecommendation("C", "red_card", "no", 1.3, 0.90, 0.77, 0.17, 0),
            BetRecommendation("D", "corners", "over", 2.0, 0.54, 0.50, 0.08, 0),
        ]
        allocated = allocate_stakes(recs, bankroll=30, max_bets=3)
        self.assertLessEqual(len(allocated), 3)
        self.assertLessEqual(max(r.stake for r in allocated), 30 * 0.12)
        self.assertLessEqual(sum(r.stake for r in allocated), 30 * 0.35)


if __name__ == "__main__":
    unittest.main()
