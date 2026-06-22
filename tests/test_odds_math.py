import unittest

from sportmira.odds.odds_math import (
    american_to_decimal,
    break_even_probability,
    decimal_to_american,
    decimal_to_implied_probability,
    expected_value,
    remove_vig,
)


class OddsMathTests(unittest.TestCase):
    def test_decimal_to_implied_probability(self):
        self.assertAlmostEqual(decimal_to_implied_probability(2.0), 0.5)

    def test_american_conversion(self):
        self.assertAlmostEqual(american_to_decimal(150), 2.5)
        self.assertAlmostEqual(american_to_decimal(-200), 1.5)
        self.assertEqual(decimal_to_american(2.5), 150)
        self.assertEqual(decimal_to_american(1.5), -200)

    def test_remove_vig(self):
        no_vig = remove_vig([0.55, 0.55])
        self.assertAlmostEqual(sum(no_vig), 1.0)
        self.assertAlmostEqual(no_vig[0], 0.5)

    def test_ev_and_break_even(self):
        self.assertAlmostEqual(expected_value(0.55, 2.0), 0.10)
        self.assertAlmostEqual(break_even_probability(2.0), 0.5)


if __name__ == "__main__":
    unittest.main()
