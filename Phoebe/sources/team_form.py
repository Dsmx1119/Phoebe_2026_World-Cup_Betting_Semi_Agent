from __future__ import annotations

from sportmira.config import Settings
from sportmira.schemas import MatchContext, SourceResult
from sportmira.sources.base import SourceAdapter
from sportmira.utils.time import utc_now_iso


class TeamFormAdapter(SourceAdapter):
    source_name = "team_form"

    def collect(self, match: MatchContext, settings: Settings) -> SourceResult:
        # Free public sources vary heavily by competition. The MVP keeps the schema
        # explicit and marks unavailable instead of inventing form data.
        return SourceResult(
            source_name=self.source_name,
            source_url="public_sources_best_effort",
            accessed_at=utc_now_iso(),
            data={
                "status": "missing",
                "teams": [
                    {
                        "team": match.home_team,
                        "last_matches": [],
                        "avg_goals_for": None,
                        "avg_goals_against": None,
                        "cards": None,
                        "formation": None,
                    },
                    {
                        "team": match.away_team,
                        "last_matches": [],
                        "avg_goals_for": None,
                        "avg_goals_against": None,
                        "cards": None,
                        "formation": None,
                    },
                ],
            },
            confidence="low",
            notes="No reliable structured free form data was parsed; model must use low-confidence baseline or market prior.",
        )
