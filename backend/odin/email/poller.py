"""Background Gmail poller: every N seconds, pull new [ODIN-EVENT] mails for each connected company."""
from __future__ import annotations

import logging
import threading
from datetime import datetime

from sqlalchemy import select

from odin.core import bus
from odin.core.config import odin_config
from odin.db.session import db
from odin.db.tables import OAuthToken, User
from odin.email import gmail
from odin.services import events

log = logging.getLogger("odin.poller")
_stop = threading.Event()
_status: dict[str, dict] = {}


def poll_company(company_id: str) -> dict:
    res = {"fetched": 0, "accepted": 0, "rejected": 0, "error": None, "at": datetime.utcnow().isoformat()}
    try:
        for m in gmail.fetch_new(company_id):
            res["fetched"] += 1
            r = events.receive(company_id, subject=m["subject"], body=m["body"], sender=m["from"],
                               gmail_msg_id=m["id"], thread_id=m["thread_id"])
            res["accepted" if r["status"] == "accepted" else "rejected"] += r["status"] != "duplicate"
            gmail.mark_processed(company_id, m["id"])
            bus.publish(company_id, "email", {"subject": m["subject"], "from": m["from"], **r})
    except gmail.NoGmail as e:
        res["error"] = str(e)
    except Exception as e:   # noqa: BLE001 — network / auth problems must not kill the loop
        log.warning("poll %s failed: %s", company_id, e)
        res["error"] = f"{type(e).__name__}: {e}"[:300]
    with db() as s:
        for tok in s.scalars(select(OAuthToken).join(User, User.id == OAuthToken.user_id)
                             .where(User.company_id == company_id)):
            tok.last_poll_at = datetime.utcnow()
    _status[company_id] = res
    return res


def status(company_id: str) -> dict:
    return _status.get(company_id, {})


def _loop():
    every = odin_config()["email"]["poll_seconds"]
    while not _stop.wait(every):
        with db() as s:
            companies = {u.company_id for u in s.scalars(
                select(User).join(OAuthToken, OAuthToken.user_id == User.id).where(OAuthToken.enc_refresh != ""))}
        for cid in companies:
            poll_company(cid)


def start() -> None:
    threading.Thread(target=_loop, name="gmail-poller", daemon=True).start()


def stop() -> None:
    _stop.set()
