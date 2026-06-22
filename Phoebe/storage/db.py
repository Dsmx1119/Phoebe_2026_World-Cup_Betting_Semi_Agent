from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

from sportmira.config import Settings, get_settings
from sportmira.schemas import BettingCard, PostMatchReview, ResearchPackage
from sportmira.storage.migrations import SCHEMA_SQL
from sportmira.utils.time import utc_now_iso


def connect(settings: Optional[Settings] = None) -> sqlite3.Connection:
    settings = settings or get_settings()
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(settings.db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    return conn


def upsert_match(conn: sqlite3.Connection, package_or_match: Any) -> int:
    if hasattr(package_or_match, "match"):
        match = package_or_match.match
    else:
        match = package_or_match
    conn.execute(
        "INSERT INTO matches(raw_match, home_team, away_team, created_at) VALUES (?, ?, ?, ?)",
        (match.raw_match, match.home_team, match.away_team, utc_now_iso()),
    )
    conn.commit()
    return int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])


def save_research_package(package: ResearchPackage, report_markdown: str, settings: Optional[Settings] = None) -> int:
    conn = connect(settings)
    match_id = upsert_match(conn, package)
    for source in package.sources:
        conn.execute(
            "INSERT INTO source_snapshots(match_id, source_name, source_url, accessed_at, confidence, payload_json) VALUES (?, ?, ?, ?, ?, ?)",
            (match_id, source.source_name, source.source_url, source.accessed_at, source.confidence, json.dumps(source.model_dump(), ensure_ascii=False)),
        )
    if package.odds_snapshot:
        conn.execute(
            "INSERT INTO odds_snapshots(match_id, captured_at, source_name, payload_json) VALUES (?, ?, ?, ?)",
            (
                match_id,
                package.odds_snapshot.captured_at,
                package.odds_snapshot.source_name,
                json.dumps(package.odds_snapshot.model_dump(), ensure_ascii=False),
            ),
        )
    conn.execute(
        "INSERT INTO research_reports(match_id, created_at, report_markdown, payload_json) VALUES (?, ?, ?, ?)",
        (match_id, utc_now_iso(), report_markdown, json.dumps(package.model_dump(), ensure_ascii=False)),
    )
    if package.betting_card:
        conn.execute(
            "INSERT INTO betting_cards(match_id, created_at, payload_json) VALUES (?, ?, ?)",
            (match_id, utc_now_iso(), json.dumps(package.betting_card.model_dump(), ensure_ascii=False)),
        )
    conn.commit()
    conn.close()
    return match_id


def latest_betting_card(match_name: str, settings: Optional[Settings] = None) -> Optional[Dict[str, Any]]:
    conn = connect(settings)
    row = conn.execute(
        """
        SELECT betting_cards.payload_json
        FROM betting_cards
        JOIN matches ON matches.id = betting_cards.match_id
        WHERE lower(matches.raw_match) = lower(?)
        ORDER BY betting_cards.id DESC
        LIMIT 1
        """,
        (match_name,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return json.loads(row["payload_json"])


def save_post_match_review(review: PostMatchReview, settings: Optional[Settings] = None) -> int:
    conn = connect(settings)
    class _Match:
        raw_match = review.match
        home_team = review.match
        away_team = ""
    match_id = upsert_match(conn, _Match)
    conn.execute(
        "INSERT INTO post_match_reviews(match_id, reviewed_at, payload_json) VALUES (?, ?, ?)",
        (match_id, review.reviewed_at, json.dumps(review.model_dump(), ensure_ascii=False)),
    )
    conn.commit()
    conn.close()
    return match_id
