Build a reliable **terminal-based League of Legends esports results and evidence agent**.

Its job is to answer factual questions about completed professional LoL games using structured match data and, when necessary, VOD evidence.

Do **not** build predictions, probabilities, betting advice, dashboards, or Polymarket integrations.

# 1. Inputs

Minimum:

```text
match
question
```

Optional:

```text
game number
match date
competition
market-specific rules
notes
```

Examples:

```text
Match: T1 vs Gen.G
Question: Both Teams Slay a Dragon?
```

```text
Match: T1 vs Gen.G
Game: 2
Question: Any Player Quadra Kill?
```

The user will **not always know the game number**.

If the question contains a game number, extract it automatically.

If not:

1. identify the series
2. enumerate its games
3. use context, notes, timing, and available evidence to identify the relevant game
4. resolve only when identification is reliable

If multiple games remain plausible and could produce different answers:

```text
Result: AMBIGUOUS
```

Never silently choose a game.

# 2. Outputs

Return:

```text
result
matched series
matched game, if applicable
evidence
source
confidence
```

Possible result types:

```text
YES
NO
ODD
EVEN
TEAM_A
TEAM_B
UNKNOWN
UNRESOLVED
AMBIGUOUS
```

Missing data or parser failure must never automatically become `NO`.

Example:

```text
Match: T1 vs Gen.G
Matched Game: Game 2

Question:
Both Teams Slay an Elemental Dragon?

Result:
YES

Evidence:
T1 — Infernal Dragon 06:14
GEN — Mountain Dragon 11:42

Excluded:
GEN — Elder Dragon 31:08

Source:
Gol.gg

Confidence:
HIGH
```

# 3. Sources

## Primary: Gol.gg

https://gol.gg/esports/home/

Use for:

* series and game results
* kills
* First Blood
* dragons
* Baron Nashor
* towers
* inhibitors
* player stats
* game duration
* Timeline / Plays events
* multi-kill evidence where available

## Secondary: LoL Esports

https://lolesports.com/

Use for:

* schedules
* team and competition identity
* series matching
* result cross-checking where available

## Fallback: VOD

If structured sources cannot establish a fact reliably, locate and inspect an official or credible VOD.

Twitch will often be the main VOD source.

# 4. Supported Competitions

Initially support:

```text
CBLOL
EBL
Hitpoint Masters
LCK
LCK Challengers
LCP
LCS
LEC
LES
LFL
LPL
LPLOL
LRN
LRS
NACL
Prime League 1st Division
Road of Legends
TCL
```

Do not hardcode the system so only these leagues can ever work.

# 5. Historical Scope and Storage

Maintain approximately the latest **30 days**.

Store:

```text
series
games
players
game stats
timeline events
source snapshots
VOD metadata
evidence
```

Use DuckDB.

Suggested:

```text
data/
├── raw/
│   ├── gol/
│   ├── lolesports/
│   └── twitch/
└── db/
    └── lol_agent.duckdb
```

Always save raw responses before parsing so historical data can be reprocessed after parser changes.

# 6. Gol.gg Timeline Is Critical

Treat the Gol.gg **Timeline** as first-class evidence.

Example:

```text
27:20
Fengu
INHIB
MID
```

Normalize to:

```json
{
  "timestamp": "27:20",
  "team": "Dominion Goblins",
  "player": "Fengu",
  "event_type": "INHIBITOR_DESTROYED",
  "lane": "MID",
  "raw_event": "INHIB MID"
}
```

Correct team attribution from the Gol.gg timeline side/column is critical.

Do not assume every structure event has a meaningful player.

Preserve raw event data.

Suggested event schema:

```text
event_id
game_id
timestamp_seconds
timestamp_display
team_id
player_id
event_type
target_team_id
target_player_id
lane
structure
objective_type
raw_text
raw_html
source_url
parser_version
```

Event types should include:

