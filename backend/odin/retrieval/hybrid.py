"""Hybrid clause retrieval: dense (bge-small via fastembed, pgvector) + BM25 (legal-aware tokens)
fused with Reciprocal Rank Fusion. Reranker slot reserved (pass-through) — corpus is < 20 contracts.
"""
from __future__ import annotations

import re
import math
import threading
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from rank_bm25 import BM25Okapi
from sqlalchemy import select

from odin.core.config import odin_config
from odin.core.context import maybe_current
from odin.core.hooks import HOOKS
from odin.core.telemetry import traced
from odin.db.session import db
from odin.db.tables import ClauseRow


# ───────────────────────────── embeddings ─────────────────────────────
@lru_cache
def _embedder():
    from fastembed import TextEmbedding
    return TextEmbedding(model_name=odin_config()["retrieval"]["embed_model"])


def chunk_header(contract_id: str, version: int, number: str, heading: str) -> str:
    return f"[{contract_id} v{version} | {heading} > {number}]".replace(" |  >", " |")


def embed_passages(texts: list[str]) -> list[list[float]]:
    return [v.tolist() for v in _embedder().passage_embed(texts)]


def embed_query(q: str) -> list[float]:
    return next(iter(_embedder().query_embed(q))).tolist()


# ───────────────────────────── BM25 ─────────────────────────────
# keep clause refs ("7.2"), money ("5,00,000"), percents and defined terms as whole tokens
_TOK = re.compile(r"\d+(?:[.,]\d+)*%?|[a-z][a-z0-9\-']*", re.I)
_STOP = set("the a an of to and or in on for by with is are be shall will may any this that such as at from "
            "its it their which other each all".split())


def tokenize(s: str) -> list[str]:
    return [t.lower() for t in _TOK.findall(s) if t.lower() not in _STOP]


class _BM25Cache:
    """Per-company BM25 index over current clauses; rebuilt when the clause set changes."""

    def __init__(self):
        self._lock = threading.Lock()
        self._idx: dict[str, tuple[frozenset, BM25Okapi, list[str]]] = {}

    def get(self, company_id: str, rows: list[ClauseRow]):
        key = frozenset(r.id for r in rows)
        with self._lock:
            hit = self._idx.get(company_id)
            if hit and hit[0] == key:
                return hit[1], hit[2]
            ids = [r.id for r in rows]
            bm = BM25Okapi([tokenize(f"{r.number} {r.heading} {r.text}") for r in rows]) if rows else None
            self._idx[company_id] = (key, bm, ids)
            return bm, ids


_BM25 = _BM25Cache()


def memory_dense_ids(by_id, query_vector, limit):
    """Cosine-ranking backend for isolated SQLite evaluation; PostgreSQL stays default."""
    qnorm = math.sqrt(math.fsum(float(x) ** 2 for x in query_vector))
    if not qnorm:
        raise ValueError("Dense query vector must be nonzero")
    scored = []
    for identity, row in by_id.items():
        vector = row.embedding
        if vector is None:
            continue
        if len(vector) != len(query_vector):
            raise ValueError("Dense passage/query dimensions differ")
        norm = math.sqrt(math.fsum(float(x) ** 2 for x in vector))
        if norm:
            score = math.fsum(float(x) * float(y) for x, y in zip(vector, query_vector)) / (norm * qnorm)
            scored.append((-score, identity))
    return [identity for _, identity in sorted(scored)[:limit]]


# ───────────────────────────── reranker slot ─────────────────────────────
class Reranker(Protocol):
    def rerank(self, query: str, hits: list["Hit"]) -> list["Hit"]: ...


class PassThrough:
    def rerank(self, query, hits):
        return hits


def reranker() -> Reranker:
    name = odin_config()["retrieval"].get("reranker", "none")
    if name in (None, "none"):
        return PassThrough()
    raise NotImplementedError(f"reranker '{name}' reserved for later — set retrieval.reranker: none")


