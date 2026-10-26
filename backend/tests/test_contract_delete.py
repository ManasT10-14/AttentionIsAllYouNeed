"""Deletion integration tests use only synthetic SQLite records and temporary uploads."""
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from odin.core.context import run_ctx
from odin.db import repo
from odin.db.tables import (
    AgentMessageRow,
    Base,
    ClauseRow,
    Company,
    Contract,
    ContractVersion,
    Record,
    Run,
)
from odin.services import contracts as deletion
from odin.services import runs
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    @contextmanager
    def db():
        with factory() as s:
            try:
                yield s
                s.commit()
            except Exception:
                s.rollback()
                raise
    for module in (deletion, runs, repo):
        monkeypatch.setattr(module, "db", db)
    root = tmp_path / "uploads"
    monkeypatch.setattr(deletion, "DATA_DIR", root)
    files = []
    def record(s, identity, artifact_kind, cid=None, **data):
        s.add(Record(id="A|"+identity, company_id="A", kind=artifact_kind, contract_id=cid,
                     data={"id": identity, **data}))
    with db() as s:
        for tenant, cid in [("A", "C1"), ("A", "C2"), ("B", "C1")]:
            s.add(Company(id=tenant)) if cid == "C1" else None
            s.add(Contract(id=tenant+cid, company_id=tenant, contract_id=cid, title=tenant+cid))
            folder = root / tenant / cid / "v1"
            folder.mkdir(parents=True)
            original, pdf = folder/"original.pdf", folder/"document.pdf"
            original.write_bytes(b"synthetic-original")
            pdf.write_bytes(b"synthetic-pdf")
            files.extend([original, pdf])
            s.add(ContractVersion(id=tenant+cid, company_id=tenant, contract_id=cid, version=1,
                  file_path=str(original), pdf_path=str(pdf), sha256="a"*64, text="Synthetic clause"))
            s.add(ClauseRow(id=tenant+cid, company_id=tenant, contract_id=cid, version=1, number="1", text="Synthetic clause", char_start=0, char_end=16))
        record(s,"ext1","extraction","C1")
        record(s,"f1","finding","C1",claim="Own finding")
        record(s,"fcross","finding","cross",other_contract_ids=["C1","C2"])
        record(s,"v1","verification",finding_id="fcross")
        record(s,"r1","ruling",finding_id="fcross")
        record(s,"dep","dependency",from_contract="C2",to_contract="C1")
        record(s,"a2","action","C2",related_finding_ids=["fcross"])
        record(s,"f2","finding","C2",claim="Mentions C1 in plain text only")
        record(s,"safe-action","action","C2",related_finding_ids=["f2"])
        record(s,"company","report",kind="company")
        # Report payload kind is separate from Record.kind.
        record(s,"current2","report","C2",risks=[{"other_contract_ids":["C1"]}])
        record(s,"history","report_run",run_id="old",generated_at="2026-01-01",report={"contract_id":"C1"})
        record(s,"revision","report_revision","C1",run_id="old",kind="contract")
        record(s,"evt","event",contract_ids=["C1","C2"],raw="Original email about C1 and C2")
        s.add(AgentMessageRow(id="msg",company_id="A",run_id="old",sender="synth",receiver="all",kind="report",contract_id="C1",summary="Saved output"))
        s.add(Record(id="B|ext",company_id="B",kind="extraction",contract_id="C1",data={"id":"other-tenant"}))
        s.flush()
    def remove():
        with run_ctx("A"):
            return deletion.delete_contract("A","C1","C1","actor")
    return SimpleNamespace(db=db, factory=factory, files=files, root=root, remove=remove)


