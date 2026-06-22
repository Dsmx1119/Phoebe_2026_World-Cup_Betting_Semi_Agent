from __future__ import annotations

import json
from dataclasses import asdict, field, is_dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from pydantic.dataclasses import dataclass as schema_dataclass  # type: ignore
except Exception:
    from dataclasses import dataclass as schema_dataclass


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def to_plain(value: Any) -> Any:
    if is_dataclass(value):
        return {k: to_plain(v) for k, v in asdict(value).items()}
    if isinstance(value, list):
        return [to_plain(v) for v in value]
    if isinstance(value, dict):
        return {str(k): to_plain(v) for k, v in value.items()}
    return value


@schema_dataclass
class Serializable:
    def model_dump(self) -> Dict[str, Any]:
        return to_plain(self)

    def model_dump_json(self, indent: int = 2) -> str:
        return json.dumps(self.model_dump(), ensure_ascii=False, indent=indent)


@schema_dataclass
class SourceResult(Serializable):
    source_name: str
    source_url: str
    accessed_at: str
    data: Dict[str, Any]
    confidence: str = "low"
    notes: str = ""


@schema_dataclass
class EvidenceItem(Serializable):
    id: str
    claim: str
    source_name: str
    source_url: str
    accessed_at: str
    confidence: str
    used_in: str
    kind: str = "fact"


@schema_dataclass
class MatchContext(Serializable):
    raw_match: str
    home_team: str
    away_team: str
    competition: Optional[str] = None
    kickoff_time: Optional[str] = None
    venue: Optional[str] = None
    neutral_site: Optional[bool] = None
    language: str = "zh"


@schema_dataclass
class RouteDecision(Serializable):
    task_type: str
    confidence: str
    reasons: List[str] = field(default_factory=list)
    needs_odds: bool = True
    needs_research: bool = True
    needs_review: bool = False


@schema_dataclass
class OddsSelection(Serializable):
    market: str
    selection: str
    odds: float
    line: Optional[float] = None
    implied_probability: Optional[float] = None
    no_vig_probability: Optional[float] = None
    source: str = "user_or_ocr"
    notes: str = ""


@schema_dataclass
class OddsSnapshot(Serializable):
    match: Optional[str]
    captured_at: str
    source_name: str
    source_url: str
    selections: List[OddsSelection] = field(default_factory=list)
    ocr_confidence: Optional[float] = None
    raw_text: str = ""
    warnings: List[str] = field(default_factory=list)


@schema_dataclass
class ProbabilityEstimate(Serializable):
    market: str
    selection: str
    probability: float
    confidence: str
    basis: str
    line: Optional[float] = None


@schema_dataclass
class ModelOutput(Serializable):
    match: str
    generated_at: str
    estimates: List[ProbabilityEstimate] = field(default_factory=list)
    likely_scorelines: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@schema_dataclass
class BetRecommendation(Serializable):
    bet: str
    market: str
    selection: str
    odds: float
    model_probability: float
    implied_probability: float
    edge: float
    stake: float
    unit: str = "u"
    confidence: str = "low"
    reason: str = ""
    main_risk: str = ""
    correlation_group: str = ""


@schema_dataclass
class BettingCard(Serializable):
    match: str
    bankroll: float
    unit: str
    max_bets: int
    risk_mode: str
    recommendations: List[BetRecommendation] = field(default_factory=list)
    rejected: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    no_bet: bool = False


@schema_dataclass
class ResearchPackage(Serializable):
    match: MatchContext
    route: RouteDecision
    sources: List[SourceResult] = field(default_factory=list)
    odds_snapshot: Optional[OddsSnapshot] = None
    model_output: Optional[ModelOutput] = None
    betting_card: Optional[BettingCard] = None
    evidence: List[EvidenceItem] = field(default_factory=list)
    stale_after: str = ""
    must_refresh_if: List[str] = field(default_factory=list)


@schema_dataclass
class PostMatchReview(Serializable):
    match: str
    actual_score: str
    actual_cards: Optional[str]
    actual_red_cards: Optional[str]
    reviewed_at: str
    one_x_two_result: str
    total_goals: int
    pnl: Optional[float]
    error_tags: List[str]
    notes: List[str]