# ───────────────────────────── search ─────────────────────────────
@dataclass
class Hit:
    clause_id: str
    contract_id: str
    version: int
    number: str
    heading: str
    clause_type: str
    text: str
    page: int
    score: float
    dense_rank: int | None = None
    sparse_rank: int | None = None
    company_id: str | None = None

    def as_dict(self, max_chars: int | None = 900) -> dict:
        return {"contract_id": self.contract_id, "clause_number": self.number, "heading": self.heading,
                "clause_type": self.clause_type, "page": self.page, "version": self.version,
                "clause_id": self.clause_id, "company_id": self.company_id,
                "score": round(self.score, 4), "text": self.text[:max_chars]}


@traced("odin:retrieval", "retriever")
def search(query: str, *, company_id: str | None = None, contract_ids: list[str] | None = None,
           clause_types: list[str] | None = None, top_k: int | None = None, current_only: bool = True) -> list[Hit]:
    cfg = odin_config()["retrieval"]
    company_id = company_id or maybe_current().company_id
    top_k = top_k or cfg["top_k"]
    cand = cfg["candidate_k"]
    stmt = select(ClauseRow).where(ClauseRow.company_id == company_id)
    if current_only:
        stmt = stmt.where(ClauseRow.is_current.is_(True))
    with db() as s:
        all_rows = list(s.scalars(stmt))
    rows = [r for r in all_rows
            if (not contract_ids or r.contract_id in contract_ids) and (not clause_types or r.clause_type in clause_types)]
    if not rows:
        HOOKS.record("retrieval", (maybe_current().agent if maybe_current() else "system"), query,
                     [], {"dense": [], "sparse": [], "filters": {"contract_ids": contract_ids,
                            "clause_types": clause_types}})
        return []
    by_id = {r.id: r for r in rows}

    # dense — pgvector cosine distance over the filtered set
    dense_ids = []
    if cfg.get("dense_enabled", True):
        qv = embed_query(query)
        if cfg.get("dense_backend") == "memory":
            dense_ids = memory_dense_ids(by_id, qv, cand)
        else:
            with db() as s:
                dstmt = (select(ClauseRow.id).where(ClauseRow.id.in_(list(by_id)), ClauseRow.embedding.is_not(None))
                         .order_by(ClauseRow.embedding.cosine_distance(qv)).limit(cand))
                dense_ids = list(s.scalars(dstmt))

    # sparse — BM25 over the company's current clauses, then filtered
    bm, ids = _BM25.get(company_id, [r for r in all_rows])
    sparse_ids: list[str] = []
    if bm:
        scores = bm.get_scores(tokenize(query))
        ranked = sorted(range(len(ids)), key=lambda i: -scores[i])
        sparse_ids = [ids[i] for i in ranked if ids[i] in by_id and scores[i] > 0][:cand]

    # RRF fusion
    k = cfg["rrf_k"]
    fused: dict[str, float] = {}
    for rank, cid in enumerate(dense_ids):
        fused[cid] = fused.get(cid, 0) + 1 / (k + rank + 1)
    for rank, cid in enumerate(sparse_ids):
        fused[cid] = fused.get(cid, 0) + 1 / (k + rank + 1)
    order = sorted(fused, key=lambda c: -fused[c])
    dpos = {c: i for i, c in enumerate(dense_ids)}
    spos = {c: i for i, c in enumerate(sparse_ids)}
    hits = [Hit(c, by_id[c].contract_id, by_id[c].version, by_id[c].number, by_id[c].heading,
                by_id[c].clause_type, by_id[c].text, by_id[c].page, fused[c], dpos.get(c), spos.get(c),
                by_id[c].company_id)
            for c in order]
    hits = reranker().rerank(query, hits)[:top_k]
    HOOKS.record("retrieval", (maybe_current().agent if maybe_current() else "system"), query,
                 [h.as_dict(None) for h in hits],
                 {"dense": dense_ids[:top_k], "sparse": sparse_ids[:top_k], "filters":
                  {"contract_ids": contract_ids, "clause_types": clause_types}})
    return hits
