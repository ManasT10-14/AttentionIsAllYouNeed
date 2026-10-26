"""Staged, chronological event replay; future drops never enter agent context."""
from __future__ import annotations

import json
import threading
from datetime import date, datetime, timezone
from functools import lru_cache

from odin.core.context import run_ctx
from odin.core.hooks import HOOKS, Blocked
from odin.core.models import Event
from odin.db import repo
from odin.db.session import db
from odin.db.tables import Company, Record, Run
from odin.services import bundle, insights
from sqlalchemy import select


@lru_cache(maxsize=128)
def _lock(company_id):
    return threading.Lock()


def state():
    s = repo.get("simulation", "official:simulation")
    if not s:
        raise ValueError("Import the official bundle first")
    return {**s, "sim_now": repo.sim_now().isoformat(),
            "pending_events": len(repo.query("simulation_pending", status="queued")),
            "held_events": len(repo.query("simulation_pending", status="quarantined"))}


def _store_state(s):
    bundle.save("simulation", "official:simulation", {k: v for k, v in s.items() if k not in ("sim_now", "pending_events", "held_events")})


def load_drop(company_id: str, n: int):
    if n not in (1, 2):
        raise ValueError("Unknown drop; expected 1 or 2")
    with _lock(company_id), run_ctx(company_id, agent="system"):
        s = state()
        if n in s["drops_loaded"]:
            return {**s, "duplicate": True}
        if n == 2 and 1 not in s["drops_loaded"]:
            raise ValueError("Load Drop 1 before Drop 2")
        accepted, rejected = 0, 0
        path = bundle.PACK / f"bundle/events/events_drop{n}.jsonl"
        seen = {r["event"]["external_id"] for r in repo.query("simulation_pending")}
        for line, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            if not raw.strip():
                continue
            identity = f"official:drop{n}:line{line}"
            try:
                data = json.loads(raw)
                if not isinstance(data, dict):
                    raise ValueError("Event must be a JSON object")
                for key in ("event_id", "timestamp", "channel", "from", "to", "subject", "body"):
                    if not isinstance(data.get(key), str) or not data[key].strip():
                        raise ValueError(f"Missing or invalid {key}")
                stamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
                if stamp.tzinfo is None:
                    raise ValueError("Timestamp must include a timezone")
                if data["event_id"] in seen:
                    raise ValueError("Duplicate event_id in drop")
                ev = Event(id=identity, external_id=data["event_id"], event_type="CUSTOM",
                           occurred_at=stamp.astimezone(timezone.utc), sender=data["from"], recipient=data["to"],
                           subject=data["subject"], description=data["body"], raw=raw, channel=data["channel"],
                           source=f"drop{n}", line=line, parse_method="jsonl", status="received")
                # Queue is separate from event records read by agents; load does not disclose future events.
                bundle.save("simulation_pending", identity, {"id": identity, "status": "queued", "event": ev.model_dump(mode="json")})
                seen.add(data["event_id"])
                accepted += 1
            except (ValueError, TypeError) as exc:
                bundle.save("event", identity, {"id": identity, "status": "rejected", "external_id": "",
                            "event_type": "CUSTOM", "occurred_at": None, "source": f"drop{n}", "line": line,
                            "subject": "Malformed drop line", "raw": raw, "reject_reason": str(exc), "parse_method": "jsonl"})
                rejected += 1
        s["drops_loaded"] = [*s["drops_loaded"], n]
        _store_state(s)
        return {**state(), "accepted": accepted, "rejected": rejected}


def add_business_days(start: date, days: int, holidays: list[dict], observed_by: str = "Quillhub") -> date:
    from odin.services.timeline import add_business_days as calculate
    return calculate(start, days, holidays, observed_by)


def _clock(company_id, target):
    with db() as s:
        s.get(Company, company_id).sim_now = target
    from odin.core import bus
    bus.publish(company_id, "clock", {"sim_now": target.isoformat()})


def snapshot(checkpoint):
    tls = insights.timelines(checkpoint)
    deadlines = [e.model_dump(mode="json") for t in tls for e in t.entries]
    extractions = [insights.extraction(c.contract_id) for c in repo.contracts()]
    data = {"checkpoint": checkpoint.isoformat(), "date": checkpoint.isoformat(),
            "obligations": [o.model_dump(mode="json") for x in extractions if x for o in x.obligations],
            "deadlines": deadlines, "exposure": insights.exposure_summary(checkpoint),
            "open_risks": [f for f in repo.query("finding") if f.get("status") not in ("superseded", "dismissed", "resolved")],
            "alerts": insights.alerts(checkpoint),
            "actions": [a for a in repo.query("action") if a.get("status") != "superseded"],
            "ledger": bundle.ledger_as_of(checkpoint),
            "events": repo.query("event"),
            "analysis_complete": all(x is not None for x in extractions) and bool(extractions)
                                 and not any(e.get("status") in ("received", "processing", "needs_review", "quarantined", "reviewing") or e.get("impact_review_required") for e in repo.query("event"))}
    # Date objects in exposure/read-side views must be JSON-safe in PostgreSQL and SQLite.
    data = json.loads(json.dumps(data, default=str))
    bundle.save("simulation_checkpoint", f"official:checkpoint:{checkpoint}", data)
    return data


