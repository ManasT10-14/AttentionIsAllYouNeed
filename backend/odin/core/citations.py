"""Citation guard (NFR2): every quote an agent produces must exist in the stored clause text.

verify() fixes the page/version, corrects a wrong clause number when the quote is found elsewhere
in the same contract, and leaves `verified=False` when the quote is not in the document.
"""
from __future__ import annotations

import threading
from collections import Counter

from rapidfuzz import fuzz

from odin.core.models import Citation
from odin.db import repo

THRESHOLD = 88
_stats = Counter()
_lock = threading.Lock()


def _norm(s: str) -> str:
    return " ".join((s or "").replace("“", '"').replace("”", '"').replace("’", "'").split()).lower()


def verify(c: Citation) -> Citation:
    rows = repo.clauses(c.contract_id, c.version) if c.version else repo.clauses(c.contract_id)
    if not rows:
        return _count(c.model_copy(update={"verified": False}))
    q = _norm(c.quote)
    num = (c.clause_number or "").strip().rstrip(".")
    target = next((r for r in rows if r.number == num), None)
    if target and (not q or fuzz.partial_ratio(q, _norm(target.text)) >= THRESHOLD):
        return _count(c.model_copy(update={"verified": bool(q), "page": target.page, "version": target.version,
                                           "clause_number": target.number}))
    if q:
        best = max(rows, key=lambda r: fuzz.partial_ratio(q, _norm(r.text)))
        if fuzz.partial_ratio(q, _norm(best.text)) >= THRESHOLD:
            return _count(c.model_copy(update={"verified": True, "page": best.page, "version": best.version,
                                               "clause_number": best.number}))
    return _count(c.model_copy(update={"verified": False, "page": target.page if target else None,
                                       "version": target.version if target else None}))


def _count(c: Citation) -> Citation:
    with _lock:
        _stats["checked"] += 1
        _stats["verified" if c.verified else "blocked"] += 1
    return c


def stats() -> dict:
    with _lock:
        return dict(_stats)


def verify_all(cits: list[Citation]) -> list[Citation]:
    return [verify(c) for c in cits]


def verified_ratio(cits: list[Citation]) -> float:
    return sum(c.verified for c in cits) / len(cits) if cits else 0.0