```text
PLAYER_KILL
FIRST_BLOOD
TOWER_DESTROYED
INHIBITOR_DESTROYED
DRAGON_SLAIN
BARON_SLAIN
HERALD_SLAIN
QUADRA_KILL
PENTA_KILL
NEXUS_DESTROYED
OTHER
```

# 7. Resolution Architecture

Use:

```text
question
↓
QuestionParser
↓
QuestionIntent
↓
SeriesMatcher / GameMatcher
↓
deterministic resolver
↓
evidence
↓
answer
```

The LLM may interpret natural language.

The factual result must be determined by code operating on structured evidence.

Implement:

```text
GameWinnerResolver
SeriesWinnerResolver
SeriesScoreResolver
FirstBloodResolver
BaronResolver
DragonResolver
InhibitorResolver
MultiKillResolver
KillParityResolver
```

# 8. Game and Series Results

Support:

```text
Who won?
Who won Game 2?
Did Team A win?
Who won the series?
What was the series score?
```

Use explicit completed-game results.

# 9. First Blood

Support:

```text
Who got First Blood?
Did Team A get First Blood?
```

Store:

```text
team
player
timestamp
```

Use explicit evidence, not final kill totals.

# 10. Baron Nashor

For:

```text
Both Teams Slay Baron Nashor?
```

evaluate:

```text
team_a_barons >= 1
AND
team_b_barons >= 1
```

Store individual Baron events when available.

Do not confuse Baron with Rift Herald or other objectives.

# 11. Elemental Dragons

For questions such as:

```text
Both Teams Slay a Dragon?
```

only these count:

```text
INFERNAL
MOUNTAIN
OCEAN
HEXTECH
CHEMTECH
CLOUD
```

**Elder Dragon does not count.**

After Dragon Soul is claimed, subsequent Elder Dragon kills must remain separate.

Store:

```text
timestamp
team
dragon_type
counts_as_elemental_dragon
```

Example:

```json
{
  "team": "Team B",
  "dragon_type": "ELDER",
  "counts_as_elemental_dragon": false
}
```

Resolve:

```text
team_a_elemental_dragons >= 1
AND
team_b_elemental_dragons >= 1
```

Example:

```text
Team A:
Infernal Dragon

Team B:
Elder Dragon

Result:
NO
```

Never use a generic dragon total unless Elder has explicitly been excluded.

# 12. Inhibitors

Support:

```text
Did Team A destroy an inhibitor?
Did both teams destroy an inhibitor?
Which team destroyed the first inhibitor?
How many inhibitors did Team A destroy?
```

Prefer explicit Gol.gg `INHIB` timeline events.

For:

```text
Both Teams Destroy an Inhibitor?
```

evaluate:

```text
team_a_inhibitors_destroyed >= 1
AND
team_b_inhibitors_destroyed >= 1
```

Do not infer inhibitor destruction from:

```text
game winner
Nexus destruction
tower count
gold
game duration
```

If the Timeline cannot establish the result, escalate to VOD evidence when possible.

# 13. Quadra / Penta Kill

Support:

```text
Any Player Quadra Kill?
Any Player Penta Kill?
```

Final kill totals are not sufficient.

A player finishing:

```text
8/2/6
```

does not prove a Quadra Kill.

Evidence priority:

```text
explicit multi-kill event
→ reliable timeline/play data
→ VOD verification
→ UNKNOWN
```

Store:

```text
player
team
timestamp
multikill_type
source
```

Do not globally assume a Pentakill also satisfies a Quadra question. Market-specific rules may override this later.

# 14. Odd / Even Total Kills

Calculate deterministically:

```python
total_kills = team_a_kills + team_b_kills
result = "EVEN" if total_kills % 2 == 0 else "ODD"
```

Example:

```text
GOB: 18
Bubiki: 17
Total: 35

Result: ODD
```

Do not use the LLM for arithmetic.

# 15. Match and Game Identification

Create:

```text
SeriesMatcher
GameMatcher
```

Match using:

```text
teams
team aliases
competition
date
game order
game duration
winner
question context
notes
```

