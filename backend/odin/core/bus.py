"""In-process pub/sub for SSE. Graph nodes run in worker threads, so publish() is thread-safe
and hops onto the API event loop. ponytail: single process only; swap for Redis pub/sub if the
backend is ever scaled to multiple workers."""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import date, datetime

_loop: asyncio.AbstractEventLoop | None = None
_subs: dict[str, set[asyncio.Queue]] = defaultdict(set)


def bind_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _loop
    _loop = loop


def _default(o):
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    return str(o)


def publish(company_id: str, kind: str, data: dict) -> None:
    if _loop is None or not _subs.get(company_id):
        return
    msg = json.dumps({"kind": kind, "data": data}, default=_default)
    for q in list(_subs[company_id]):
        _loop.call_soon_threadsafe(q.put_nowait, msg)


def subscribe(company_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=1000)
    _subs[company_id].add(q)
    return q


def unsubscribe(company_id: str, q: asyncio.Queue) -> None:
    _subs[company_id].discard(q)
