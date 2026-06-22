from __future__ import annotations

from sportmira.config import Settings
from sportmira.schemas import MatchContext, SourceResult
from sportmira.sources.base import SourceAdapter


class WhoScoredPublicAdapter(SourceAdapter):
    source_name = "whoscored_public"

    def collect(self, match: MatchContext, settings: Settings) -> SourceResult:
        return self.unavailable(
            "https://www.whoscored.com/",
            "WhoScored is JS-heavy and may restrict automated access; SportMira MVP does not bypass protections.",
        )