Support aliases such as:

```text
GOB
Dominion Goblins
```

If game number is supplied, verify the series and use it.

If not:

```text
identify series
→ enumerate games
→ use available context/evidence
→ select only if uniquely supported
```

If uncertain, return `AMBIGUOUS`.

Never choose the first candidate arbitrarily.

# 16. Twitch / VOD Fallback

Implement:

```text
VODLocator
VODInspector
```

The agent may need Twitch APIs/endpoints to locate the correct broadcast/VOD.

Credentials must come from environment variables:

```text
TWITCH_CLIENT_ID
TWITCH_CLIENT_SECRET
```

Never commit credentials.

Store candidate metadata:

```text
vod_id
platform
channel
title
created_at
duration
url
match_candidate_score
```

Verify VOD identity using:

```text
competition
teams
date
broadcast timing
series/game order
```

Do not assume the first search result is correct.

# 17. VOD Inspection

Use VOD inspection when structured evidence is insufficient.

Typical cases:

```text
Quadra / Penta verification
missing inhibitor evidence
missing timeline events
source disagreement
uncertain game identification
```

Do not inspect an entire multi-hour broadcast unless unavoidable.

Narrow the relevant section using:

```text
series start
game order
game duration
Gol.gg timestamps
known event time
broadcast breaks
```

Example:

```text
Gol.gg game time:
27:20

Estimated VOD window:
02:14:00–02:17:00
```

Inspect only that range when possible.

Twitch API metadata is for locating VODs. Actual event verification must come from accessible video content.

Store:

```text
vod_id
vod_url
vod_timestamp_start
vod_timestamp_end
game_clock
observed_event
team
player
confidence
notes
```

# 18. Optional Market Rules

Rules may be supplied per question:

```bash
lol-agent ask \
  "T1 vs Gen.G" \
  --rules rules.txt \
  "Any Player Quadra Kill?"
```

Store:

```text
original_question
original_rules
parsed_condition
```

Keep the original rule text unchanged and authoritative.

Do not convert one market's special rule into global behavior.

# 19. Evidence Hierarchy

General priority:

```text
1. Explicit Gol.gg structured evidence
2. Other relevant Gol.gg data
3. LoL Esports verification
4. Official/credible VOD evidence
5. Other credible source
6. UNKNOWN
```

Question-specific priority may differ.

Example for inhibitors:

```text
Gol.gg Timeline
→ VOD
→ UNKNOWN
```

Never silently hide source conflicts.

If strong sources disagree:

```text
Result: AMBIGUOUS
Source conflict detected.
```

Preserve both pieces of evidence.

# 20. Confidence

Confidence means **evidence quality**, not probability.

Use:

```text
HIGH
MEDIUM
LOW
```

Example HIGH:

```text
exact match/game identified
+
required page parsed successfully
+
explicit event/stat found
```

or:

```text
exact VOD identified
+
event verified at a precise timestamp
```

If evidence is insufficient, return `UNKNOWN`.

# 21. Database

Use DuckDB.

Main tables:

```text
competitions
teams
team_aliases
players
series
games
player_game_stats
timeline_events
source_snapshots
vods
vod_match_candidates
vod_evidence
questions
resolutions
```

# 22. Parser Reliability

Keep collection and parsing separate:

```text
collectors/
parsers/
```

Save representative source fixtures.

Tests must cover:

```text
series matching
game matching
missing game number
team aliases
winner
kills
First Blood
Baron
elemental dragons
Elder exclusion
INHIB parsing
inhibitor team attribution
Quadra Kill
Penta Kill
Odd/Even calculation
VOD-to-match matching
```

Critical invariants:

```text
PARSER FAILURE != NO
MISSING DATA != NO
NO EVENTS PARSED != NO EVENTS OCCURRED
```

Validate pages before trusting parsed results.

# 23. CLI

Support approximately:

```bash
lol-agent sync --days 30

lol-agent match "T1 vs Gen.G"

lol-agent ask \
  "T1 vs Gen.G" \
  "Both Teams Slay a Dragon?"

lol-agent ask \
  "T1 vs Gen.G" \
  --game 2 \
  "Both Teams Slay a Dragon?"

lol-agent ask \
  "T1 vs Gen.G" \
  --rules rules.txt \
  "Any Player Quadra Kill?"

lol-agent evidence \
  "T1 vs Gen.G" \
  "Did Both Teams Destroy an Inhibitor?"

lol-agent vod "T1 vs Gen.G"

lol-agent doctor
```

Support:

```text
--json
--verbose
```

Keep default output concise.

# 24. Technology

Use:

```text
Python 3.12+
httpx
BeautifulSoup / lxml
Pydantic
DuckDB
Typer
pytest
```

Add Twitch API/client support.

Use browser/video automation only when necessary for VOD inspection.

Respect authentication, access controls, and rate limits.

Implement:

```text
timeouts
retries
caching
rate limiting
structured logging
```

# 25. Repository Structure

```text
lol-market-agent/
├── README.md
├── pyproject.toml
├── .env.example
├── src/lol_agent/
│   ├── cli.py
│   ├── config.py
│   ├── models/
│   ├── db/
│   ├── collectors/
│   │   ├── gol.py
│   │   ├── lolesports.py
│   │   └── twitch.py
│   ├── parsers/
│   │   ├── gol_summary.py
│   │   ├── gol_stats.py
│   │   └── gol_timeline.py
│   ├── matching/
│   │   ├── series.py
│   │   ├── games.py
│   │   └── vod.py
│   ├── questions/
│   ├── resolvers/
│   ├── evidence/
│   ├── vod/
│   │   ├── locator.py
│   │   ├── inspector.py
│   │   └── timestamp.py
│   └── services/
├── tests/
│   ├── fixtures/
│   ├── parsers/
│   ├── matching/
│   └── resolvers/
└── data/
    ├── raw/
    └── db/
```

# 26. Build Order

## Phase 1 — Gol.gg vertical slice

Using one known completed match:

```text
find series
→ enumerate games
→ parse summary
→ parse timeline
→ normalize
→ save
```

Manually verify against Gol.gg.

## Phase 2 — Core resolvers

Implement:

```text
Game Winner
Series Score
First Blood
Odd/Even Kills
Both Teams Baron
Both Teams Elemental Dragon
Both Teams Inhibitor
```

## Phase 3 — VOD fallback

Implement:

```text
Twitch authentication
→ VOD discovery
→ VOD/match matching
→ timestamp narrowing
→ evidence capture
```

Test against a known accessible VOD.

## Phase 4 — Multi-kills

Implement:

```text
Quadra Kill
Penta Kill
```

Use VOD fallback when structured evidence is insufficient.

## Phase 5 — Scale

Run across the last 30 days.

Track:

```text
coverage
parser failures
missing source data
VOD availability
ambiguous matches
unresolved questions
```

Do not hide failures.

# 27. Definition of Done

V1 is complete when I can provide as little as:

```text
match
question
```

and the agent can:

1. identify the correct series
2. identify the relevant game when possible without requiring a game number
3. collect and normalize Gol.gg evidence
4. parse Timeline events correctly
5. resolve supported questions deterministically
6. exclude Elder from elemental-dragon markets
7. detect inhibitor destruction from explicit `INHIB` events
8. locate and inspect VODs when structured evidence is insufficient
9. return evidence and confidence
10. return `AMBIGUOUS` or `UNKNOWN` instead of guessing

Priority:

1. Correct series/game identification
2. Gol.gg parser reliability
3. Timeline and `INHIB` parsing
4. Elemental-dragon logic
5. Deterministic resolvers
6. VOD fallback
7. Evidence traceability
8. Safe missing/conflicting-data handling
9. Easy addition of new question types

Build the **data and evidence engine first**. Use VOD inspection only when structured sources cannot establish the fact reliably.
