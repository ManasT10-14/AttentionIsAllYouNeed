"""Event intake: email/manual/demo → validated Event record → event graph run (FR5, NFR3)."""
from __future__ import annotations

import hashlib
import logging
from typing import Optional

from pydantic import BaseModel

from odin.agents.base import prompt
from odin.core.config import odin_config
from odin.core.context import run_ctx
from odin.core.hooks import HOOKS, Blocked
from odin.core.models import Event, ParsedEvent, new_id
from odin.db import repo
from odin.db.session import db
from odin.db.tables import Company
from odin.email import event_parser
from odin.llm.call import LLMFailure, structured

log = logging.getLogger("odin.events")


class LLMParsed(BaseModel):
    ok: bool
    event: Optional[ParsedEvent] = None
    confidence: float = 0.0
    problems: list[str] = []


def receive(company_id: str, *, subject: str, body: str, sender: str = "", gmail_msg_id: str | None = None,
            thread_id: str | None = None, method: str = "strict", scenario_id: str | None = None,
            run: bool = True, background: bool = True) -> dict:
    with run_ctx(company_id, scenario_id=scenario_id, agent="heimdall"):
        dedupe = gmail_msg_id or hashlib.sha1(f"{subject}\n{body}".encode()).hexdigest()[:16]
        if not scenario_id:
            existing = next((e for e in repo.query("event") if e.get("gmail_msg_id") == dedupe), None)
            if existing:
                if method == "manual" and existing.get("status") == "rejected":
                    return {"status": "rejected", "event_id": existing["id"],
                            "problems": [existing.get("reject_reason") or "Event could not be parsed"], "auto_replied": False}
                return {"status": "duplicate", "dedupe": dedupe}
        ev_id = new_id("evt")
        quarantine = ""
        try:
            body = HOOKS.on_email(body, {"company_id": company_id, "sender": sender, "subject": subject,
                                         "event_id": ev_id})
        except Blocked as e:   # held for admin review (POST /api/security/events/{id}), never auto-run
            quarantine = f"quarantined by security guard: {e}"
        parse_method, conf = method, 1.0
        try:
            parsed = event_parser.parse(subject, body)
        except event_parser.EventParseError as e:
            parsed, conf, problems = _llm_parse(subject, body, e.problems)
            if not parsed:
                return _reject(company_id, ev_id, dedupe, subject, body, sender, problems, thread_id, scenario_id, method)
            parse_method = "llm"
        known = {c.contract_id for c in repo.contracts()}
        if parsed.contract_ids == ["ALL"]:
            parsed.contract_ids = sorted(known)
        unknown = [c for c in parsed.contract_ids if c not in known]
        parsed.contract_ids = [c for c in parsed.contract_ids if c in known]
        if parsed.external_id and not scenario_id and any(
                e.get("external_id") == parsed.external_id for e in repo.query("event")):
            return {"status": "duplicate", "external_id": parsed.external_id}
        ev = Event(id=ev_id, gmail_msg_id=dedupe, sender=sender, subject=subject, raw=body[:20000],
                   parse_method=parse_method, parse_confidence=conf, status="processing", scenario_id=scenario_id,
                   **parsed.model_dump())
        if unknown:
            ev.reject_reason = f"unknown contract ids ignored: {unknown}; Heimdall will infer"
        if quarantine:
            ev.status, ev.reject_reason = "quarantined", "; ".join(filter(None, [quarantine, ev.reject_reason]))
            repo.put("event", ev)
            return {"status": "quarantined", "event_id": ev_id, "reason": quarantine}
        repo.put("event", ev)
        if not scenario_id:
            _advance_clock(company_id, ev)
    if run:
        from odin.graphs import event as event_graph
        run_id = event_graph.run(company_id, ev_id, scenario_id=scenario_id, background=background)
        return {"status": "accepted", "event_id": ev_id, "run_id": run_id, "parse_method": parse_method}
    return {"status": "accepted", "event_id": ev_id, "parse_method": parse_method}


def _llm_parse(subject: str, body: str, problems: list[str]):
    try:
        out = structured("email_parse", LLMParsed, prompt("email_parse"),
                         f"Strict parser problems: {problems}\n\n<email>\nSubject: {subject}\n\n{body[:6000]}\n</email>")
    except LLMFailure as e:
        return None, 0.0, problems + [f"LLM fallback unavailable: {e}"]
    if out.ok and out.event and out.confidence >= 0.6:
        return out.event, out.confidence, []
    return None, out.confidence, problems + out.problems


def _reject(company_id, ev_id, dedupe, subject, body, sender, problems, thread_id, scenario_id, method) -> dict:
    ev = Event(id=ev_id, gmail_msg_id=dedupe, sender=sender, subject=subject, raw=body[:20000], status="rejected",
               reject_reason="; ".join(problems), parse_method=method, parse_confidence=0.0, scenario_id=scenario_id,
               event_type="CUSTOM", occurred_at=event_parser.utcnow())
    repo.put("event", ev)
    replied = False
    if sender and method == "strict" and odin_config()["email"]["auto_reply_on_reject"] and not scenario_id:
        try:
            from odin.tools.registry import REGISTRY
            REGISTRY.invoke("system", "send_system_reply", {"to": sender, "subject": f"Re: {subject}",
                                                            "body": event_parser.reply_body(problems),
                                                            "thread_id": thread_id})
            replied = True
        except Exception as e:   # noqa: BLE001
            log.warning("auto-reply failed: %s", e)
    return {"status": "rejected", "event_id": ev_id, "problems": problems, "auto_replied": replied}


def _advance_clock(company_id: str, ev: Event) -> None:
    """Events from the future pull the simulated clock forward (spec §3.3)."""
    d = ev.occurred_at.date()
    with db() as s:
        c = s.get(Company, company_id)
        if c and (c.sim_now is None or d > c.sim_now):
            c.sim_now = d
