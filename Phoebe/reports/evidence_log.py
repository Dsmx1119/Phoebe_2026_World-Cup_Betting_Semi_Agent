from __future__ import annotations

from typing import Iterable, List, Optional

from sportmira.schemas import EvidenceItem, OddsSnapshot, SourceResult
from sportmira.utils.time import utc_now_iso


def build_evidence_log(sources: Iterable[SourceResult], odds_snapshot: Optional[OddsSnapshot] = None) -> List[EvidenceItem]:
    evidence: List[EvidenceItem] = []
    idx = 1
    for source in sources:
        status = source.data.get("status", "available") if source.data else "available"
        kind = "fact" if status not in {"missing", "unavailable"} else "missing"
        claim = f"{source.source_name} returned status={status}; notes={source.notes or 'none'}"
        evidence.append(
            EvidenceItem(
                id=f"E{idx}",
                claim=claim,
                source_name=source.source_name,
                source_url=source.source_url,
                accessed_at=source.accessed_at,
                confidence=source.confidence,
                used_in="data_collection",
                kind=kind,
            )
        )
        idx += 1
    if odds_snapshot:
        evidence.append(
            EvidenceItem(
                id=f"E{idx}",
                claim=f"Odds snapshot captured with {len(odds_snapshot.selections)} parsed selections.",
                source_name=odds_snapshot.source_name,
                source_url=odds_snapshot.source_url,
                accessed_at=odds_snapshot.captured_at,
                confidence="medium" if odds_snapshot.selections else "low",
                used_in="odds_snapshot,model,betting_card",
                kind="fact" if odds_snapshot.selections else "missing",
            )
        )
    return evidence
