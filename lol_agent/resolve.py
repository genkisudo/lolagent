from __future__ import annotations

from .db import connect
from .models import Answer, Intent


def answer(db_path: str, match: str, intent: Intent, date: str | None = None, competition: str | None = None) -> Answer:
    con = connect(db_path)
    query = "SELECT * FROM series WHERE (lower(team_a || ' vs ' || team_b) = lower(?) OR lower(team_b || ' vs ' || team_a) = lower(?))"
    args = [match, match]
    if date:
        query += " AND match_date = ?"; args.append(date)
    if competition:
        query += " AND lower(competition) = lower(?)"; args.append(competition)
    matches = con.execute(query, args).fetchall()
    if not matches:
        return Answer("UNRESOLVED", note="No completed series exactly matched the supplied teams.")
    if len(matches) > 1:
        return Answer("AMBIGUOUS", note="More than one series matches; add match date or competition.")
    sid, team_a, team_b, _, _, series_winner, source, _ = matches[0]
    title = f"{team_a} vs {team_b}"
    if intent.kind == "unknown":
        return Answer("UNRESOLVED", title, source=source, note="The question is outside the supported deterministic intents.")
    games = con.execute("SELECT * FROM games WHERE series_id=? AND completed=true ORDER BY game_number", [sid]).fetchall()
    if intent.kind in {"series_winner", "series_score"}:
        if not games:
            return Answer("UNKNOWN", title, source=source, note="No completed games are stored.")
        if intent.kind == "series_score":
            aw, bw = sum(g[3] == team_a for g in games), sum(g[3] == team_b for g in games)
            return Answer(f"{aw}-{bw}", title, evidence=[f"Completed games: {len(games)}"], source=source, confidence="HIGH")
        wording = intent.question.lower()
        target = team_a if team_a.lower() in wording or "team a" in wording else team_b if team_b.lower() in wording or "team b" in wording else None
        result = "YES" if target == series_winner else "NO" if target and series_winner else "TEAM_A" if series_winner == team_a else "TEAM_B" if series_winner == team_b else "UNKNOWN"
        return Answer(result, title, evidence=[f"Series winner: {series_winner}"] if series_winner else [], source=source, confidence="HIGH" if series_winner else "LOW")
    chosen = [game for game in games if intent.game_number is None or game[2] == intent.game_number]
    if intent.game_number is None and len(games) != 1:
        return Answer("AMBIGUOUS", title, source=source, note="This series has multiple games; specify a game number or include one in the question.")
    if not chosen:
        return Answer("UNRESOLVED", title, source=source, note="The requested game is not stored as completed.")
    game = chosen[0]
    events = con.execute("SELECT timestamp_display, team, player, event_type, lane, objective_type, raw_text FROM events WHERE game_id=? ORDER BY timestamp_seconds", [game[0]]).fetchall()
    return resolve_game(intent, team_a, team_b, game, events, title, source)


def resolve_game(intent, team_a, team_b, game, events, title, source):
    label = f"Game {game[2]}"
    timeline_complete = bool(game[10])
    def select(kind, test=lambda event: True): return [event for event in events if event[3] == kind and test(event)]
    def describe(event): return f"{event[1]} — {event[5] or event[3].replace('_', ' ').title()} {event[0] or 'time unknown'}" + (f" — {event[2]}" if event[2] else "")
    def asked_team():
        wording = intent.question.lower()
        if team_a.lower() in wording or "team a" in wording: return team_a
        if team_b.lower() in wording or "team b" in wording: return team_b
        return None
    def team_yes_no(found):
        target = asked_team()
        if not target: return None
        return "YES" if any(event[1] == target for event in found) else "NO"
    if intent.kind == "game_winner":
        target = asked_team()
        result = "YES" if target == game[3] else "NO" if target and game[3] else "TEAM_A" if game[3] == team_a else "TEAM_B" if game[3] == team_b else "UNKNOWN"
        return Answer(result, title, label, [f"Winner: {game[3]}"] if game[3] else [], source, "HIGH" if game[3] else "LOW")
    if intent.kind == "kill_parity":
        if game[4] is None or game[5] is None:
            return Answer("UNKNOWN", title, label, source=source, note="Final team kills are unavailable.")
        total = game[4] + game[5]
        return Answer("EVEN" if total % 2 == 0 else "ODD", title, label, [f"{team_a}: {game[4]} kills; {team_b}: {game[5]} kills; total: {total}"], source, "HIGH")
    if intent.kind == "first_blood":
        found = select("FIRST_BLOOD")
        if not found: return Answer("UNKNOWN", title, label, source=source, note="No explicit First Blood event is stored.")
        target = asked_team()
        result = "YES" if target == found[0][1] else "NO" if target else "TEAM_A" if found[0][1] == team_a else "TEAM_B" if found[0][1] == team_b else "UNKNOWN"
        return Answer(result, title, label, [describe(found[0])], source, "HIGH")
    if intent.kind in {"baron_both", "baron_team"}: found = select("BARON_SLAIN")
    elif intent.kind in {"dragon_both", "dragon_team"}: found = select("DRAGON_SLAIN", lambda e: e[5] in {"INFERNAL", "MOUNTAIN", "OCEAN", "HEXTECH", "CHEMTECH", "CLOUD"})
    elif intent.kind.startswith("inhibitor"): found = select("INHIBITOR_DESTROYED")
    elif intent.kind in {"quadra", "penta"}: found = select("QUADRA_KILL" if intent.kind == "quadra" else "PENTA_KILL")
    else: return Answer("UNRESOLVED", title, label, source=source)
    if intent.kind == "inhibitor_first":
        if not found: return Answer("UNKNOWN", title, label, source=source, note="No explicit inhibitor events are stored.")
        return Answer("TEAM_A" if found[0][1] == team_a else "TEAM_B" if found[0][1] == team_b else "UNKNOWN", title, label, [describe(found[0])], source, "HIGH")
    if intent.kind == "inhibitor_count":
        target = asked_team()
        if not target:
            return Answer("UNRESOLVED", title, label, source=source, note="Specify Team A, Team B, or a participating team for an inhibitor count.")
        if not timeline_complete:
            return Answer("UNKNOWN", title, label, source=source, note="A complete timeline is required for a structure count.")
        return Answer(str(sum(event[1] == target for event in found)), title, label, [describe(event) for event in found if event[1] == target], source, "HIGH")
    if intent.kind in {"quadra", "penta"}:
        return Answer("YES" if found else "UNKNOWN", title, label, [describe(e) for e in found], source, "HIGH" if found else "LOW", None if found else f"No explicit {intent.kind} evidence is stored; final KDA is not used.")
    if not found:
        return Answer("UNKNOWN", title, label, source=source, note="No relevant explicit objective events are stored; absence is not treated as a negative result.")
    if intent.kind.endswith("both"):
        both = {team_a, team_b}.issubset({e[1] for e in found})
        if not both and not timeline_complete:
            return Answer("UNKNOWN", title, label, [describe(e) for e in found], source, "LOW", "The stored timeline is not marked complete, so it cannot prove a negative.")
        return Answer("YES" if both else "NO", title, label, [describe(e) for e in found], source, "HIGH")
    targeted = team_yes_no(found)
    if targeted == "NO" and not timeline_complete:
        return Answer("UNKNOWN", title, label, [describe(e) for e in found], source, "LOW", "The stored timeline is not marked complete, so it cannot prove a negative.")
    if targeted:
        return Answer(targeted, title, label, [describe(e) for e in found], source, "HIGH")
    return Answer("UNRESOLVED", title, label, source=source, note="Team-specific wording needs an explicit team resolver.")
