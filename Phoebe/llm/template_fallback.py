from __future__ import annotations

from sportmira.reports.memo_writer import write_memo
from sportmira.schemas import ResearchPackage


def render_report(package: ResearchPackage) -> str:
    return write_memo(package)
