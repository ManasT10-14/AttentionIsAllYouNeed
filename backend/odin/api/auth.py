"""Google OAuth login (same grant gives Heimdall Gmail access) + dev login for local demos."""
from __future__ import annotations

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select

from odin.api.deps import current_user
from odin.core.config import settings
from odin.core.models import new_id
from odin.db.session import db
from odin.db.tables import Company, OAuthToken, User
from odin.email.gmail import SCOPES, store_tokens

router = APIRouter(prefix="/auth", tags=["auth"])
oauth = OAuth()
oauth.register("google", client_id=settings().google_client_id, client_secret=settings().google_client_secret,
               server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
               client_kwargs={"scope": " ".join(SCOPES)})


def _upsert_user(email: str, name: str, google_sub: str | None = None) -> User:
    with db() as s:
        u = s.scalar(select(User).where(User.email == email))
        if u:
            if google_sub:
                u.google_sub = google_sub
            return u
        cid = new_id("co")
        s.add(Company(id=cid, name=name or email.split("@")[-1]))
        s.flush()
        u = User(id=new_id("usr"), company_id=cid, email=email, name=name, google_sub=google_sub, role="admin")
        s.add(u)
        return u


@router.get("/google/login")
async def google_login(request: Request):
    if not settings().google_client_id:
        raise HTTPException(400, "GOOGLE_CLIENT_ID not configured — use dev login")
    redirect = f"{settings().public_base_url}/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect, access_type="offline", prompt="consent",
                                                 include_granted_scopes="true")


@router.get("/google/callback")
async def google_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    info = token.get("userinfo") or {}
    if not info.get("email"):
        raise HTTPException(400, "Google did not return an email")
    current = request.session.get("user_id")
    if current:
        # Already signed in (e.g. dev login with seeded data): CONNECT this Gmail inbox to the current
        # company instead of switching to a new, empty company keyed by the Google email.
        with db() as s:
            u = s.get(User, current)
            if u:
                u.google_sub = info.get("sub")
                u.gmail_address = info["email"]
    else:
        u = None
    if not u:
        u = _upsert_user(info["email"], info.get("name", ""), info.get("sub"))
    store_tokens(u.id, token)
    request.session["user_id"] = u.id
    return RedirectResponse(settings().frontend_url)


class DevLogin(BaseModel):
    email: str = "demo@acme.example"
    name: str = "Acme Corp"


@router.post("/dev-login")
def dev_login(body: DevLogin, request: Request):
    if not settings().dev_login:
        raise HTTPException(403, "dev login disabled")
    u = _upsert_user(body.email, body.name)
    request.session["user_id"] = u.id
    return {"ok": True, "user_id": u.id}


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/me")
def me(request: Request):
    flags = {"google_configured": bool(settings().google_client_id), "dev_login": settings().dev_login}
    try:
        u = current_user(request)
    except HTTPException as e:
        raise HTTPException(401, {"error": e.detail, **flags})
    with db() as s:
        c = s.get(Company, u.company_id)
        tok = s.get(OAuthToken, u.id)
    return {"user": {"id": u.id, "email": u.email, "name": u.name, "role": u.role},
            "company": {"id": c.id, "name": c.name, "context": c.context, "sim_now": c.sim_now},
            "gmail_connected": bool(tok and tok.enc_refresh),
            "gmail_address": u.gmail_address or (u.email if tok and tok.enc_refresh else None),
            **flags}
