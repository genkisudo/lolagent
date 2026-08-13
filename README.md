# LoL evidence agent

A terminal-first agent for factual questions about completed League of Legends esports games. It resolves results from stored structured evidence—never from prediction logic—and missing evidence never becomes `NO`.

## Requirements

- Python 3.10+
- DuckDB (`pip install -r requirements.txt`)

## Quick start

    python3 -m lol_agent init
    python3 -m lol_agent ingest-json examples/t1_gen_g_game2.json
    python3 -m lol_agent answer --match 'T1 vs Gen.G' --game 2 --question 'Both Teams Slay an Elemental Dragon?'

Use a different database by placing `--db` before the command:

    python3 -m lol_agent --db /tmp/lol_agent.duckdb init

## Commands

    python3 -m lol_agent init
    python3 -m lol_agent ingest-json SNAPSHOT.json
    python3 -m lol_agent ingest-json --force SNAPSHOT.json
    python3 -m lol_agent answer --match MATCH --question QUESTION [--game NUMBER] [--date YYYY-MM-DD] [--competition NAME] [--json]

`ingest-json` first saves an immutable source snapshot under `data/raw/`, then writes parsed records to DuckDB at `data/db/lol_agent.duckdb`. Use `--force` to reprocess an existing snapshot after an adapter or parser update.

`data/` is intentionally excluded from Git: it contains generated DuckDB files and source snapshots that can grow quickly or have redistribution restrictions. The example JSON fixture is committed so the project remains runnable after cloning.

## Evidence safety rules

- Event team attribution must come from the source side/column; it is never inferred from a player name.
- Set `game.timeline_complete` to `true` only when the source adapter collected the entire timeline. `NO` answers for objectives and inhibitor counts require that signal; otherwise the result is `UNKNOWN`.
- Elder Dragon is excluded from elemental-dragon questions.
- Final KDA does not prove a quadra or pentakill. Without explicit multi-kill evidence, the result is `UNKNOWN`.
- A multi-game series without an explicitly identified game returns `AMBIGUOUS` rather than silently selecting one.
- The resolver returns `FLAGGED` with a machine-readable `flags` value for a canceled unplayed series, an explicit tie, or a delayed/postponed series that remains winnerless more than seven days after `scheduled_date` (or `match_date`).

For schedule-state inputs, include an optional `series.status` (`canceled`, `tied`, `delayed`, or `postponed`) and `series.scheduled_date` in the normalized JSON. `scheduled_date` takes precedence over `match_date`.

## Supported questions

- Game and series winner; series score
- First Blood
- Baron Nashor
- Elemental dragons
- Inhibitors, including first inhibitor and a team count
- Quadra and pentakill events
- Odd/even total kills

Run the verification suite with:

    python3 -m unittest discover -s tests -v
