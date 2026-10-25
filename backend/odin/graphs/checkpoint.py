"""LangGraph Postgres checkpointer (run replay / resumability). Falls back to in-memory if unavailable."""
from __future__ import annotations

import logging
from functools import lru_cache

from odin.core.config import settings

log = logging.getLogger("odin.checkpoint")


@lru_cache
def checkpointer():
    import os
    if os.getenv("ODIN_CHECKPOINT_BACKEND") == "memory":
        from langgraph.checkpoint.memory import InMemorySaver
        return InMemorySaver()
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg_pool import ConnectionPool
        url = settings().database_url.replace("postgresql+psycopg://", "postgresql://")
        pool = ConnectionPool(url, max_size=10, kwargs={"autocommit": True, "prepare_threshold": 0})
        saver = PostgresSaver(pool)
        saver.setup()
        return saver
    except Exception as e:   # noqa: BLE001
        log.warning("Postgres checkpointer unavailable (%s) — using in-memory", e)
        from langgraph.checkpoint.memory import InMemorySaver
        return InMemorySaver()
