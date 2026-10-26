"""Company-scoped contract deletion; historical run evidence is retained."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException
from odin.core import bus
from odin.core.config import DATA_DIR
from odin.db.session import db
from odin.db.tables import ClauseRow, Company, Contract, ContractVersion, Record, Run
from sqlalchemy import delete, select

log = logging.getLogger(__name__)

HISTORY = {"report_run", "report_revision", "contract_deletion"}
DERIVED = {"finding", "dependency", "violation", "verification", "ruling", "action", "alert", "clarification"}
CONTRACT_KEYS = {"contract_id", "contract_ids", "other_contract_ids", "from_contract", "to_contract", "contract"}
LINK_KEYS = {"finding_id", "finding_ids", "related_finding_ids", "violation_id", "related_violation_ids", "action_id", "ruling_id"}


def references(value, targets: set[str], keys: set[str]) -> bool:
    if isinstance(value, list):
        return any(references(v, targets, keys) for v in value)
    if not isinstance(value, dict):
        return False
    for key, val in value.items():
        if key in keys:
            if isinstance(val, str) and val in targets:
                return True
            if isinstance(val, list) and any(isinstance(v, str) and v in targets for v in val):
                return True
        if isinstance(val, (dict, list)) and references(val, targets, keys):
            return True
    return False


def deletion_ids(rows, cid: str) -> set[str]:
    """Follow exact structured links, never title/text substring matches."""
    doomed = {r.id for r in rows if r.kind not in HISTORY and r.kind != "event" and (
        r.contract_id == cid or
        (r.kind == "report" and (r.data.get("kind") == "company" or references(r.data, {cid}, CONTRACT_KEYS))) or
        (r.kind in DERIVED and references(r.data, {cid}, CONTRACT_KEYS)))}
    while True:
        logical = {r.data.get("id") for r in rows if r.id in doomed} - {None}
        linked = {r.id for r in rows if r.kind in (DERIVED | {"report"}) and references(r.data, logical, LINK_KEYS)}
        if linked <= doomed:
            return doomed
        doomed |= linked


def safe_upload_path(raw: str, company_id: str) -> Path | None:
    root = DATA_DIR.resolve()
    tenant = (root / company_id).resolve()
    path = Path(raw).resolve()
    if tenant == root or not tenant.is_relative_to(root) or not path.is_relative_to(tenant) or path == tenant:
        return None
    return path


def delete_contract(company_id: str, cid: str, confirmation: str, actor_id: str) -> dict:
    if confirmation != cid:
        raise HTTPException(400, "Type the exact contract ID to confirm deletion")
    warnings, removed_files = [], 0
    staged = []
    from odin.core.models import new_id
    quarantine = DATA_DIR / company_id / "_deletions" / new_id("files")
    try:
        with db() as s:
            # Run creation and final upload persistence use the same tenant lock.
            s.scalar(select(Company).where(Company.id == company_id).with_for_update())
            contract = s.scalar(select(Contract).where(Contract.company_id == company_id, Contract.contract_id == cid))
            if not contract:
                raise HTTPException(404, "Contract not found")
            from odin.services.approvals import ApprovalRequired, assert_source_mutation_allowed
            try:
                assert_source_mutation_allowed(s, company_id, cid)
            except ApprovalRequired as exc:
                raise HTTPException(409, str(exc)) from exc
            if s.scalar(select(Run.id).where(Run.company_id == company_id, Run.status == "running").limit(1)):
                raise HTTPException(409, "Wait for running agents to finish before deleting a contract")
            # Freeze any surviving older company report before its latest copy is invalidated.
            from odin.services.runs import archive_legacy_report
            archive_legacy_report(company_id)
            rows = list(s.scalars(select(Record).where(Record.company_id == company_id)))
            doomed = deletion_ids(rows, cid)
            versions = list(s.scalars(select(ContractVersion).where(ContractVersion.company_id == company_id, ContractVersion.contract_id == cid)))
            others = list(s.scalars(select(ContractVersion).where(
                (ContractVersion.company_id != company_id) | (ContractVersion.contract_id != cid))))
            shared_paths = {p for v in others for p in (v.file_path, v.pdf_path)}
            shared_hashes = {v.sha256 for v in others if v.company_id == company_id}
            paths = {p for v in versions for p in (v.file_path, v.pdf_path)}
            for v in versions:
                if v.sha256 not in shared_hashes:
                    stage = DATA_DIR / company_id / "_staging" / v.sha256[:16]
                    paths.update([str(stage / Path(v.file_path).name), str(stage / "document.pdf")])
            for raw in paths:
                path = safe_upload_path(raw, company_id)
                if path is None or any(Path(p).resolve() == path for p in shared_paths):
                    warnings.append("A file outside the exclusive upload location was retained.")
                    continue
                try:
                    if path.is_file():
                        quarantine.mkdir(parents=True, exist_ok=True)
                        backup = quarantine / str(len(staged))
                        path.replace(backup)
                        staged.append((path, backup))
                        removed_files += 1
                except OSError:
                    log.warning("Unable to stage a contract upload for deletion", exc_info=True)
                    warnings.append("An uploaded file could not be removed; database deletion will still complete.")
            for row in rows:
                if row.id in doomed:
                    s.delete(row)
                elif row.kind == "event" and cid in (row.data.get("contract_ids") or []):
                    row.data = {**row.data, "contract_ids": [c for c in row.data["contract_ids"] if c != cid],
                                "deleted_contract_ids": sorted(set(row.data.get("deleted_contract_ids", [])) | {cid})}
                elif row.kind == "owners" and cid in row.data.get("map", {}):
                    row.data = {**row.data, "map": {k: v for k, v in row.data["map"].items() if k != cid}}
            s.execute(delete(ClauseRow).where(ClauseRow.company_id == company_id, ClauseRow.contract_id == cid))
            s.execute(delete(ContractVersion).where(ContractVersion.company_id == company_id, ContractVersion.contract_id == cid))
            s.delete(contract)
            from odin.core.models import new_id
            identity = new_id("deleted")
            s.add(Record(id=f"{company_id}|{identity}", company_id=company_id, kind="contract_deletion", contract_id=cid, data={
                "id": identity, "contract_id": cid, "title": contract.title, "actor_id": actor_id,
                "deleted_at": datetime.utcnow().isoformat(), "last_version": contract.current_version,
                "removed_records": len(doomed)}))
    except Exception:
        for original, backup in reversed(staged):
            if backup.exists() and not original.exists():
                backup.replace(original)
        raise
    # Commit succeeded: purge only the quarantined files, never a newly re-uploaded version.
    for original, backup in staged:
        try:
            backup.unlink(missing_ok=True)
        except OSError:
            warnings.append("An uploaded file remains in deletion quarantine; cleanup is incomplete.")
    result = {"deleted": True, "contract_id": cid, "removed_records": len(doomed),
              "removed_files": removed_files, "cleanup_warnings": sorted(set(warnings)),
              "history_retained": True, "reports_invalidated": True}
    bus.publish(company_id, "contract_deleted", result)
    return result
