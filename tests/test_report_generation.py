import unittest

from sportmira.reports.evidence_log import build_evidence_log
from sportmira.reports.memo_writer import write_memo
from sportmira.schemas import MatchContext, ResearchPackage, RouteDecision, SourceResult
from sportmira.utils.time import utc_now_iso


class ReportGenerationTests(unittest.TestCase):
    def test_report_has_required_sections_and_evidence(self):
        source = SourceResult(
            source_name="team_form",
            source_url="test",
            accessed_at=utc_now_iso(),
            data={"status": "missing"},
            confidence="low",
            notes="test missing",
        )
        package = ResearchPackage(
            match=MatchContext("Korea vs Czechia", "Korea", "Czechia"),
            route=RouteDecision("standard", "medium"),
            sources=[source],
            stale_after=utc_now_iso(),
            must_refresh_if=["lineups change"],
        )
        package.evidence = build_evidence_log(package.sources)
        report = write_memo(package)
        self.assertIn("# SportMira Match Betting Memo: Korea vs Czechia", report)
        self.assertIn("## 10. Evidence Log", report)
        self.assertIn("stale_after", report)
        self.assertIn("lineups change", report)


if __name__ == "__main__":
    unittest.main()
