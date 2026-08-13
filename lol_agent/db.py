from __future__ import annotations

from pathlib import Path
import duckdb

SCHEMA = """
CREATE TABLE IF NOT EXISTS series (
 series_id VARCHAR PRIMARY KEY, team_a VARCHAR NOT NULL, team_b VARCHAR NOT NULL,
 competition VARCHAR, match_date DATE, winner VARCHAR, source VARCHAR, source_url VARCHAR,
 status VARCHAR);
CREATE TABLE IF NOT EXISTS games (
 game_id VARCHAR PRIMARY KEY, series_id VARCHAR NOT NULL, game_number INTEGER NOT NULL,
 winner VARCHAR, team_a_kills INTEGER, team_b_kills INTEGER, duration_seconds INTEGER,
 completed BOOLEAN DEFAULT true, source VARCHAR, source_url VARCHAR, timeline_complete BOOLEAN DEFAULT false);
CREATE TABLE IF NOT EXISTS players (
 player_id VARCHAR PRIMARY KEY, display_name VARCHAR NOT NULL, team VARCHAR,
 source VARCHAR, source_url VARCHAR);
CREATE TABLE IF NOT EXISTS game_stats (
 game_id VARCHAR NOT NULL, player_id VARCHAR, team VARCHAR, kills INTEGER, deaths INTEGER,
 assists INTEGER, cs INTEGER, gold INTEGER, raw_json VARCHAR, source VARCHAR,
 PRIMARY KEY (game_id, player_id));
CREATE TABLE IF NOT EXISTS events (
 event_id VARCHAR PRIMARY KEY, game_id VARCHAR NOT NULL, timestamp_seconds INTEGER,
 timestamp_display VARCHAR, team VARCHAR, player VARCHAR, event_type VARCHAR NOT NULL,
 target_team VARCHAR, target_player VARCHAR, lane VARCHAR, structure VARCHAR,
 objective_type VARCHAR, counts_as_elemental_dragon BOOLEAN, raw_text VARCHAR,
 raw_html VARCHAR, source VARCHAR, source_url VARCHAR, parser_version VARCHAR);
CREATE TABLE IF NOT EXISTS source_snapshots (
 source_key VARCHAR PRIMARY KEY, source VARCHAR, source_url VARCHAR, raw_path VARCHAR,
 captured_at TIMESTAMP DEFAULT current_timestamp);
CREATE TABLE IF NOT EXISTS vod_metadata (
 vod_id VARCHAR PRIMARY KEY, game_id VARCHAR, provider VARCHAR, url VARCHAR,
 title VARCHAR, published_at TIMESTAMP, duration_seconds INTEGER, source_snapshot_key VARCHAR);
CREATE TABLE IF NOT EXISTS evidence (
 evidence_id VARCHAR PRIMARY KEY, game_id VARCHAR, event_id VARCHAR, claim_type VARCHAR,
 result VARCHAR, detail VARCHAR, source VARCHAR, source_url VARCHAR, confidence VARCHAR,
 created_at TIMESTAMP DEFAULT current_timestamp);
"""


def connect(path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(path)
    connection.execute(SCHEMA)
    columns = {row[0] for row in connection.execute("DESCRIBE games").fetchall()}
    if "timeline_complete" not in columns:
        connection.execute("ALTER TABLE games ADD COLUMN timeline_complete BOOLEAN DEFAULT false")
    series_columns = {row[0] for row in connection.execute("DESCRIBE series").fetchall()}
    if "status" not in series_columns:
        connection.execute("ALTER TABLE series ADD COLUMN status VARCHAR")
    return connection
