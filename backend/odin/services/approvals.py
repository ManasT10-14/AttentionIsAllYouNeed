"""Durable, payload-bound, one-shot approvals for external action effects.

An executing/ambiguous claim deliberately has no automatic retry. A provider timeout
does not prove that delivery failed; reconciliation must happen before a new action.
"""
from __future__ import annotations

import hashlib
import json
import re
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone

from odin.core.context import current, maybe_current
from odin.core.models import new_id
from odin.db import repo
from odin.db.session import db
from odin.db.tables import Company, Contract, ContractVersion, Record
from sqlalchemy import select, update


class ApprovalRequired(Exception):
    pass


_LIFETIME = timedelta(hours=1)
_EMAIL = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@(?:[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,}$")
_EMAIL_IN_TEXT = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_META = {"status", "approval", "approval_execution", "approved_by", "approved_at", "edited_by",
         "rejected_by", "sent_at", "gmail", "applied_version"}
_DISPATCH = ContextVar("approved_action_dispatch", default=None)


def _require_admin():
    context = maybe_current()
    if not context or context.user_role not in {"admin", "super_admin"}:
        raise ApprovalRequired("admin authorization is required for action dispatch and review")


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _revision(action: dict) -> str:
    return _digest({k: v for k, v in action.items() if k not in _META})


def action_payload(action: dict) -> tuple[str, dict]:
    """Only saved action data may construct an executable payload."""
    if action.get("kind") == "amendment":
        if not action.get("redlines"):
            raise ApprovalRequired("amendment has no redlines")
        return "apply_amendment", {"action_id": action["id"]}
    return "send_gmail", {"to": action.get("to", ""), "subject": action.get("subject", ""),
                           "body": action.get("body_md", ""), "thread_id": None}


def _row(s, aid):
    c = current()
    if not c.company_id or c.scenario_id:
        raise ApprovalRequired("external action approval requires a live company scope")
    row = s.get(Record, repo._pk(c.company_id, aid))
    if not row or row.company_id != c.company_id or row.kind != "action" or row.scenario_id:
        raise ApprovalRequired("action is unavailable")
    return row


def _sources(s, action):
    c = current()
    cid = action.get("contract_id")
    stmt = select(Contract).where(Contract.company_id == c.company_id)
    if cid != "cross":
        stmt = stmt.where(Contract.contract_id == cid)
    contracts = s.scalars(stmt.order_by(Contract.contract_id).with_for_update()).all()
    if not contracts:
        raise ApprovalRequired("action source contract is unavailable")
    sources = []
    for contract in contracts:
        version = s.scalar(select(ContractVersion).where(ContractVersion.company_id == c.company_id,
            ContractVersion.contract_id == contract.contract_id,
            ContractVersion.version == contract.current_version))
        if not version or not version.sha256 or contract.status in {"withdrawn", "deleted", "superseded"}:
            raise ApprovalRequired("action source is unavailable or withdrawn")
        sources.append({"contract_id": contract.contract_id, "version": contract.current_version,
                        "sha256": version.sha256, "meta_hash": _digest(contract.meta), "status": contract.status})
    by_id = {source["contract_id"]: source for source in sources}
    for citation in action.get("citations", []):
        source = by_id.get(citation.get("contract_id"))
        if not source or citation.get("version") != source["version"]:
            raise ApprovalRequired("action cites a stale source version")
    return sources, contracts


def _basis(s, action):
    """Pin linked evidence, including amounts and uncertainty, rather than only availability."""
    result = []
    invalid = {"withdrawn", "superseded", "dismissed", "challenged", "rejected", "disputed"}
    for kind, field in (("finding", "related_finding_ids"), ("violation", "related_violation_ids")):
        for rid in sorted(set(action.get(field, []))):
            row = s.get(Record, repo._pk(current().company_id, rid))
            if (not row or row.kind != kind or row.company_id != current().company_id or row.scenario_id
                or row.status in invalid or row.data.get("status") in invalid
                or (action.get("contract_id") != "cross" and row.contract_id != action.get("contract_id"))):
                raise ApprovalRequired("linked action basis is unavailable, disputed or dismissed")
            result.append({"id": rid, "kind": kind, "version": row.version, "status": row.status,
                           "contract_id": row.contract_id, "revision": _digest(row.data)})
    return result


def _preconditions(s, action, tool, payload, contracts):
    if tool == "send_gmail":
        recipient = payload["to"]
        if not _EMAIL.fullmatch(recipient) or "\r" in payload["subject"] or "\n" in payload["subject"]:
            raise ApprovalRequired("action requires a single valid recipient and subject")
        if not payload["body"].strip():
            raise ApprovalRequired("action body is empty")
        # Notice addresses must be evidenced, rather than inferred from a party name/domain.
        company = repo.company(current().company_id)
        own_names = {str(name).strip().casefold() for name in
                     [company.name if company else "", (company.context or {}).get("name", "") if company else ""]}
        evidence = []
        for contract in contracts:
            evidence.extend(party for party in contract.meta.get("parties", [])
                            if party.get("role") != "company" and
                            str(party.get("name", "")).strip().casefold() not in own_names)
        for contract in contracts:
            rows = s.scalars(select(Record).where(Record.company_id == current().company_id,
                Record.kind == "extraction", Record.contract_id == contract.contract_id,
                Record.version == contract.current_version, Record.scenario_id.is_(None))).all()
            evidence.extend(row.data.get("notice", {}) for row in rows)
        if action.get("kind") == "escalation_memo":
            evidence.append(company.context if company else {})
        addresses = {value.casefold() for value in _EMAIL_IN_TEXT.findall(json.dumps(evidence))}
        if recipient.casefold() not in addresses:
            raise ApprovalRequired("recipient is not a documented contract notice/contact address")
    if action.get("kind") == "payment_instruction":
        # Existing free-text drafts contain no typed beneficiary/amount authorization.
        raise ApprovalRequired("payment instructions require verified structured financial authorization")


def _replace(s, row, data):
    old = row.data
    result = s.execute(update(Record).where(Record.id == row.id, Record.company_id == current().company_id,
        Record.kind == "action", Record.status == row.status, Record.data == old).values(
            data=data, status=data["status"], updated_at=datetime.utcnow()),
        execution_options={"synchronize_session": False})
    if result.rowcount != 1:
        raise ApprovalRequired("action changed concurrently; reload before review")


def approve(aid: str, *, reviewer: str) -> dict:
    _require_admin()
    if not reviewer:
        raise ApprovalRequired("admin review is required")
    with db() as s:
        row = _row(s, aid)
        action = row.data
        if row.status not in {"draft", "approved"} or action.get("approval_execution", {}).get("state"):
            raise ApprovalRequired("action is consumed or no longer reviewable")
        tool, payload = action_payload(action)
        sources, contracts = _sources(s, action)
        basis = _basis(s, action)
        _preconditions(s, action, tool, payload, contracts)
        now = datetime.now(timezone.utc)
        binding = {"id": new_id("approval"), "company_id": current().company_id, "action_id": aid,
                   "action_revision": _revision(action), "record_version": row.version, "tool": tool,
                   "payload_hash": _digest(payload), "sources": sources, "basis": basis, "reviewer": reviewer,
                   "approved_at": now.isoformat(), "expires_at": (now + _LIFETIME).isoformat()}
        data = {**action, "status": "approved", "approved_by": reviewer, "approved_at": now.isoformat(),
                "approval": binding, "approval_execution": {}}
        _replace(s, row, data)
    return data


def edit(aid: str, updates: dict, *, reviewer: str) -> dict:
    _require_admin()
    with db() as s:
        row = _row(s, aid)
        if row.status not in {"draft", "approved"} or row.data.get("approval_execution", {}).get("state"):
            raise ApprovalRequired("only unexecuted drafts or approvals can be edited")
        data = {**row.data, **updates, "status": "draft", "approval": None,
                "approval_execution": {}, "edited_by": reviewer}
        _replace(s, row, data)
    return data


def reject(aid: str, *, reviewer: str) -> dict:
    _require_admin()
    with db() as s:
        row = _row(s, aid)
        if row.status not in {"draft", "approved"} or row.data.get("approval_execution", {}).get("state"):
            raise ApprovalRequired("executing or consumed actions cannot be rejected")
        data = {**row.data, "status": "rejected", "approval": None, "rejected_by": reviewer}
        _replace(s, row, data)
    return data


def claim(aid: str | None, tool: str, payload: dict) -> str:
    """Linearize a one-shot dispatch authorization, not provider delivery or future source edits."""
    if not aid:
        raise ApprovalRequired("this tool needs a payload-bound admin approval")
    _require_admin()
    with db() as s:
        # Ingest, deletion and linked-basis writes take the same short tenant lock.
        # Commit the durable lease before releasing this lock and contacting a provider.
        s.scalar(select(Company).where(Company.id == current().company_id).with_for_update())
        row = _row(s, aid)
        action = row.data
        binding = action.get("approval") or {}
        if row.status != "approved" or action.get("status") != "approved" or not binding:
            raise ApprovalRequired("action needs a new payload-bound admin approval")
        if action.get("approval_execution", {}).get("state"):
            raise ApprovalRequired("approval is already executing or consumed")
        _validate_binding(s, row, aid, tool, payload)
        execution_id = new_id("execution")
        data = {**action, "approval_execution": {"id": execution_id, "state": "executing",
                "idempotency_key": binding["id"], "started_at": datetime.now(timezone.utc).isoformat()}}
        _replace(s, row, data)
    return execution_id


def _validate_binding(s, row, aid, tool, payload):
    action, binding = row.data, row.data.get("approval") or {}
    try:
        expired = datetime.fromisoformat(binding["expires_at"]) <= datetime.now(timezone.utc)
    except (KeyError, TypeError, ValueError):
        expired = True
    sources, contracts = _sources(s, action)
    expected_tool, expected_payload = action_payload(action)
    if (row.status != "approved" or action.get("status") != "approved" or expired
        or binding.get("company_id") != current().company_id or binding.get("action_id") != aid
        or binding.get("tool") != tool or tool != expected_tool or binding.get("sources") != sources
        or binding.get("basis") != _basis(s, action) or binding.get("action_revision") != _revision(action)
        or binding.get("record_version") != row.version or binding.get("payload_hash") != _digest(payload)
        or _digest(payload) != _digest(expected_payload)):
        raise ApprovalRequired("approval payload, action or source changed, or approval expired")
    _preconditions(s, action, tool, payload, contracts)
    return binding


def revalidate_claim(aid: str, execution_id: str, tool: str, payload: dict) -> dict:
    """Cancellation/source recheck immediately before dispatch, without holding network locks.

    A later concurrent source edit cannot retract an already dispatched provider request.
    The registry consumes this claim even if this final check refuses dispatch.
    """
    _require_admin()
    with db() as s:
        row = _row(s, aid)
        execution = row.data.get("approval_execution", {})
        if execution.get("id") != execution_id or execution.get("state") != "executing":
            raise ApprovalRequired("execution claim is unavailable")
        return _validate_binding(s, row, aid, tool, payload)


@contextmanager
def dispatch_context(aid: str, execution_id: str, tool: str, payload: dict):
    token = _DISPATCH.set((aid, execution_id, tool, payload))
    try:
        yield
    finally:
        _DISPATCH.reset(token)


def dispatch_sources(aid: str, tool: str, payload: dict) -> list[dict]:
    dispatch = _DISPATCH.get()
    if not dispatch or (dispatch[0], dispatch[2], dispatch[3]) != (aid, tool, payload):
        raise ApprovalRequired("tool requires its registry dispatch claim")
    return revalidate_claim(*dispatch)["sources"]


def _live_leases(s, company_id):
    return s.scalars(select(Record).where(Record.company_id == company_id, Record.kind == "action",
        Record.scenario_id.is_(None), Record.data["approval_execution"]["state"].as_string() == "executing")).all()


def assert_source_mutation_allowed(s, company_id: str, contract_id: str, *, execution_id: str | None = None) -> None:
    """Call under the Company row lock, before altering a source or deleting its records.

    Leases are durable and never expire automatically: a crashed dispatch requires manual
    reconciliation. Only its own local amendment may write the leased source, using the
    random execution ID and the registry's internal dispatch context together.
    """
    owned = False
    for row in _live_leases(s, company_id):
        action = row.data
        binding = action.get("approval") or {}
        affected = action.get("contract_id") == "cross" or any(
            source.get("contract_id") == contract_id for source in binding.get("sources", []))
        if not affected:
            continue
        dispatch = _DISPATCH.get()
        execution = action.get("approval_execution", {})
        own_amendment = (execution_id and dispatch and current().company_id == company_id
            and dispatch == (action.get("id"), execution_id, "apply_amendment", {"action_id": action.get("id")})
            and execution.get("id") == execution_id and binding.get("tool") == "apply_amendment"
            and action.get("contract_id") == contract_id)
        if not own_amendment:
            raise ApprovalRequired("contract source is leased by an executing action; reconcile or wait before changing it")
        _require_admin()
        _validate_binding(s, row, action["id"], "apply_amendment", {"action_id": action["id"]})
        owned = True
    if execution_id and not owned:
        raise ApprovalRequired("amendment source mutation requires its active dispatch lease")


def assert_basis_mutation_allowed(s, company_id: str, record_id: str, kind: str) -> None:
    """Call under the Company row lock before changing/removing a linked evidence record."""
    logical_id = record_id.removeprefix(f"{company_id}|")
    for row in _live_leases(s, company_id):
        basis = (row.data.get("approval") or {}).get("basis", [])
        if any(item.get("id") == logical_id and item.get("kind") == kind for item in basis):
            raise ApprovalRequired("action basis is leased by an executing action; reconcile or wait before changing it")


def finish(aid: str, execution_id: str, *, ok: bool, tool: str, dispatched: bool = True) -> None:
    with db() as s:
        row = _row(s, aid)
        execution = row.data.get("approval_execution", {})
        if execution.get("id") != execution_id or execution.get("state") != "executing":
            raise ApprovalRequired("execution claim is unavailable")
        state = "completed" if ok else "ambiguous" if dispatched else "cancelled"
        data = {**row.data, "approval_execution": {**execution, "state": state,
                "finished_at": datetime.now(timezone.utc).isoformat()}}
        if ok:
            data["status"] = "applied" if tool == "apply_amendment" else "sent"
            if tool == "apply_amendment":
                data["application_effect"] = "local proposal only; counterparty agreement is not established"
        _replace(s, row, data)
