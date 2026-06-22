from __future__ import annotations

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_match TEXT NOT NULL,
    home_team TEXT,
    away_team TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER,
    source_name TEXT NOT NULL,
    source_url TEXT,
    accessed_at TEXT,
    confidence TEXT,
    payload_json TEXT NOT NULL,
    FOREIGN KEY(match_id) REFERENCES matches(id)
);

CREATE TABLE IF NOT EXISTS odds_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER,
    captured_at TEXT,
    source_name TEXT,
    payload_json TEXT NOT NULL,
    FOREIGN KEY(match_id) REFERENCES matches(id)
);

CREATE TABLE IF NOT EXISTS research_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER,
    created_at TEXT NOT NULL,
    report_markdown TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    FOREIGN KEY(match_id) REFERENCES matches(id)
);

CREATE TABLE IF NOT EXISTS betting_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER,
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    FOREIGN KEY(match_id) REFERENCES matches(id)
);

CREATE TABLE IF NOT EXISTS post_match_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER,
    reviewed_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    FOREIGN KEY(match_id) REFERENCES matches(id)
);
"""
