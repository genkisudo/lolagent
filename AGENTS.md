# Repository Guidelines

## Project Structure & Module Organization

- `lol_agent/` contains the application package. `cli.py` defines the terminal interface; `ingest.py` imports normalized match snapshots; `db.py` owns DuckDB setup; `questions.py` parses supported prompts; and `resolve.py` answers them from stored evidence.
- `tests/` contains the `unittest` suite. Add focused regression coverage in `tests/test_*.py` for every behavior change.
- `examples/` holds committed, runnable JSON fixtures. Use these for reproducible tests and demos.
- `data/raw/` and `data/db/` are generated local state. Do not commit source snapshots or `.duckdb` databases.

## Build, Test, and Development Commands

Use Python 3.10+ and install dependencies with:

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
```

Initialize and exercise the CLI locally:

```bash
python3 -m lol_agent init
python3 -m lol_agent ingest-json examples/t1_gen_g_game2.json
python3 -m lol_agent answer --match 'T1 vs Gen.G' --game 2 --question 'Who won?'
```

Pass `--db /tmp/lol_agent.duckdb` before the subcommand to isolate a local run. Use `ingest-json --force` only when intentionally reprocessing an existing snapshot.

## Coding Style & Naming Conventions

Follow the existing standard-library Python style: four-space indentation, `from __future__ import annotations`, type hints for public functions, and short, direct doc-free functions where names make intent clear. Use `snake_case` for modules, functions, variables, and test methods; `PascalCase` for classes and dataclasses. Keep evidence resolution deterministic—never infer outcomes from player names or incomplete timelines.

## Testing Guidelines

Use `unittest` and name tests `test_<expected_behavior>`. Build tests around temporary DuckDB files and committed fixtures, as `AgentTests.setUp` does. Cover positive, negative, ambiguous, and unknown outcomes; importantly, a negative objective result requires a complete timeline. Run the full discovery command before opening a pull request.

## Commit & Pull Request Guidelines

The available Git history uses a short imperative subject (`first commit`). Continue with concise, action-led subjects such as `Handle missing timeline evidence`. Keep commits focused. Pull requests should explain the user-visible behavior change, identify updated fixtures or schema implications, link relevant issues, and include CLI output when it clarifies changed answers. Confirm tests pass and do not include generated `data/` contents.
