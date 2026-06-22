import unittest

from sportmira.odds.market_normalizer import normalize_snapshot
from sportmira.odds.market_parser import parse_odds_text


class MarketParserTests(unittest.TestCase):
    def test_parse_chinese_1x2_and_totals(self):
        text = """
        胜平负
        Korea 2.10
        平局 3.20
        Czechia 3.50
        进球
        大 2.5 1.91
        小 2.5 1.95
        有人被罚下场 是 4.50 否 1.18
        """
        snapshot = normalize_snapshot(parse_odds_text(text, "Korea vs Czechia", "Korea", "Czechia"))
        pairs = {(s.market, s.selection, s.line): s.odds for s in snapshot.selections}
        self.assertEqual(pairs[("1x2", "home", None)], 2.10)
        self.assertEqual(pairs[("1x2", "draw", None)], 3.20)
        self.assertEqual(pairs[("1x2", "away", None)], 3.50)
        self.assertEqual(pairs[("total_goals", "over", 2.5)], 1.91)
        self.assertEqual(pairs[("red_card", "yes", None)], 4.50)

    def test_parse_mocked_ocr_text(self):
        text = "Total Goals Over 2.5 2.05 Under 2.5 1.80"
        snapshot = parse_odds_text(text)
        self.assertEqual(len(snapshot.selections), 2)
        self.assertEqual(snapshot.selections[0].market, "total_goals")


if __name__ == "__main__":
    unittest.main()
