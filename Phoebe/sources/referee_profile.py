from __future__ import annotations

from sportmira.config import Settings
from sportmira.schemas import MatchContext, SourceResult
from sportmira.sources.base import SourceAdapter
from sportmira.utils.time import utc_now_iso


class RefereeProfileAdapter(SourceAdapter):
    source_name = "referee_profile"

    def collect(self, match: MatchContext, settings: Settings) -> SourceResult:
        return SourceResult(
            source_name=self.source_name,
            source_url="referee_not_announced_or_not_collected",
            accessed_at=utc_now_iso(),
            data={
                "status": "missing",
                "referee_name": None,
                "nationality": None,
                "recent_matches": [],
                "yellow_cards_per_match": None,
                "red_cards_per_match": None,
                "penalty_frequency": None,
                "style_inference": "inference unavailable until referee is identified",
            },
            confidence="low",
            notes="Referee could not be identified from public structured sources; must_refresh_if referee announced or changes.",
        )
