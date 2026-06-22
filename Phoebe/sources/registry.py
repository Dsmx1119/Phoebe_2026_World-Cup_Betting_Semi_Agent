from __future__ import annotations

from typing import List, Optional

from sportmira.config import Settings
from sportmira.schemas import MatchContext, SourceResult
from sportmira.sources.base import SourceAdapter, safe_collect
from sportmira.sources.football_results import FootballResultsAdapter
from sportmira.sources.news_preview import NewsPreviewAdapter
from sportmira.sources.odds_public import OddsPublicAdapter
from sportmira.sources.referee_profile import RefereeProfileAdapter
from sportmira.sources.search_web import SearchWebAdapter
from sportmira.sources.team_form import TeamFormAdapter
from sportmira.sources.venue_weather import VenueWeatherAdapter
from sportmira.sources.whoscored_public import WhoScoredPublicAdapter


def default_adapters(odds_url: Optional[str] = None) -> List[SourceAdapter]:
    adapters: List[SourceAdapter] = [
        TeamFormAdapter(),
        FootballResultsAdapter(),
        NewsPreviewAdapter(),
        RefereeProfileAdapter(),
        VenueWeatherAdapter(),
        WhoScoredPublicAdapter(),
        SearchWebAdapter(),
    ]
    if odds_url:
        adapters.append(OddsPublicAdapter(odds_url))
    return adapters


def collect_sources(match: MatchContext, settings: Settings, odds_url: Optional[str] = None) -> List[SourceResult]:
    return [safe_collect(adapter, match, settings) for adapter in default_adapters(odds_url=odds_url)]
