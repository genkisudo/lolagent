from __future__ import annotations

import argparse
import json
from pathlib import Path
from .db import connect
from .ingest import ingest_json
from .questions import parse_question
from .resolve import answer

DEFAULT_DB = "data/db/lol_agent.duckdb"


def main() -> None:
    parser = argparse.ArgumentParser(prog="lol-agent", description="Deterministic LoL esports results and evidence agent")
    parser.add_argument("--db", default=DEFAULT_DB, help=f"DuckDB path (place before command; default: {DEFAULT_DB})")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Create the DuckDB schema")
    ingest = sub.add_parser("ingest-json", help="Snapshot and ingest normalized source JSON")
    ingest.add_argument("path")
    ingest.add_argument("--force", action="store_true", help="Reparse this snapshot after an adapter/parser update")
    ask = sub.add_parser("answer", help="Resolve a factual question from stored evidence")
    ask.add_argument("--match", required=True, help="Team A vs Team B, in source order")
    ask.add_argument("--question", required=True)
    ask.add_argument("--game", type=int)
    ask.add_argument("--date")
    ask.add_argument("--competition")
    ask.add_argument("--json", action="store_true", help="Emit machine-readable output")
    args = parser.parse_args()
    if args.command == "init":
        connect(args.db).close()
        print(f"Initialized {args.db}")
    elif args.command == "ingest-json":
        ingest_json(args.path, args.db, force=args.force)
        print(f"Ingested {Path(args.path).name} into {args.db}")
    else:
        response = answer(args.db, args.match, parse_question(args.question, args.game), args.date, args.competition)
        print(json.dumps(response.as_dict(), indent=2) if args.json else response.render())
