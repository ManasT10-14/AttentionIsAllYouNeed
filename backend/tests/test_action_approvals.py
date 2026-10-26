"""Approval boundary regressions, isolated database and sandboxed effects only."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest
from odin.core.context import run_ctx
from odin.core.hooks import HOOKS
from odin.db import repo, session
from odin.db.tables import (
    AgentMessageRow,
    ClauseRow,
    Company,
    Contract,
    ContractVersion,
    Record,
    Run,
    ToolCall,
)
from odin.tools.core import GmailArgs
from odin.tools.registry import ApprovalRequired, ToolRegistry
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def store(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'approval.db'}", connect_args={"check_same_thread": False})
    for table in (Company.__table__, Contract.__table__, ContractVersion.__table__, Record.__table__,
                  ToolCall.__table__, ClauseRow.__table__, Run.__table__, AgentMessageRow.__table__):
        table.create(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(session, "_factory", lambda: factory)
    monkeypatch.setattr(HOOKS, "guards", [])
    monkeypatch.setattr(HOOKS, "evals", [])
    with session.db() as s:
        s.add(Company(id="a", name="Aurora"))
        s.add(Contract(id="contract-a", company_id="a", contract_id="C01", current_version=1,
                       meta={"parties": [{"name": "Forge", "email": "notice@forge.test"}]}))
        s.add(ContractVersion(id="version-a", company_id="a", contract_id="C01", version=1,
                              sha256="source-one", file_path="", pdf_path="", text=""))
        s.add(Record(id="a|act", company_id="a", kind="action", contract_id="C01", status="draft", data={
            "id": "act", "contract_id": "C01", "kind": "breach_notice", "status": "draft",
            "to": "notice@forge.test", "subject": "Notice", "body_md": "Please cure the breach.",
            "citations": [], "related_finding_ids": []}))
    yield factory
    engine.dispose()


def registry(effect):
    reg = ToolRegistry()
    effect.__name__ = "send_gmail"
    reg.tool(args=GmailArgs, scope="external_send", side_effect=True, requires_approval=True)(effect)
    reg.grant("system", "send_gmail")
    return reg


def approve():
    from odin.services import approvals
    return approvals.approve("act", reviewer="admin@aurora.test")


def payload():
    return {"to": "notice@forge.test", "subject": "Notice", "body": "Please cure the breach."}


def test_status_only_legacy_approval_cannot_authorize_send(store):
    with run_ctx("a", user_role="admin"):
        repo.set_status("act", "approved")
        reg = registry(lambda args: {"sent": True})
        with pytest.raises(ApprovalRequired):
            reg.invoke("system", "send_gmail", payload(), approval_id="act")


@pytest.mark.parametrize("field,value", [("to", "other@forge.test"), ("body", "changed"),
                                         ("subject", "changed"), ("thread_id", "different")])
def test_approval_rejects_changed_payload(store, field, value):
    with run_ctx("a", user_role="admin"):
        approve()
        reg = registry(lambda args: pytest.fail("unapproved effect"))
        changed = {**payload(), field: value}
        with pytest.raises(ApprovalRequired):
            reg.invoke("system", "send_gmail", changed, approval_id="act")


def test_two_concurrent_calls_produce_one_effect(store):
    effects = []
    reg = registry(lambda args: effects.append(args.body) or {"sent": True})
    with run_ctx("a", user_role="admin"):
        approve()
    def send():
        with run_ctx("a", user_role="admin"):
            try:
                return reg.invoke("system", "send_gmail", payload(), approval_id="act")
            except ApprovalRequired:
                return "denied"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: send(), range(2)))
    assert len(effects) == 1 and results.count("denied") == 1
    with run_ctx("a"):
        assert repo.get("action", "act")["approval_execution"]["state"] == "completed"


@pytest.mark.parametrize("mutation", ["source", "expiry", "withdrawal", "edit", "tool"])
def test_stale_or_wrong_approval_blocks_effect(store, mutation):
    with run_ctx("a", user_role="admin"):
        approve()
        with session.db() as s:
            row = s.get(Record, "a|act")
            data = deepcopy(row.data)
            if mutation == "source":
                s.get(ContractVersion, "version-a").sha256 = "changed-source"
            elif mutation == "expiry":
                data["approval"]["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
            elif mutation == "withdrawal":
                row.status = data["status"] = "rejected"
            elif mutation == "edit":
                data["body_md"] = "changed stored action"
            else:
                data["approval"]["tool"] = "apply_amendment"
            row.data = data
        with pytest.raises(ApprovalRequired):
            registry(lambda args: pytest.fail("stale effect")).invoke("system", "send_gmail", payload(), approval_id="act")


def test_effect_error_consumes_approval_and_cannot_be_reapproved(store):
    def error(args):
        raise TimeoutError("delivery outcome unknown")
    reg = registry(error)
    with run_ctx("a", user_role="admin"):
        approve()
        with pytest.raises(TimeoutError):
            reg.invoke("system", "send_gmail", payload(), approval_id="act")
        with pytest.raises(ApprovalRequired):
            reg.invoke("system", "send_gmail", payload(), approval_id="act")
        with pytest.raises(ApprovalRequired):
            approve()
        assert repo.get("action", "act")["approval_execution"]["state"] == "ambiguous"


def test_audit_redacts_nested_args_summary_and_error(store, monkeypatch):
    canary = "SyntheticApprovalSecret987654"
    monkeypatch.setenv("APPROVAL_API_KEY", canary)
    reg = ToolRegistry()
    from pydantic import BaseModel
    class Args(BaseModel):
        nested: dict
    @reg.tool(args=Args, scope="read_state")
    def inspect(args):
        raise ValueError(canary)
    reg.grant("system", "inspect")
    with run_ctx("a"):
        with pytest.raises(ValueError):
            reg.invoke("system", "inspect", {"nested": {"api_key": "opaque", "text": canary}})
    with session.db() as s:
        row = s.scalar(select(ToolCall))
        assert canary not in str(row.args) + row.result_summary and "opaque" not in str(row.args)


def test_edit_invalidates_approval_and_reviewer_is_required(store):
    from odin.services import approvals
    with run_ctx("a", user_role="admin"):
        approved = approve()
        assert approved["approval"]["reviewer"] == "admin@aurora.test"
        edited = approvals.edit("act", {"body_md": "A revised notice"}, reviewer="admin@aurora.test")
        assert edited["status"] == "draft" and edited["approval"] is None
        with pytest.raises(ApprovalRequired):
            registry(lambda args: pytest.fail("invalidated effect")).invoke("system", "send_gmail", payload(), approval_id="act")
    with run_ctx("a", user_role="viewer"):
        with pytest.raises(ApprovalRequired):
            approve()


def test_recipient_domain_alone_does_not_authorize_other_contact(store):
    with run_ctx("a", user_role="admin"):
        repo.set_status("act", "draft", to="attacker@forge.test")
        with pytest.raises(ApprovalRequired):
            approve()


def test_notice_cannot_be_sent_to_own_company_contact(store):
    with session.db() as s:
        contract = s.get(Contract, "contract-a")
        contract.meta = {"parties": [{"name": "Forge", "role": "counterparty", "email": "notice@forge.test"},
                                     {"name": "Aurora", "role": "company", "email": "admin@aurora.test"}]}
    with run_ctx("a", user_role="admin"):
        repo.set_status("act", "draft", to="admin@aurora.test")
        with pytest.raises(ApprovalRequired):
            approve()


def test_amendment_approval_does_not_authorize_mail_or_changed_redlines(store):
    from odin.services import approvals
    with run_ctx("a", user_role="admin"):
        repo.set_status("act", "draft", kind="amendment", redlines=[{"clause_number": "1", "before": "a", "after": "b"}])
        approve()
        with pytest.raises(ApprovalRequired):
            registry(lambda args: pytest.fail("unrelated mail")).invoke("system", "send_gmail", payload(), approval_id="act")
        repo.set_status("act", "approved", redlines=[{"clause_number": "1", "before": "a", "after": "c"}])
        with pytest.raises(ApprovalRequired):
            approvals.claim("act", "apply_amendment", {"action_id": "act"})


def test_cross_tenant_approval_is_not_visible(store):
    with run_ctx("a", user_role="admin"):
        approve()
    with run_ctx("other", user_role="admin"):
        with pytest.raises(ApprovalRequired):
            registry(lambda args: pytest.fail("foreign effect")).invoke("system", "send_gmail", payload(), approval_id="act")


def test_unknown_attachment_arguments_cannot_use_approval(store):
    from pydantic import ValidationError
    with run_ctx("a", user_role="admin"):
        approve()
        with pytest.raises(ValidationError):
            registry(lambda args: pytest.fail("unexpected attachment")).invoke("system", "send_gmail",
                {**payload(), "attachments": ["changed.pdf"]}, approval_id="act")


@pytest.mark.parametrize("mutation", ["withdrawal", "hash"])
def test_source_change_between_claim_and_dispatch_consumes_without_effect(store, monkeypatch, mutation):
    from odin.services import approvals
    real_claim = approvals.claim
    effects = []
    def interleaved_claim(*args, **kwargs):
        execution_id = real_claim(*args, **kwargs)
        with session.db() as s:
            if mutation == "withdrawal":
                s.get(Contract, "contract-a").status = "withdrawn"
            else:
                s.get(ContractVersion, "version-a").sha256 = "changed-after-claim"
        return execution_id
    monkeypatch.setattr(approvals, "claim", interleaved_claim)
    with run_ctx("a", user_role="admin"):
        approve()
        with pytest.raises(ApprovalRequired):
            registry(lambda args: effects.append(args) or {}).invoke("system", "send_gmail", payload(), approval_id="act")
        assert not effects
        assert repo.get("action", "act")["approval_execution"]["state"] == "cancelled"
        with pytest.raises(ApprovalRequired):
            approve()


@pytest.mark.parametrize("role", ["viewer", "system"])
def test_approval_id_cannot_be_used_by_non_admin_dispatch(store, role):
    with run_ctx("a", user_role="admin"):
        approve()
    with run_ctx("a", user_role=role):
        with pytest.raises(ApprovalRequired):
            registry(lambda args: pytest.fail("non-admin effect")).invoke("system", "send_gmail", payload(), approval_id="act")


@pytest.mark.parametrize("mutation", ["dismissed_violation", "financial_basis"])
def test_changed_linked_basis_invalidates_approval(store, mutation):
    with session.db() as s:
        s.add(Record(id="a|finding", company_id="a", kind="finding", contract_id="C01", status="open",
                     data={"id": "finding", "status": "open", "amount": 100}))
        s.add(Record(id="a|violation", company_id="a", kind="violation", contract_id="C01", status="open",
                     data={"id": "violation", "status": "open", "amount": 100}))
    with run_ctx("a", user_role="admin"):
        repo.set_status("act", "draft", related_finding_ids=["finding"], related_violation_ids=["violation"])
        approve()
        if mutation == "dismissed_violation":
            repo.set_status("violation", "dismissed")
        else:
            repo.set_status("finding", "open", amount=200)
        with pytest.raises(ApprovalRequired):
            registry(lambda args: pytest.fail("stale basis effect")).invoke("system", "send_gmail", payload(), approval_id="act")


def test_amendment_checks_approved_version_at_its_actual_source_read(store, monkeypatch):
    from types import SimpleNamespace

    from odin.ingest import service as ingest
    from odin.tools.core import AmendArgs, apply_amendment
    effects = []
    monkeypatch.setattr(repo, "contract", lambda cid: SimpleNamespace(current_version=2, meta={}, title="Changed"))
    monkeypatch.setattr(repo, "clauses", lambda *a, **k: [])
    monkeypatch.setattr(ingest, "ingest_contract", lambda *a, **k: effects.append(a) or
                        SimpleNamespace(version=3, is_update=False, contract_id="C01", warnings=[]))
    reg = ToolRegistry()
    reg.tool(args=AmendArgs, scope="file_write", side_effect=True, requires_approval=True)(apply_amendment)
    reg.grant("system", "apply_amendment")
    with run_ctx("a", user_role="admin"):
        repo.set_status("act", "draft", kind="amendment", redlines=[{"clause_number": "1", "before": "a", "after": "b"}])
        approve()
        with pytest.raises(ApprovalRequired):
            reg.invoke("system", "apply_amendment", {"action_id": "act"}, approval_id="act")
    assert not effects


def test_delete_rejects_source_with_live_execution_lease(store, monkeypatch, tmp_path):
    from fastapi import HTTPException
    from odin.services import approvals, contracts
    monkeypatch.setattr(contracts, "DATA_DIR", tmp_path)
    with run_ctx("a", user_role="admin"):
        approve()
        approvals.claim("act", "send_gmail", {**payload(), "thread_id": None})
        with pytest.raises(HTTPException) as refused:
            contracts.delete_contract("a", "C01", "C01", "admin")
        assert refused.value.status_code == 409
        assert repo.contract("C01").current_version == 1


@pytest.mark.parametrize("forged_internal_token", [False, True])
def test_upload_rejects_source_with_live_execution_lease(store, monkeypatch, tmp_path, forged_internal_token):
    from types import SimpleNamespace

    from odin.core.models import CoverMeta
    from odin.ingest import service as ingest
    from odin.services import approvals
    monkeypatch.setattr(ingest, "DATA_DIR", tmp_path)
    monkeypatch.setattr(ingest, "parse_pdf", lambda *a, **k: SimpleNamespace(
        cover=CoverMeta(contract_id="C01", title="Synthetic update"), warnings=[], clauses=[], text="Synthetic update"))
    with run_ctx("a", user_role="admin"):
        approve()
        execution_id = approvals.claim("act", "send_gmail", {**payload(), "thread_id": None})
        with pytest.raises((ApprovalRequired, ValueError)):
            ingest.ingest_contract("a", "update.pdf", b"synthetic update",
                                   approval_execution_id=execution_id if forged_internal_token else None)
        assert repo.contract("C01").current_version == 1


@pytest.mark.parametrize("analysis_fails", [False, True])
def test_amendment_own_lease_allows_only_its_version_pinned_local_ingest(store, monkeypatch, tmp_path, analysis_fails):
    from types import SimpleNamespace

    from odin.api import routes
    from odin.core.models import CoverMeta
    from odin.graphs import update as update_graph
    from odin.ingest import service as ingest
    monkeypatch.setattr(ingest, "DATA_DIR", tmp_path)
    monkeypatch.setattr(ingest, "docx_to_pdf", lambda src, dst: dst.write_bytes(b"synthetic pdf") and [])
    monkeypatch.setattr(ingest, "parse_pdf", lambda *a, **k: SimpleNamespace(
        cover=CoverMeta(contract_id="C01", title="Local proposal"), warnings=[], clauses=[], text="Local proposal"))
    starts = []
    def start_analysis(*args, **kwargs):
        assert repo.get("action", "act")["approval_execution"]["state"] == "completed"
        starts.append(args)
        if analysis_fails:
            raise RuntimeError("Synthetic private provider failure")
        return "sandbox-run"
    monkeypatch.setattr(update_graph, "run", start_analysis)
    seen = []
    real_clauses = repo.clauses
    def pinned_clauses(*args, **kwargs):
        seen.append(kwargs)
        return real_clauses(*args, **kwargs)
    monkeypatch.setattr(repo, "clauses", pinned_clauses)
    with run_ctx("a", user_role="admin"):
        repo.set_status("act", "draft", kind="amendment", redlines=[{"clause_number": "1", "before": "a", "after": "b"}])
        approve()
        user = SimpleNamespace(company_id="a", role="admin", email="admin@aurora.test")
        result = routes.decide_action("act", "apply", u=user)
        assert result["version"] == 2 and repo.contract("C01").current_version == 2
        assert len(starts) == 1
        assert result["run_id"] == (None if analysis_fails else "sandbox-run")
        action = repo.get("action", "act")
        assert action["approval_execution"]["state"] == "completed"
        assert "counterparty agreement is not established" in action["application_effect"]
        if analysis_fails:
            assert result["analysis_warning"] == action["analysis_warning"]
            assert "private provider" not in result["analysis_warning"]
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as replay:
            routes.decide_action("act", "apply", u=user)
        assert replay.value.status_code == 403 and len(starts) == 1
        assert repo.contract("C01").current_version == 2
    assert seen == [{"version": 1, "current_only": False}]


def test_side_effect_tools_remain_hidden_from_model_bindings():
    from odin.tools.registry import REGISTRY
    assert all(t.name != "send_gmail" for t in REGISTRY.langchain_tools("system", ["send_gmail"]))
    assert REGISTRY.langchain_tools("system", ["get_clause"])[0].name == "get_clause"


def test_system_reply_requires_exact_parser_template_and_executes_once(store, monkeypatch):
    from odin.email import event_parser, gmail
    from odin.tools.core import SystemReplyArgs, send_system_reply
    from odin.tools.registry import ToolDenied
    subject, raw = "[ODIN-EVENT]", "malformed input"
    with pytest.raises(event_parser.EventParseError) as rejected:
        event_parser.parse(subject, raw)
    problems = rejected.value.problems
    with session.db() as s:
        s.add(Record(id="a|evt", company_id="a", kind="event", status="rejected", data={
            "id": "evt", "status": "rejected", "parse_method": "strict", "subject": subject,
            "raw": raw, "sender": "notice@forge.test", "thread_id": "thread", "reject_problems": problems}))
    effects = []
    monkeypatch.setattr(gmail, "send_message", lambda *args: effects.append(args) or {"sent": True})
    args = {"event_id": "evt", "to": "notice@forge.test", "subject": f"Re: {subject}",
            "body": event_parser.reply_body(problems), "thread_id": "thread"}
    with run_ctx("a"):
        with pytest.raises(ToolDenied):
            send_system_reply(SystemReplyArgs(**{**args, "body": "arbitrary unapproved email"}))
        send_system_reply(SystemReplyArgs(**args))
        with pytest.raises(ToolDenied):
            send_system_reply(SystemReplyArgs(**args))
    assert len(effects) == 1


def test_webhook_requires_operator_https_host_policy_and_no_redirects(monkeypatch):
    from types import SimpleNamespace

    from odin.tools import core
    from odin.tools.registry import ToolDenied
    monkeypatch.setattr(core, "settings", lambda: SimpleNamespace(webhook_url="https://hooks.example.test/notify"))
    monkeypatch.delenv("ODIN_WEBHOOK_ALLOWED_HOSTS", raising=False)
    args = core.WebhookArgs(event="alert", payload={"title": "Alert"})
    with pytest.raises(ToolDenied):
        core.post_webhook(args)
    monkeypatch.setenv("ODIN_WEBHOOK_ALLOWED_HOSTS", "hooks.example.test")
    sent = []
    monkeypatch.setattr(core.httpx, "post", lambda *args, **kwargs: sent.append(kwargs) or SimpleNamespace(status_code=200))
    core.post_webhook(args)
    assert len(sent) == 1 and sent[0]["follow_redirects"] is False
