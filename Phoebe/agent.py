from __future__ import annotations

from typing import Optional, Tuple

from sportmira.config import Settings, get_settings
from sportmira.llm.local_ollama import LocalOllamaClient
from sportmira.llm.template_fallback import render_report as render_template_report
from sportmira.models.cards_model import build_cards_estimates
from sportmira.models.ev import build_betting_card
from sportmira.models.poisson_goals import build_goals_model
from sportmira.odds.market_normalizer import normalize_snapshot
from sportmira.odds.screenshot_ocr import ocr_screenshot
from sportmira.reports.evidence_log import build_evidence_log
from sportmira.reports.markdown_report import save_markdown_report
from sportmira.schemas import MatchContext, OddsSnapshot, ResearchPackage
from sportmira.sources.odds_public import odds_snapshot_from_source
from sportmira.sources.registry import collect_sources
from sportmira.storage.db import save_research_package
from sportmira.utils.text import parse_match_name
from sportmira.utils.time import iso_after_hours
from sportmira.router import route_task


class SportMiraAgent:
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    def _match_context(self, raw_match: Optional[str], language: str = "zh") -> MatchContext:
        raw = raw_match or "Unknown Team A vs Unknown Team B"
        home, away = parse_match_name(raw)
        return MatchContext(raw_match=raw, home_team=home, away_team=away, language=language)

    def _report_with_local_llm_first(self, package: ResearchPackage) -> str:
        # Keep the deterministic memo as the source of truth. Ollama may be used only
        # if it preserves the required memo skeleton; otherwise template fallback wins.
        deterministic = render_template_report(package)
        client = LocalOllamaClient(self.settings)
        prompt = (
            "Polish this markdown memo without adding facts. Preserve all headings, tables, "
            "evidence IDs, stale_after, and must_refresh_if.\n\n"
            + deterministic
        )
        generated = client.generate(prompt, timeout=5.0)
        if generated and "## 10. Evidence Log" in generated and "must_refresh_if" in generated:
            return generated
        return deterministic

    def analyze(
        self,
        match: Optional[str],
        screenshot: Optional[str] = None,
        odds_url: Optional[str] = None,
        bankroll: float = 0.0,
        unit: str = "u",
        max_bets: int = 3,
        language: str = "zh",
        risk_mode: str = "conservative",
        task_text: str = "",
    ) -> Tuple[ResearchPackage, str, str]:
        context = self._match_context(match, language=language)
        route = route_task(
            text=task_text or match or "",
            match=match,
            screenshot=screenshot,
            bankroll=bankroll,
            max_bets=max_bets,
        )
        sources = collect_sources(context, self.settings, odds_url=odds_url) if route.needs_research else []
        odds_snapshot: Optional[OddsSnapshot] = None
        if screenshot:
            odds_snapshot = ocr_screenshot(
                screenshot,
                match_name=context.raw_match,
                home_team=context.home_team,
                away_team=context.away_team,
                output_json="odds_snapshot.json",
            )
        if not odds_snapshot:
            for source in sources:
                odds_snapshot = odds_snapshot_from_source(source)
                if odds_snapshot:
                    break
        if odds_snapshot:
            normalize_snapshot(odds_snapshot)
        model_output = build_goals_model(context.raw_match, sources, odds_snapshot, self.settings)
        model_output.estimates.extend(build_cards_estimates(sources, odds_snapshot))
        card = None
        if bankroll > 0 or route.task_type == "betting_card":
            card = build_betting_card(
                context.raw_match,
                odds_snapshot,
                model_output,
                bankroll=bankroll,
                unit=unit,
                max_bets=max_bets,
                risk_mode=risk_mode,
            )
        must_refresh_if = [
            "starting lineups differ materially",
            "referee announced or changes",
            "odds move more than 8-10% from captured snapshot",
            "key player ruled out or unexpectedly starts",
            "weather/venue/kickoff changes",
            "live red card or early penalty changes match state",
        ]
        package = ResearchPackage(
            match=context,
            route=route,
            sources=sources,
            odds_snapshot=odds_snapshot,
            model_output=model_output,
            betting_card=card,
            stale_after=iso_after_hours(12),
            must_refresh_if=must_refresh_if,
        )
        package.evidence = build_evidence_log(sources, odds_snapshot=odds_snapshot)
        report = self._report_with_local_llm_first(package)
        report_path = save_markdown_report(context.raw_match, report)
        save_research_package(package, report, settings=self.settings)
        return package, report, report_path
