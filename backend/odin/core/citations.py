"""Citation guard (NFR2): every quote an agent produces must exist in the stored clause text.

verify() fixes the page/version, corrects a wrong clause number when the quote is found elsewhere
in the same contract, and leaves `verified=False` when the quote is not in the document.
"""
from __future__ import annotations

import threading
import re
from collections import Counter

from rapidfuzz import fuzz

from odin.core.models import Citation
from odin.db import repo

THRESHOLD = 88
_stats = Counter()
_lock = threading.Lock()


def _norm(s: str) -> str:
    return " ".join((s or "").split()).lower()


def canonical_span(quote: str, text: str) -> str | None:
    """Recover only a unique whitespace-equivalent span; never repair words or numbers.

    Models often reflow a PDF/TXT line break. Return the original source bytes as
    the citation instead of accepting the model's reflowed quote as verbatim.
    Ambiguous repeated matches and changed words remain unverified.
    """
    if not quote or not quote.strip():
        return None
    if quote in text:
        return quote
    tokens = re.findall(r"\S+", quote)
    if not tokens:
        return None
    pattern = r"\s+".join(re.escape(t) for t in tokens)
    matches = list(re.finditer(pattern, text))
    return matches[0].group() if len(matches) == 1 else None


def verify(c: Citation) -> Citation:
    doc_id = c.contract_id.strip()
    if doc_id.lower().endswith((".txt", ".pdf")):
        doc_id = doc_id.rsplit(".", 1)[0]
    rows = repo.clauses(doc_id, c.version) if c.version else repo.clauses(doc_id)
    if not rows:
        return _count(c.model_copy(update={"verified": False}))
    q = _norm(c.quote)
    num = (c.clause_number or "").strip().rstrip(".")
    target = next((r for r in rows if r.number == num), None)
    ordered = ([target] if target else []) + [r for r in rows if r is not target]
    for row in ordered:
        if getattr(row, "ref", None):
            exact = canonical_span(c.quote, row.text)
            if exact is None:
                continue
        else:
            if not q or fuzz.partial_ratio(q, _norm(row.text)) < THRESHOLD:
                continue
            exact = c.quote
        return _count(c.model_copy(update={"verified": True, "contract_id": row.contract_id,
                                           "quote": exact, "page": row.page, "version": row.version,
                                           "clause_number": row.number,
                                           "ref": getattr(row, "ref", None) or c.ref}))
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
