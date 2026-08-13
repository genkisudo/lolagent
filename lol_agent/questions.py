from __future__ import annotations

import re
from .models import Intent


def parse_question(question: str, game_number: int | None = None) -> Intent:
    text = " ".join(question.lower().split())
    embedded = re.search(r"\bgame\s*(\d+)\b", text)
    game = game_number or (int(embedded.group(1)) if embedded else None)
    if "series score" in text or "score of the series" in text:
        return Intent("series_score", game, question)
    if "first blood" in text:
        return Intent("first_blood", game, question)
    if "baron" in text:
        return Intent("baron_both" if "both" in text else "baron_team", game, question)
    if "dragon" in text:
        return Intent("dragon_both" if "both" in text else "dragon_team", game, question)
    if "inhib" in text:
        return Intent("inhibitor_first" if "first" in text else "inhibitor_count" if "how many" in text else "inhibitor_both" if "both" in text else "inhibitor_team", game, question)
    if "quadra" in text:
        return Intent("quadra", game, question)
    if "penta" in text:
        return Intent("penta", game, question)
    if "odd" in text or "even" in text:
        return Intent("kill_parity", game, question)
    if "who won" in text or re.search(r"\bdid\s+.+\s+win\b", text):
        return Intent("series_winner" if "series" in text else "game_winner", game, question)
    return Intent("unknown", game, question)
