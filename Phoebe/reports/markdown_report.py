from __future__ import annotations

from pathlib import Path

from sportmira.utils.text import slugify


def save_markdown_report(match_name: str, markdown: str, root: str = ".sportmira/reports") -> str:
    path = Path(root)
    path.mkdir(parents=True, exist_ok=True)
    report_path = path / f"{slugify(match_name)}.md"
    report_path.write_text(markdown, encoding="utf-8")
    return str(report_path)
