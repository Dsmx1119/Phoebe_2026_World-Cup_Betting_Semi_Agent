from __future__ import annotations

from sportmira.config import Settings
from sportmira.schemas import MatchContext, SourceResult
from sportmira.sources.base import SourceAdapter
from sportmira.utils.time import utc_now_iso


class VenueWeatherAdapter(SourceAdapter):
    source_name = "venue_weather"

    def collect(self, match: MatchContext, settings: Settings) -> SourceResult:
        if not match.venue:
            return SourceResult(
                source_name=self.source_name,
                source_url="venue_missing",
                accessed_at=utc_now_iso(),
                data={"status": "missing", "venue": None, "weather": None},
                confidence="low",
                notes="Venue was not provided; weather must be refreshed if venue/kickoff is known.",
            )
        return SourceResult(
            source_name=self.source_name,
            source_url="no_key_free_weather_not_configured",
            accessed_at=utc_now_iso(),
            data={"status": "missing", "venue": match.venue, "weather": None},
            confidence="low",
            notes="No paid weather API is used; add a public weather URL manually if needed.",
        )
