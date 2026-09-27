from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Fact:
    value: Any
    source: str

    @property
    def known(self) -> bool:
        return self.value not in (None, "", []) and bool(self.source.strip())


class CandidateProfile:
    """A fact store that never turns an unknown into an inferred answer."""

    def __init__(self, facts: dict[str, Fact]) -> None:
        self.facts = facts

    @classmethod
    def load(cls, path: str | Path) -> "CandidateProfile":
        raw = json.loads(Path(path).read_text())
        facts = {
            key: Fact(value=item.get("value", ""), source=item.get("source", ""))
            for key, item in raw.get("facts", {}).items()
        }
        return cls(facts)

    def answer(self, key: str) -> tuple[Any, dict[str, str]] | None:
        fact = self.facts.get(key)
        if not fact or not fact.known:
            return None
        return fact.value, {"fact": key, "source": fact.source}

    def require(self, key: str) -> tuple[Any, dict[str, str]]:
        answer = self.answer(key)
        if answer is None:
            raise UnknownFactError(f"No sourced value for {key!r}; human input required")
        return answer


class UnknownFactError(ValueError):
    pass