def test_delete_removes_search_and_dependent_live_data_but_preserves_history(workspace):
    result = workspace.remove()
    assert result["deleted"] and result["removed_files"] == 2
    with workspace.db() as s:
        assert s.get(Contract,"AC1") is None
        assert s.get(ClauseRow,"AC1") is None
        assert s.get(ContractVersion,"AC1") is None
        assert s.get(Contract,"AC2") and s.get(Contract,"BC1")
        assert s.get(ClauseRow,"AC2") and s.get(ClauseRow,"BC1")
        for identity in ("ext1","f1","fcross","v1","r1","dep","a2","current2","company"):
            assert s.get(Record,"A|"+identity) is None, identity
        for identity in ("f2","safe-action","history","revision"):
            assert s.get(Record,"A|"+identity), identity
        assert s.get(Record,"B|ext") and s.get(AgentMessageRow,"msg")
        event = s.get(Record,"A|evt").data
        assert event["contract_ids"] == ["C2"] and event["deleted_contract_ids"] == ["C1"]
        assert event["raw"] == "Original email about C1 and C2"
        assert s.scalar(select(Record).where(Record.kind=="contract_deletion"))
    assert not any(p.exists() for p in workspace.files[:2])
    assert all(p.exists() for p in workspace.files[2:])


def test_running_agent_blocks_deletion_without_mutation(workspace):
    with workspace.db() as s:
        s.add(Run(id="busy",company_id="A",kind="analysis",status="running"))
    with pytest.raises(HTTPException) as exc:
        workspace.remove()
    assert exc.value.status_code == 409
    assert all(p.exists() for p in workspace.files)
    with workspace.db() as s:
        assert s.get(Contract,"AC1")


def test_other_tenant_run_does_not_block(workspace):
    with workspace.db() as s:
        s.add(Run(id="busy-B",company_id="B",kind="analysis",status="running"))
    assert workspace.remove()["deleted"]


def test_confirmation_and_company_scope_are_enforced(workspace):
    with pytest.raises(HTTPException) as exc:
        deletion.delete_contract("A","C1","C2","actor")
    assert exc.value.status_code == 400
    with pytest.raises(HTTPException) as exc:
        deletion.delete_contract("B","C2","C2","actor")
    assert exc.value.status_code == 404
    assert all(p.exists() for p in workspace.files)


def test_database_failure_restores_uploads_and_rolls_back(workspace, monkeypatch):
    @contextmanager
    def failing_db():
        with workspace.factory() as s:
            try:
                yield s
                s.flush()
                raise RuntimeError("commit failure")
            finally:
                s.rollback()
    monkeypatch.setattr(deletion,"db",failing_db)
    with pytest.raises(RuntimeError,match="commit failure"):
        workspace.remove()
    assert all(p.exists() for p in workspace.files)
    with workspace.db() as s:
        assert s.get(Contract,"AC1") and s.get(Record,"A|ext1")


def test_paths_outside_tenant_are_not_deleted(workspace, tmp_path):
    outside = tmp_path/"outside.pdf"
    outside.write_bytes(b"keep")
    with workspace.db() as s:
        row=s.get(ContractVersion,"AC1")
        row.file_path=str(outside)
    result=workspace.remove()
    assert result["cleanup_warnings"] and outside.read_bytes()==b"keep"


def test_delete_route_requires_admin():
    from odin.api.routes import router
    route=next(r for r in router.routes if r.path=="/contracts/{cid}" and "DELETE" in r.methods)
    dependency=next(d.call for d in route.dependant.dependencies if d.name=="u")
    with pytest.raises(HTTPException) as exc:
        dependency(SimpleNamespace(role="viewer"))
    assert exc.value.status_code==403


def test_reupload_does_not_reuse_deleted_version_numbers(workspace, monkeypatch):
    from odin.ingest import service as ingest
    workspace.remove()
    monkeypatch.setattr(ingest,"db",workspace.db)
    monkeypatch.setattr(ingest,"DATA_DIR",workspace.root)
    monkeypatch.setattr(ingest.HOOKS,"on_ingest",lambda *a,**kw: None)
    cover=SimpleNamespace(contract_id="C1", version=None, title="Replacement", type="other",
                          model_dump=lambda **kw: {"contract_id":"C1"})
    monkeypatch.setattr(ingest,"parse_pdf",lambda *a,**kw: SimpleNamespace(cover=cover,warnings=[],clauses=[],text="Replacement"))
    result=ingest.ingest_contract("A","new.pdf",b"synthetic-pdf")
    assert result.version==2 and not result.duplicate
    with workspace.db() as s:
        assert s.scalar(select(ContractVersion).where(ContractVersion.company_id=="A",ContractVersion.contract_id=="C1")).version==2
        assert s.get(Record,"A|history")  # retained historical report remains unchanged
