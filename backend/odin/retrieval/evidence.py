"""Ask-specific retrieval over current, tenant-scoped clauses; no re-index required."""
from __future__ import annotations

import logging
import re
from collections import defaultdict

from odin.db import repo
from odin.retrieval import hybrid
from rank_bm25 import BM25Okapi

log = logging.getLogger(__name__)
_REF = re.compile(r"\b(?:clauses?|sections?)\s+(\d+(?:\.\d+)*)(?:\s*(?:and|,)\s*(\d+(?:\.\d+)*))?", re.I)


def windows(text: str, size: int = 1200, overlap: int = 200):
    """Bounded overlapping spans retain offsets into the original stored clause."""
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            boundary = text.rfind(' ', start + size // 2, end)
            if boundary > start:
                end = boundary
        yield start, end, text[start:end]
        if end == len(text):
            break
        start = max(start + 1, end - overlap)


def retrieve(question: str, contract_ids: list[str], *, limit: int = 10, char_budget: int = 26000) -> tuple[list[dict], list[str]]:
    """Fuse full-text chunk BM25 with existing dense/BM25 ranks, then expand references.

    Lexical reranking is local and deterministic. This is not a neural cross-encoder.
    Dense retrieval failure degrades to full-text search instead of failing the question.
    """
    rows = [r for cid in contract_ids for r in repo.clauses(cid)]
    by_id = {r.id: r for r in rows}
    if not rows:
        return [], ['No searchable clauses are indexed for the selected agreements.']
    chunks = [(r, start, end, body) for r in rows for start, end, body in windows(r.text)]
    tokens = hybrid.tokenize(question)
    query_words = set(tokens)
    scores = defaultdict(float)
    best_span = {}
    if chunks and tokens:
        bm = BM25Okapi([hybrid.tokenize(f'{r.number} {r.heading} {body}') for r, _, _, body in chunks], epsilon=0.5)
        raw = bm.get_scores(tokens)
        # Coverage also works in tiny scopes where BM25 IDFs may be zero/negative.
        ranked = sorted(range(len(chunks)), key=lambda i: (
            -len(query_words & set(hybrid.tokenize(chunks[i][3]))), -float(raw[i])))
        ranked = [i for i in ranked if query_words & set(hybrid.tokenize(chunks[i][3]))]
        for rank, i in enumerate(ranked[:60]):
            row, start, end, _ = chunks[i]
            if row.id not in best_span:
                scores[row.id] += 1 / (60 + rank + 1)
                best_span[row.id] = (start, end)
    warnings = []
    try:
        dense = hybrid.search(question, contract_ids=contract_ids, top_k=32)
        for rank, hit in enumerate(dense):
            if hit.clause_id in by_id:
                scores[hit.clause_id] += 1 / (60 + rank + 1)
    except Exception:  # full-text evidence remains available if embeddings/provider fail
        log.warning('Ask dense retrieval unavailable; using local clause search', exc_info=True)
        warnings.append('Semantic search was unavailable; full-text clause search was used.')
    refs = {v for m in _REF.finditer(question) for v in m.groups() if v}
    for row in rows:
        if row.number in refs:
            scores[row.id] += 1
    order = sorted(scores, key=lambda identity: (-scores[identity], identity))
    if len(contract_ids) > 1 and re.search(r'\b(which|compare|across|agreements|contracts)\b', question, re.I):
        # A comparison must not spend every slot on one agreement.
        selected, represented = [], set()
        target = max(limit, min(20, len(contract_ids)))
        for identity in order:
            cid = by_id[identity].contract_id
            if cid not in represented:
                selected.append(identity)
                represented.add(cid)
                if len(selected) == target:
                    break
        selected += [identity for identity in order if identity not in selected][:max(0, target - len(selected))]
    else:
        selected = order[:limit]
    # Expand explicit same-agreement cross-references; never infer another agreement.
    lookup = {(r.contract_id, r.number): r.id for r in rows}
    for identity in list(selected[:5]):
        row = by_id[identity]
        numbers = {v for m in _REF.finditer(row.text) for v in m.groups() if v}
        for number in sorted(numbers):
            linked = lookup.get((row.contract_id, number))
            if linked and linked not in selected and len(selected) < limit + 4:
                selected.append(linked)
    # Spend context on reference evidence as well as high-ranked parents.
    passages = []
    remaining = char_budget
    for offset, identity in enumerate(selected):
        row = by_id[identity]
        allowance = min(6000, remaining // max(1, len(selected) - offset))
        if allowance < 200:
            break
        body = row.text
        start, end = 0, len(body)
        if len(body) > allowance:
            a, b = best_span.get(identity, (0, min(len(body), 1200)))
            start = max(0, a - max(0, allowance - (b - a)) // 2)
            end = min(len(body), start + allowance)
            start = max(0, end - allowance)
        passages.append({'contract_id': row.contract_id, 'clause_number': row.number,
                         'clause_id': row.id, 'version': row.version, 'page': row.page,
                         'heading': row.heading, 'text': body[start:end],
                         'excerpt_start': start, 'excerpt_end': end,
                         'truncated': start > 0 or end < len(body), 'score': round(scores.get(identity, 0), 5)})
        remaining -= end - start
    return passages, warnings
