"""Gmail API access with the company's stored (encrypted) OAuth tokens."""
from __future__ import annotations

import base64
import hashlib
import re
from datetime import datetime
from email.mime.text import MIMEText
from functools import lru_cache

from cryptography.fernet import Fernet
from sqlalchemy import select

from odin.core.config import odin_config, settings
from odin.db.session import db
from odin.db.tables import OAuthToken, User

SCOPES = ["openid", "email", "profile",
          "https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/gmail.modify",
          "https://www.googleapis.com/auth/gmail.send"]


@lru_cache
def _fernet() -> Fernet:
    key = settings().fernet_key
    if not key:   # derive a stable key from SECRET_KEY for dev
        key = base64.urlsafe_b64encode(hashlib.sha256(settings().secret_key.encode()).digest()).decode()
    return Fernet(key.encode())


def enc(s: str) -> str:
    return _fernet().encrypt(s.encode()).decode() if s else ""


def dec(s: str) -> str:
    return _fernet().decrypt(s.encode()).decode() if s else ""


def store_tokens(user_id: str, token: dict) -> None:
    with db() as s:
        row = s.get(OAuthToken, user_id) or OAuthToken(user_id=user_id)
        if token.get("refresh_token"):
            row.enc_refresh = enc(token["refresh_token"])
        row.enc_access = enc(token.get("access_token", ""))
        row.expires_at = datetime.utcfromtimestamp(token["expires_at"]) if token.get("expires_at") else None
        row.scopes = token.get("scope", "")
        s.merge(row)


class NoGmail(Exception):
    pass


def _service(company_id: str):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    with db() as s:
        row = s.execute(select(OAuthToken, User).join(User, User.id == OAuthToken.user_id)
                        .where(User.company_id == company_id)).first()
    if not row or not row[0].enc_refresh:
        raise NoGmail("company has no Gmail connection (log in with Google)")
    tok = row[0]
    creds = Credentials(token=dec(tok.enc_access) or None, refresh_token=dec(tok.enc_refresh),
                        token_uri="https://oauth2.googleapis.com/token", client_id=settings().google_client_id,
                        client_secret=settings().google_client_secret, scopes=tok.scopes.split() or SCOPES)
    return build("gmail", "v1", credentials=creds, cache_discovery=False), row[1].email


def _label_id(svc, name: str) -> str:
    labels = svc.users().labels().list(userId="me").execute().get("labels", [])
    for l in labels:
        if l["name"] == name:
            return l["id"]
    return svc.users().labels().create(userId="me", body={"name": name, "labelListVisibility": "labelShow",
                                                          "messageListVisibility": "show"}).execute()["id"]


def _body(payload: dict) -> str:
    def walk(p):
        mt = p.get("mimeType", "")
        data = p.get("body", {}).get("data")
        if mt == "text/plain" and data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        for part in p.get("parts", []) or []:
            t = walk(part)
            if t:
                return t
        if mt == "text/html" and data:
            html = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            return re.sub(r"<[^>]+>", "", re.sub(r"<br\s*/?>|</p>", "\n", html))
        return ""
    return walk(payload)


def fetch_new(company_id: str, max_results: int = 20) -> list[dict]:
    svc, _ = _service(company_id)
    cfg = odin_config()["email"]
    q = f'subject:"{cfg["subject_prefix"]}" -label:{cfg["processed_label"].replace("/", "-")} newer_than:7d'
    msgs = svc.users().messages().list(userId="me", q=q, maxResults=max_results).execute().get("messages", [])
    out = []
    for m in msgs:
        full = svc.users().messages().get(userId="me", id=m["id"], format="full").execute()
        h = {x["name"].lower(): x["value"] for x in full["payload"].get("headers", [])}
        out.append({"id": m["id"], "thread_id": full.get("threadId"), "subject": h.get("subject", ""),
                    "from": h.get("reply-to") or h.get("from", ""), "body": _body(full["payload"])})
    return out


def mark_processed(company_id: str, msg_id: str) -> None:
    svc, _ = _service(company_id)
    lid = _label_id(svc, odin_config()["email"]["processed_label"])
    svc.users().messages().modify(userId="me", id=msg_id, body={"addLabelIds": [lid]}).execute()


def send_message(company_id: str, to: str, subject: str, body: str, thread_id: str | None = None) -> dict:
    svc, me = _service(company_id)
    msg = MIMEText(body)
    msg["to"], msg["from"], msg["subject"] = to, me, subject
    payload = {"raw": base64.urlsafe_b64encode(msg.as_bytes()).decode()}
    if thread_id:
        payload["threadId"] = thread_id
    r = svc.users().messages().send(userId="me", body=payload).execute()
    return {"id": r.get("id"), "thread_id": r.get("threadId")}
