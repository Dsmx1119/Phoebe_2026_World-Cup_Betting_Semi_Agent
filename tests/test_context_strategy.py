import unittest

from sportmira.context_strategy import (
    asian_handicap_expected_value,
    decimal_implied_probability,
    expected_value,
    fuzzy_team_score,
    no_vig_probabilities,
    parse_handicap_line,
    probability_edge,
)


class ContextStrategyTests(unittest.TestCase):
    def test_parse_handicap_line(self):
        self.assertEqual(parse_handicap_line("-0.25"), -0.25)
        self.assertEqual(parse_handicap_line("France -0.5"), -0.5)

    def test_water_to_probabilities(self):
        self.assertAlmostEqual(decimal_implied_probability(1.95), 1 / 1.95)
        no_vig = no_vig_probabilities([1.95, 1.95])
        self.assertAlmostEqual(no_vig[0], 0.5)
        self.assertAlmostEqual(no_vig[1], 0.5)

    def test_ev_and_probability_edge(self):
        self.assertAlmostEqual(expected_value(0.54, 1.95), 0.053)
        self.assertAlmostEqual(probability_edge(0.54, 2.0), 0.04)

    def test_asian_handicap_ev_for_half_and_quarter_lines(self):
        self.assertAlmostEqual(asian_handicap_expected_value("home", -0.5, 1.95, 0.54, 0.24, 0.22), 0.053)
        self.assertAlmostEqual(asian_handicap_expected_value("home", -0.25, 1.95, 0.54, 0.24, 0.22), 0.173)
        self.assertAlmostEqual(asian_handicap_expected_value("away", -0.25, 1.95, 0.54, 0.24, 0.22), -0.217)

    def test_team_fuzzy_match_alias(self):
        self.assertGreater(fuzzy_team_score("South Korea", "Korea Republic"), 0.9)


if __name__ == "__main__":
    unittest.main()
