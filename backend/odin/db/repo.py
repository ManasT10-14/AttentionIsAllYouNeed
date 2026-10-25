"""Shared state store (FR2.4 / NFR6). All agents read & write through here (via tools).

What-if scenarios: writes inside a scenario are tagged with scenario_id; reads inside a scenario
see base records + that scenario's records. Normal reads never see scenario records."""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Iterable, Optional, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy import or_, select, update

from odin.core import bus
from odin.core.context import maybe_current
from odin.core.models import AgentMessage, Clause
from odin.db.session import db
from odin.db.tables import AgentMessageRow, ClauseRow, Company, Contract, ContractVersion, Record, Run

M = TypeVar("M", bound=BaseModel)


def _scope():
    c = maybe_current()
    return (c.company_id, c.scenario_id, c.run_id) if c else (None, None, None)


# ───────────────────────────── records ─────────────────────────────
def put(kind: str, model: BaseModel, *, company_id: str | None = None, contract_id: str | None = None,
        version: int | None = None, status: str | None = None, publish: bool = True, rid: str | None = None) -> dict:
    cid, scen, run_id = _scope()
    company_id = company_id or cid
    data = model.model_dump(mode="json")
    rid = rid or data.get("id") or f"{kind}:{contract_id}:{version}"
    if scen and not rid.startswith(f"{scen}:") and repo_base_exists(rid, company_id):
        rid = f"{scen}:{rid}"          # what-if never overwrites a real record
    status = status if status is not None else str(data.get("status", ""))
    with db() as s:
        row = s.get(Record, _pk(company_id, rid))
        if row is None:
            row = Record(id=_pk(company_id, rid), company_id=company_id, kind=kind, contract_id=contract_id, version=version,
                         run_id=run_id, scenario_id=scen, status=status, data=data)
            s.add(row)
        else:
            row.data, row.status, row.updated_at = data, status, datetime.utcnow()
            if run_id:
                row.run_id = run_id
            if contract_id:
                row.contract_id = contract_id
            if version is not None:
                row.version = version
    if publish and not scen:
        bus.publish(company_id, kind, data)
    return data


def _pk(company_id: str | None, rid: str) -> str:
    """Records are always company-scoped: logical ids (ext:MSA-1:v1, fd-…) repeat across tenants."""
    if not company_id:
        raise RuntimeError("record access without a company scope")
    return f"{company_id}|{rid}"


def repo_base_exists(rid: str, company_id: str) -> bool:
    with db() as s:
        row = s.get(Record, _pk(company_id, rid))
        return row is not None and row.scenario_id is None


def get(kind: str, rid: str, model: Type[M] | None = None):
    cid, scen, _ = _scope()
    with db() as s:
        row = (s.get(Record, _pk(cid, f"{scen}:{rid}")) if scen else None) or s.get(Record, _pk(cid, rid))
        if not row or row.kind != kind:
            return None
        return model.model_validate(row.data) if model else row.data


def query(kind: str, *, company_id: str | None = None, contract_id: str | None = None,
          contract_ids: Iterable[str] | None = None, status: str | Iterable[str] | None = None,
          version: int | None = None, run_id: str | None = None, model: Type[M] | None = None,
          scenario_id: str | None = "__ctx__", limit: int | None = None) -> list:
    cid, scen, _ = _scope()
    company_id = company_id or cid
    if scenario_id == "__ctx__":
        scenario_id = scen
    stmt = select(Record).where(Record.company_id == company_id, Record.kind == kind)
    stmt = stmt.where(or_(Record.scenario_id.is_(None), Record.scenario_id == scenario_id) if scenario_id
                      else Record.scenario_id.is_(None))
    if contract_id:
        stmt = stmt.where(Record.contract_id == contract_id)
    if contract_ids is not None:
        stmt = stmt.where(Record.contract_id.in_(list(contract_ids)))
    if status:
        stmt = stmt.where(Record.status.in_([status] if isinstance(status, str) else list(status)))
    if version is not None:
        stmt = stmt.where(Record.version == version)
    if run_id:
        stmt = stmt.where(Record.run_id == run_id)
    stmt = stmt.order_by(Record.created_at)
    if limit:
        stmt = stmt.limit(limit)
    with db() as s:
        rows = s.scalars(stmt).all()
    if scenario_id:   # scenario copy ("<scen>:<id>") overrides its base record
        pref = f"{scenario_id}:"
        logical = {r.id: r.id.split("|", 1)[1] for r in rows}
        shadowed = {logical[r.id][len(pref):] for r in rows if logical[r.id].startswith(pref)}
        rows = [r for r in rows if logical[r.id] not in shadowed]
    return [model.model_validate(r.data) if model else r.data for r in rows]


def set_status(rid: str, status: str, **data_updates) -> Optional[dict]:
    cid, scen, run_id = _scope()
    with db() as s:
        row = (s.get(Record, _pk(cid, f"{scen}:{rid}")) if scen else None) or s.get(Record, _pk(cid, rid))
        if not row:
            return None
        d = {**row.data, **data_updates}
        if "status" in d:
            d["status"] = status
        if scen and row.scenario_id is None:      # copy-on-write inside a what-if
            s.add(Record(id=_pk(cid, f"{scen}:{rid}"), company_id=row.company_id, kind=row.kind, contract_id=row.contract_id,
                         version=row.version, run_id=run_id, scenario_id=scen, status=status, data=d))
        else:
            row.data, row.status, row.updated_at = d, status, datetime.utcnow()
        company_id, kind = row.company_id, row.kind
    if not scen:
        bus.publish(company_id, kind, d)
    return d


