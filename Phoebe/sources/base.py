from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from sportmira.config import Settings
from sportmira.schemas import MatchContext, SourceResult
from sportmira.utils.time import utc_now_iso


class SourceAdapter(ABC):
    source_name = "base"

    @abstractmethod
    def collect(self, match: MatchContext, settings: Settings) -> SourceResult:
        raise NotImplementedError

    def unavailable(self, url: str, reason: str, confidence: str = "low") -> SourceResult:
        return SourceResult(
            source_name=self.source_name,
            source_url=url,
            accessed_at=utc_now_iso(),
            data={"status": "unavailable", "reason": reason},
            confidence=confidence,
            notes=reason,
        )


def safe_collect(adapter: SourceAdapter, match: MatchContext, settings: Settings) -> SourceResult:
    try:
        return adapter.collect(match, settings)
    except Exception as exc:
        return adapter.unavailable("adapter_error", f"{adapter.source_name} failed independently: {exc}")
