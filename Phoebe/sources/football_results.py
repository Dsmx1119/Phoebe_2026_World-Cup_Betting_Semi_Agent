from __future__ import annotations

from urllib.parse import quote_plus

from sportmira.config import Settings
from sportmira.schemas import MatchContext, SourceResult
from sportmira.sources.base import SourceAdapter
from sportmira.utils.time import utc_now_iso
from sportmira.utils.web import fetch_public_url


class FootballResultsAdapter(SourceAdapter):
    source_name = "football_results"

    def collect(self, match: MatchContext, settings: Settings) -> SourceResult:
        query = f"{match.home_team} {match.away_team} recent results football"
        url = f"https://en.wikipedia.org/w/index.php?search={quote_plus(query)}"
        fetched = fetch_public_url(settings, url)
        if fetched.get("error") or int(fetched.get("status_code") or 0) >= 400:
            return self.unavailable(url, str(fetched.get("error") or f"HTTP {fetched.get('status_code')}"))
        return SourceResult(
            source_name=self.source_name,
            source_url=url,
            accessed_at=utc_now_iso(),
            data={
                "status": "available_unparsed",
                "summary": "Public results page fetched; structured last-match extraction is limited in MVP.",
            },
            confidence="low",
            notes="MVP stores the public page snapshot but does not claim exact recent results unless parsed.",
        )
