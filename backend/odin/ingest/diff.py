"""Clause-level diff between two versions of a contract (plan §6)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from rapidfuzz import fuzz

from odin.db import repo


@dataclass
class ClauseChange:
    number: str
    change: str                 # added | removed | modified | renumbered
    old_number: str | None = None
    before: str = ""
    after: str = ""
    similarity: float = 100.0


@dataclass
class ClauseDiff:
    contract_id: str
    from_version: int
    to_version: int
    changes: list[ClauseChange] = field(default_factory=list)

    @property
    def touched_numbers(self) -> list[str]:
        return [c.number for c in self.changes if c.change in ("added", "modified", "renumbered")]

    def as_dict(self) -> dict:
        return {"contract_id": self.contract_id, "from_version": self.from_version, "to_version": self.to_version,
                "changes": [asdict(c) for c in self.changes]}


def diff_versions(contract_id: str, v_from: int, v_to: int, company_id: str | None = None) -> ClauseDiff:
    old = {c.number: c for c in repo.clauses(contract_id, v_from, current_only=False, company_id=company_id)}
    new = {c.number: c for c in repo.clauses(contract_id, v_to, current_only=False, company_id=company_id)}
    out = ClauseDiff(contract_id, v_from, v_to)
    unmatched_old = set(old) - set(new)
    for num, c in new.items():
        if num in old:
            sim = fuzz.ratio(old[num].text, c.text)
            if sim < 99.5:
                out.changes.append(ClauseChange(num, "modified", before=old[num].text, after=c.text, similarity=sim))
            continue
        # same text under a new number? (renumbered)
        best = max(unmatched_old, key=lambda o: fuzz.ratio(old[o].text, c.text), default=None)
        if best and fuzz.ratio(old[best].text, c.text) > 90:
            unmatched_old.discard(best)
            out.changes.append(ClauseChange(num, "renumbered", old_number=best, before=old[best].text, after=c.text,
                                            similarity=fuzz.ratio(old[best].text, c.text)))
        else:
            out.changes.append(ClauseChange(num, "added", after=c.text, similarity=0))
    for num in sorted(unmatched_old):
        out.changes.append(ClauseChange(num, "removed", before=old[num].text, similarity=0))
    return out
