from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Intent:
    kind: str
    game_number: int | None = None
    question: str = ""


@dataclass
class Answer:
    result: str
    series: str | None = None
    game: str | None = None
    evidence: list[str] = field(default_factory=list)
    source: str | None = None
    confidence: str = "LOW"
    note: str | None = None

    def render(self) -> str:
        output = [f"Result: {self.result}"]
        if self.series:
            output.insert(0, f"Matched Series: {self.series}")
        if self.game:
            output.insert(1 if self.series else 0, f"Matched Game: {self.game}")
        if self.evidence:
            output += ["", "Evidence:", *[f"- {x}" for x in self.evidence]]
        if self.note:
            output += ["", f"Note: {self.note}"]
        if self.source:
            output += ["", f"Source: {self.source}"]
        output += [f"Confidence: {self.confidence}"]
        return "\n".join(output)

    def as_dict(self) -> dict[str, Any]:
        return {"result": self.result, "matched_series": self.series, "matched_game": self.game, "evidence": self.evidence, "source": self.source, "confidence": self.confidence, "note": self.note}
