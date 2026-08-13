from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from .db import connect

ELEMENTAL = {"INFERNAL", "MOUNTAIN", "OCEAN", "HEXTECH", "CHEMTECH", "CLOUD"}


def seconds(value: str | int | None) -> int | None:
    if value is None or isinstance(value, int):
        return value
    minutes, remainder = value.split(":", 1)
    return int(minutes) * 60 + int(remainder)


def ingest_json(path: str, db_path: str, raw_root: str = "data/raw", force: bool = False) -> None:
    raw = Path(path).read_bytes()
    document = json.loads(raw)
    source = document.get("source", "unknown")
    key = document.get("source_key") or hashlib.sha256(raw).hexdigest()
    raw_destination = Path(raw_root) / source.lower().replace(".", "_") / f"{key}.json"
    raw_destination.parent.mkdir(parents=True, exist_ok=True)
    if not raw_destination.exists():
        shutil.copyfile(path, raw_destination)
    con = connect(db_path)
    series = document["series"]
    already_ingested = con.execute("SELECT 1 FROM source_snapshots WHERE source_key = ?", [key]).fetchone()
    if already_ingested and not force:
        return
    if already_ingested:
        game_ids = [game["id"] for game in document.get("games", [])]
        for game_id in game_ids:
            con.execute("DELETE FROM evidence WHERE game_id = ?", [game_id])
            con.execute("DELETE FROM events WHERE game_id = ?", [game_id])
            con.execute("DELETE FROM game_stats WHERE game_id = ?", [game_id])
            con.execute("DELETE FROM games WHERE game_id = ?", [game_id])
        con.execute("DELETE FROM source_snapshots WHERE source_key = ?", [key])
    con.execute("DELETE FROM series WHERE series_id = ?", [series["id"]])
    con.execute("INSERT INTO source_snapshots(source_key, source, source_url, raw_path) VALUES (?, ?, ?, ?)", [key, source, document.get("source_url"), str(raw_destination)])
    con.execute("INSERT INTO series VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [series["id"], series["team_a"], series["team_b"], series.get("competition"), series.get("match_date"), series.get("winner"), source, document.get("source_url")])
    for game in document.get("games", []):
        con.execute("""INSERT INTO games
            (game_id, series_id, game_number, winner, team_a_kills, team_b_kills,
             duration_seconds, completed, source, source_url, timeline_complete)
            VALUES (?, ?, ?, ?, ?, ?, ?, true, ?, ?, ?)""",
            [game["id"], series["id"], game["number"], game.get("winner"),
             game.get("team_a_kills"), game.get("team_b_kills"), game.get("duration_seconds"),
             source, game.get("source_url", document.get("source_url")), game.get("timeline_complete", False)])
        for index, event in enumerate(game.get("events", [])):
            event_type = event["event_type"].upper()
            objective = (event.get("objective_type") or "").upper()
            event_id = event.get("id") or f"{game['id']}:{index}:{hashlib.sha1(json.dumps(event, sort_keys=True).encode()).hexdigest()[:10]}"
            elemental = event_type == "DRAGON_SLAIN" and objective in ELEMENTAL
            con.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [event_id, game["id"], seconds(event.get("timestamp")), event.get("timestamp"), event.get("team"), event.get("player"), event_type, event.get("target_team"), event.get("target_player"), event.get("lane"), event.get("structure"), objective or None, elemental, event.get("raw_text"), event.get("raw_html"), source, event.get("source_url", document.get("source_url")), event.get("parser_version", "json-v1")])
