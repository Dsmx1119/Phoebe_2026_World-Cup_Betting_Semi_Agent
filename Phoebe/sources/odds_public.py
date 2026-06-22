from __future__ import annotations

from typing import Optional

from sportmira.config import Settings
from sportmira.odds.market_normalizer import normalize_snapshot
from sportmira.odds.market_parser import parse_odds_text
from sportmira.schemas import MatchContext, OddsSnapshot, SourceResult
from sportmira.sources.base import SourceAdapter
from sportmira.utils.time import utc_now_iso
from sportmira.utils.web import fetch_public_url


class OddsPublicAdapter(SourceAdapter):
    source_name = "odds_public"

    def __init__(self, url: Optional[str] = None):
        self.url = url

    def collect(self, match: MatchContext, settings: Settings) -> SourceResult:
        if not self.url:
            return self.unavailable("odds_url_missing", "No public odds URL was provided.")
        fetched = fetch_public_url(settings, self.url)
        if fetched.get("error") or int(fetched.get("status_code") or 0) >= 400:
            return self.unavailable(self.url, str(fetched.get("error") or f"HTTP {fetched.get('status_code')}"))
        snapshot = parse_odds_text(
            str(fetched.get("text") or ""),
            match_name=match.raw_match,
            home_team=match.home_team,
            away_team=match.away_team,
            source_name=self.source_name,
            source_url=self.url,
        )
        normalize_snapshot(snapshot)
        return SourceResult(
            source_name=self.source_name,
            source_url=self.url,
            accessed_at=utc_now_iso(),
            data={"status": "available", "odds_snapshot": snapshot.model_dump()},
            confidence="medium" if snapshot.selections else "low",
            notes="Public odds page parsed with generic text parser; confirm fields if page layout is complex.",
        )


def odds_snapshot_from_source(result: SourceResult) -> Optional[OddsSnapshot]:
    data = result.data.get("odds_snapshot") if result.data else None
    if not isinstance(data, dict):
        return None
    try:
        from sportmira.schemas import OddsSelection

        selections = [OddsSelection(**item) for item in data.get("selections", [])]
        return OddsSnapshot(
            match=data.get("match"),
            captured_at=data.get("captured_at", utc_now_iso()),
            source_name=data.get("source_name", result.source_name),
            source_url=data.get("source_url", result.source_url),
            selections=selections,
            ocr_confidence=data.get("ocr_confidence"),
            raw_text=data.get("raw_text", ""),
            warnings=data.get("warnings", []),
        )
    except Exception:
        return None
