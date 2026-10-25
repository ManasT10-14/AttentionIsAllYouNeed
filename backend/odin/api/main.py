"""FastAPI app: REST under /api, SSE live stream, Gmail poller, static frontend (if built)."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sse_starlette.sse import EventSourceResponse
from starlette.middleware.sessions import SessionMiddleware

from odin.api import auth, routes
from odin.api.deps import current_user
from odin.core import bus
from odin.core.config import settings
from odin.db.session import init_db
from odin.db.tables import User

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings()
    init_db()
    bus.bind_loop(asyncio.get_running_loop())
    from odin.email import poller
    poller.start()
    yield
    poller.stop()


app = FastAPI(title="RAGNAROK · Odin", version="0.1.0", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings().secret_key, same_site="lax", https_only=False)
app.add_middleware(CORSMiddleware, allow_origins=[settings().frontend_url], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router, prefix="/api")
app.include_router(auth.router)                # Google redirect URI (/auth/google/callback)
app.include_router(routes.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/stream")
async def stream(request: Request, u: User = Depends(current_user)):
    q = bus.subscribe(u.company_id)

    async def gen():
        try:
            yield {"event": "ping", "data": "{}"}    # flush headers now; proxies hold them until first bytes
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=15)
                    yield {"data": msg}          # unnamed → EventSource.onmessage
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": "{}"}
        finally:
            bus.unsubscribe(u.company_id, q)
    # no-transform: stops proxies (e.g. the Next.js dev server) from gzipping and buffering the stream
    return EventSourceResponse(gen(), headers={"Cache-Control": "no-cache, no-transform"})


@app.get("/", include_in_schema=False)
def root():
    """The UI lives in frontend/ (served separately); send browsers there."""
    return RedirectResponse(settings().frontend_url)