def invalidate(kinds: list[str], contract_id: str, company_id: str | None = None, *,
               except_status: tuple[str, ...] = ("sent", "applied", "approved")) -> int:
    """Mark derived records of a contract stale (contract update flow §6)."""
    cid, _, _ = _scope()
    company_id = company_id or cid
    with db() as s:
        rows = s.scalars(select(Record).where(Record.company_id == company_id, Record.contract_id == contract_id,
                                              Record.kind.in_(kinds), Record.scenario_id.is_(None))).all()
        n = 0
        for r in rows:
            if r.status in except_status:
                continue
            r.status = "superseded"
            r.data = {**r.data, "status": "superseded"} if "status" in r.data else r.data
            n += 1
        return n


def drop_scenario(scenario_id: str) -> None:
    with db() as s:
        for r in s.scalars(select(Record).where(Record.scenario_id == scenario_id)).all():
            s.delete(r)


# ───────────────────────────── messages / runs ─────────────────────────────
def message(msg: AgentMessage) -> None:
    cid, scen, _ = _scope()
    if scen:
        msg.payload = {**msg.payload, "scenario_id": scen}
    msg.payload = json.loads(json.dumps(msg.payload, default=str))   # dates etc. → JSON-safe
    with db() as s:
        s.add(AgentMessageRow(id=msg.id, company_id=cid, run_id=msg.run_id, sender=msg.sender,
                              receiver=msg.receiver, kind=msg.kind, summary=msg.summary,
                              payload=msg.payload, contract_id=msg.contract_id, ts=msg.ts))
    bus.publish(cid, "agent_message", msg.model_dump(mode="json"))


def messages(company_id: str, run_id: str | None = None, limit: int = 500) -> list[dict]:
    stmt = select(AgentMessageRow).where(AgentMessageRow.company_id == company_id)
    if run_id:
        stmt = stmt.where(AgentMessageRow.run_id == run_id)
    stmt = stmt.order_by(AgentMessageRow.ts.desc()).limit(limit)
    with db() as s:
        rows = s.scalars(stmt).all()
    return [{"id": r.id, "run_id": r.run_id, "sender": r.sender, "receiver": r.receiver, "kind": r.kind,
             "summary": r.summary, "payload": r.payload, "contract_id": r.contract_id, "ts": r.ts.isoformat()}
            for r in reversed(rows)]


def update_run(run_id: str, **fields) -> None:
    with db() as s:
        s.execute(update(Run).where(Run.id == run_id).values(**fields))
        r = s.get(Run, run_id)
        company_id = r.company_id if r else None
        snap = run_dict(r) if r else None
    if company_id:
        bus.publish(company_id, "run", snap)


def run_dict(r: Run) -> dict:
    return {"id": r.id, "kind": r.kind, "status": r.status, "workplan": r.workplan, "budget": r.budget,
            "trace_url": r.trace_url, "error": r.error, "scenario_id": r.scenario_id,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None}


# ───────────────────────────── contracts / clauses ─────────────────────────────
def company(company_id: str) -> Company | None:
    with db() as s:
        return s.get(Company, company_id)


def sim_now(company_id: str | None = None) -> date:
    cid = company_id or _scope()[0]
    c = company(cid)
    return c.sim_now if c and c.sim_now else date.today()


def contracts(company_id: str | None = None) -> list[Contract]:
    cid = company_id or _scope()[0]
    with db() as s:
        return list(s.scalars(select(Contract).where(Contract.company_id == cid).order_by(Contract.contract_id)))


def contract(contract_id: str, company_id: str | None = None) -> Contract | None:
    cid = company_id or _scope()[0]
    with db() as s:
        return s.scalar(select(Contract).where(Contract.company_id == cid, Contract.contract_id == contract_id))


def version_row(contract_id: str, version: int, company_id: str | None = None) -> ContractVersion | None:
    cid = company_id or _scope()[0]
    with db() as s:
        return s.scalar(select(ContractVersion).where(ContractVersion.company_id == cid,
                                                      ContractVersion.contract_id == contract_id,
                                                      ContractVersion.version == version))


def clauses(contract_id: str | None = None, version: int | None = None, *, current_only: bool = True,
            company_id: str | None = None, numbers: list[str] | None = None) -> list[ClauseRow]:
    cid = company_id or _scope()[0]
    stmt = select(ClauseRow).where(ClauseRow.company_id == cid)
    if contract_id:
        stmt = stmt.where(ClauseRow.contract_id == contract_id)
    if version is not None:
        stmt = stmt.where(ClauseRow.version == version)
    elif current_only:
        stmt = stmt.where(ClauseRow.is_current.is_(True))
    if numbers:
        stmt = stmt.where(ClauseRow.number.in_(numbers))
    stmt = stmt.order_by(ClauseRow.contract_id, ClauseRow.char_start)
    with db() as s:
        return list(s.scalars(stmt))


def clause_by_number(contract_id: str, number: str, version: int | None = None) -> ClauseRow | None:
    rows = clauses(contract_id, version, numbers=[number.strip().rstrip(".")])
    return rows[0] if rows else None


def to_clause(r: ClauseRow) -> Clause:
    return Clause(id=r.id, contract_id=r.contract_id, version=r.version, number=r.number, heading=r.heading,
                  text=r.text, page=r.page, char_start=r.char_start, char_end=r.char_end,
                  clause_type=r.clause_type)