def advance(company_id: str, target: date | None = None, *, one: bool = False, assess: bool = True):
    """Synchronous worker; routes schedule one background run so browser calls stay short."""
    from odin.graphs import event as event_graph
    with _lock(company_id), run_ctx(company_id, agent="system"):
        s = state()
        # A later play/advance request must not skip an earlier security hold.
        # Only an explicit review outcome can remove it from the pending queue.
        for held in repo.query("simulation_pending", status="quarantined"):
            event = repo.get("event", held["event"]["id"] + ":event") or {}
            if event.get("status") == "rejected" and event.get("review_decision") == "confirm":
                repo.set_status(held["id"], "rejected")
            elif event.get("review_release_status") == "released":
                repo.set_status(held["id"], "delivered")
            else:
                return {**state(), "processed": 0, "blocked_by_security": True,
                        "held_event_id": event.get("id"), "reason": "Review the held event before advancing"}
        now = repo.sim_now()
        pending = sorted(repo.query("simulation_pending", status="queued"), key=lambda x: (x["event"]["occurred_at"], x["id"]))
        if one:
            if not pending:
                return {**s, "processed": 0}
            target = max(now, date.fromisoformat(pending[0]["event"]["occurred_at"][:10]))
        elif target is None:
            target = next((date.fromisoformat(d) for d in s["checkpoints"] if d > now.isoformat()), now)
        if target < now:
            raise ValueError("Clock cannot move backwards; reset the simulation first")
        if target.isoformat() > s["checkpoints"][-1]:
            raise ValueError("Target is beyond the final checkpoint")
        if 1 not in s["drops_loaded"]:
            raise ValueError("Load Drop 1 before advancing")
        if target.isoformat() > s["checkpoints"][0] and 2 not in s["drops_loaded"]:
            raise ValueError("Load Drop 2 before advancing beyond checkpoint 1")
        known_snaps = {r["checkpoint"] for r in repo.query("simulation_checkpoint")}
        cps = [date.fromisoformat(d) for d in s["checkpoints"] if d not in known_snaps and d <= target.isoformat()]
        selected = [p for p in pending if p["event"]["occurred_at"][:10] <= target.isoformat()]
        if one:
            selected = selected[:1]
        processed = 0
        for p in selected:
            ev = Event.model_validate(p["event"])
            event_id = ev.id + ":event"
            existing = repo.get("event", event_id)
            if existing and existing.get("status") in ("processed", "noise", "needs_review"):
                repo.set_status(p["id"], "delivered")
                continue
            # Scheduled JSONL bypasses email parsing, but never the security ingress policy.
            # Scan at delivery time: loading a future drop must not disclose it to models.
            try:
                HOOKS.on_email(f"Subject: {ev.subject}\nFrom: {ev.sender}\nTo: {ev.recipient}\n"
                               f"{ev.description}\n{ev.raw}",
                               {"company_id": company_id, "event_id": event_id, "source": "scheduled_event"})
            except Blocked as exc:
                from odin.services.events import quarantine_event
                quarantine_event(company_id, ev.model_copy(update={"id": event_id}), str(exc))
                repo.set_status(p["id"], "quarantined")
                return {**state(), "processed": processed, "blocked_by_security": True,
                        "held_event_id": event_id, "reason": "Review the held event before advancing"}
            event_day = ev.occurred_at.date()
            while cps and cps[0] < event_day:
                cp = cps.pop(0)
                _clock(company_id, cp)
                snapshot(cp)
            _clock(company_id, max(now, event_day))
            # Different record kinds require distinct logical IDs.
            ev.id = event_id
            repo.put("event", ev)
            if assess:
                event_graph.run(company_id, event_id, background=False)
            repo.set_status(p["id"], "delivered")
            processed += 1
        _clock(company_id, target)
        # Do not freeze a checkpoint while same-day events remain in the queue.
        remaining = repo.query("simulation_pending", status="queued")
        for cp in cps:
            if not any(p["event"]["occurred_at"][:10] <= cp.isoformat() for p in remaining):
                _clock(company_id, cp)
                snapshot(cp)
        _clock(company_id, target)
        return {**state(), "processed": processed}


def reset(company_id):
    with _lock(company_id), run_ctx(company_id, agent="system"):
        s = state()
        events = repo.query("event")
        ids = {e["id"] for e in events if e.get("source") in ("drop1", "drop2")}
        with db() as session:
            rows = session.scalars(select(Record).where(Record.company_id == company_id, Record.scenario_id.is_(None))).all()
            event_runs = {r.id for r in session.scalars(select(Run).where(Run.company_id == company_id)).all()
                          if r.workplan.get("links", {}).get("event_id") in ids}
            for r in rows:
                if r.kind == "report":
                    session.delete(r)
                elif r.kind in ("simulation_pending", "simulation_checkpoint") or (r.kind == "event" and r.data.get("id") in ids):
                    session.delete(r)
                elif r.data.get("event_id") in ids or r.run_id in event_runs:
                    if r.status in ("sent", "approved", "applied"):
                        raise ValueError("Cannot reset a simulation with approved or executed actions")
                    r.status = "superseded"
                    r.data = {**r.data, "status": "superseded"}
            session.get(Company, company_id).sim_now = date.fromisoformat(s["start_date"])
        _clock(company_id, date.fromisoformat(s["start_date"]))
        _store_state({**s, "drops_loaded": []})
        return state()
