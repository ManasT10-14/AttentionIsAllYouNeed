from __future__ import annotations

from typing import Iterator

from fastapi import Depends, HTTPException, Request

from odin.core.context import RunCtx, run_ctx
from odin.db.session import db
from odin.db.tables import User

ROLE_RANK = {"viewer": 0, "admin": 1, "super_admin": 2}


def current_user(request: Request) -> User:
    uid = request.session.get("user_id")
    if not uid:
        raise HTTPException(401, "not logged in")
    with db() as s:
        u = s.get(User, uid)
    if not u:
        request.session.clear()
        raise HTTPException(401, "session expired")
    return u


def require_role(role: str):
    def dep(u: User = Depends(current_user)) -> User:
        if ROLE_RANK.get(u.role, -1) < ROLE_RANK[role]:
            raise HTTPException(403, f"requires role {role}")
        return u
    return dep


def ctx(u: User = Depends(current_user)) -> Iterator[RunCtx]:
    """Every request runs inside the caller's company context."""
    with run_ctx(u.company_id, agent="system", user_role=u.role) as c:
        yield c
