"""Tenant-scoped, compare-and-swap quarantine review and one-shot release."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from odin.core.context import run_ctx
from odin.core.privacy import redact
from odin.db import repo
from odin.db.session import db
from odin.db.tables import Record
from sqlalchemy import select, update

POLICY = "quarantine-review-v1"


def review(company_id: str, sid: str, *, decision: str, reason: str, reviewer: str,
           expected_revision: int = 0) -> dict:
    reason = reason.strip()
    if not reason:
        raise HTTPException(422, "a review reason is required")
    now = datetime.now(timezone.utc).isoformat()
    metadata = {"reviewed_by": reviewer, "reviewed_at": now, "review_reason": redact(reason),
                "review_note": redact(reason), "review_policy": POLICY, "review_decision": decision}
    # All pending state and review metadata commit together. A concurrent request
    # fails the CAS before it can parse, move the clock, or launch the graph.
    with db() as s:
        sec = s.get(Record, repo._pk(company_id, sid))
        if not sec or sec.kind != "security_event":
            raise HTTPException(404, "unknown security event")
        revision = sec.data.get("review_revision", 0)
        if revision != expected_revision or sec.status in ("released", "confirmed", "release_pending", "release_failed"):
            raise HTTPException(409, "review changed; refresh before reviewing again")
        event_id = sec.data.get("event_id")
        ev = s.get(Record, repo._pk(company_id, event_id)) if event_id else None
        if ev and ev.kind != "event":
            ev = None
        if decision == "release" and (not ev or ev.status != "quarantined"):
            raise HTTPException(409, "only a held event can be released once")
        status = {"release": "release_pending", "confirm": "confirmed", "dismiss": "dismissed"}[decision]
        changed = s.execute(update(Record).where(Record.id == sec.id, Record.company_id == company_id,
                        Record.updated_at == sec.updated_at, Record.status == sec.status)
                        .values(status=status, updated_at=datetime.utcnow(),
                                data={**sec.data, **metadata, "status": status, "review_revision": revision + 1}))
        if changed.rowcount != 1:
            raise HTTPException(409, "review already claimed")
        held = dict(ev.data) if ev else None
        if ev and ev.status == "quarantined":
            next_status = {"release": "reviewing", "confirm": "rejected", "dismiss": "quarantined"}[decision]
            changed = s.execute(update(Record).where(Record.id == ev.id, Record.company_id == company_id,
                            Record.status == "quarantined", Record.updated_at == ev.updated_at).values(status=next_status,
                            updated_at=datetime.utcnow(), data={**ev.data, **metadata, "status": next_status,
                            "review_revision": ev.data.get("review_revision", 0) + 1}))
            if changed.rowcount != 1:
                raise HTTPException(409, "event already reviewed")
        siblings = s.scalars(select(Record).where(Record.company_id == company_id,
                            Record.kind == "security_event")).all() if ev else [sec]
        siblings = [r for r in siblings if r.data.get("event_id") == event_id] if ev else siblings
        sibling_ids = [r.id.split("|", 1)[1] for r in siblings]
        for sibling in siblings:
            if sibling.id == sec.id:
                continue
            sibling.status = status
            sibling.data = {**sibling.data, **metadata, "status": status,
                            "review_revision": sibling.data.get("review_revision", 0) + 1}
        private = s.get(Record, repo._pk(company_id, "quarantine:" + event_id)) if event_id else None
        evidence = dict(private.data.get("evidence", {})) if private and private.kind == "quarantine_evidence" else None
    result = {"id": sid, "status": status, "event_id": event_id, "run_id": None,
              "updated": len(sibling_ids), "review_revision": revision + 1}
    if decision != "release":
        return result
    from odin.graphs import event as event_graph
    from odin.services import events
    try:
        if not evidence:
            # Historical email holds predate private evidence storage. Reparse
            # their saved source; fail closed if that source is unavailable.
            if not held.get("raw"):
                raise ValueError("original quarantine evidence unavailable")
            evidence = {"body": held["raw"], "subject": held.get("subject", ""),
                        "sender": held.get("sender", ""), "method": held.get("parse_method", "strict")}
        with run_ctx(company_id, scenario_id=held.get("scenario_id"), agent="system", user_role="admin"):
            parsed = events.validate_released_event(held, evidence)
            repo.put("event", parsed)
            repo.set_status(event_id, "processing", **metadata, review_release_status="release_pending")
            if not parsed.scenario_id:
                events._advance_clock(company_id, parsed)
            run_id = event_graph.run(company_id, event_id, scenario_id=parsed.scenario_id)
        result.update(status="released", run_id=run_id)
    except Exception:  # A failed launch stays claimed; a retry cannot launch again.
        with run_ctx(company_id, scenario_id=held.get("scenario_id")):
            repo.set_status(event_id, "needs_review", review_release_status="release_failed",
                            reject_reason="Release validation or launch failed; manual recovery required")
        result.update(status="release_failed", error="Release validation or launch failed; no automatic retry")
    with db() as s:
        # Update data only: the background graph may already have changed status.
        event_row = s.get(Record, repo._pk(company_id, event_id))
        if event_row:
            event_row.data = {**event_row.data, "review_release_status": result["status"],
                              "security_run_id": result["run_id"]}
        for identity in sibling_ids:
            row = s.get(Record, repo._pk(company_id, identity))
            if row:
                row.status = result["status"]
                row.data = {**row.data, "status": result["status"], "run_id": result["run_id"],
                            "release_error": result.get("error")}
    return result
