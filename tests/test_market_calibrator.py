import unittest

from sportmira.models.market_calibrator import (
    blend_probabilities,
    fit_market_calibration,
    no_vig_probabilities,
)


class MarketCalibratorTests(unittest.TestCase):
    def test_no_vig_probabilities_sum_to_one(self):
        probs = no_vig_probabilities([2.0, 3.5, 4.0])
        self.assertAlmostEqual(sum(probs), 1.0)
        self.assertGreater(probs[0], probs[2])

    def test_blend_probabilities_uses_market_alpha(self):
        model = [0.2, 0.3, 0.5]
        market = [0.5, 0.3, 0.2]
        self.assertEqual(blend_probabilities(model, market, 0.0), model)
        self.assertEqual(blend_probabilities(model, market, 1.0), market)

    def test_fit_market_calibration_prefers_better_market_when_model_is_bad(self):
        samples = [
            {
                "result": "home",
                "model_probabilities": [0.1, 0.2, 0.7],
                "market_probabilities": [0.7, 0.2, 0.1],
            },
            {
                "result": "away",
                "model_probabilities": [0.7, 0.2, 0.1],
                "market_probabilities": [0.1, 0.2, 0.7],
            },
        ]
        fit = fit_market_calibration(samples)
        self.assertGreater(fit.market_alpha, 0.5)
        self.assertLess(fit.train_log_loss, fit.model_log_loss)


if __name__ == "__main__":
    unittest.main()
