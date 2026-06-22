from __future__ import annotations

from typing import Optional

from sportmira.config import Settings
from sportmira.schemas import MatchContext
from sportmira.sources.registry import collect_sources


def run_pre_match_research(match: MatchContext, settings: Settings, odds_url: Optional[str] = None):
    return collect_sources(match, settings, odds_url=odds_url)
