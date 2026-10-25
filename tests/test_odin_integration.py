"""Exercise real Odin hooks and services without providers or PostgreSQL."""

import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from pathlib import Path

import pytest
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "backend"))


def test_capture_is_context_local_and_parallel_safe():
    from odin.core.hooks import HOOKS

    from ragnarok.odin_capture import capture

    with capture() as first:
        contexts = [copy_context() for _ in range(8)]
        with ThreadPoolExecutor(4) as pool:
            list(pool.map(lambda ctx: ctx.run(HOOKS.record, "agent", "thor", {}, {}, {}), contexts))
        with capture() as second:
            HOOKS.record("agent", "loki", {}, {}, {})
    HOOKS.record("agent", "outside", {}, {}, {})
    assert len(first.records) == 8
    assert [r["agent"] for r in second.records] == ["loki"]


def test_capture_limit_marks_evidence_partial():
    from odin.core.hooks import HOOKS

    from ragnarok.odin_capture import capture

    with capture(max_records=1) as observed:
        HOOKS.record("agent", "thor", {}, {}, {})
        HOOKS.record("agent", "loki", {}, {}, {})
    assert observed.truncated and len(observed.records) == 1


def test_registry_records_denial_approval_failure_and_execution(monkeypatch):
    from odin.core.hooks import HOOKS
    from odin.tools.registry import ApprovalRequired, ToolDenied, ToolRegistry

    from ragnarok.odin_capture import capture

    class Args(BaseModel):
        n: int = 1

    reg = ToolRegistry()
    monkeypatch.setattr(reg, "_audit", lambda *args, **kw: None)

    @reg.tool(args=Args, scope="read_state")
    def read(args):
        return args.n

    @reg.tool(args=Args, scope="external_send", side_effect=True, requires_approval=True)
    def send(args):
        raise AssertionError("must never reach an external send")

    @reg.tool(args=Args, scope="read_state")
    def broken(args):
        raise ValueError("body failed")

    reg.grant("thor", "read", "send", "broken")
    with capture() as observed:
        with pytest.raises(ToolDenied):
            reg.invoke("loki", "read", {})
        with pytest.raises(ApprovalRequired):
            reg.invoke("thor", "send", {})
        assert reg.invoke("thor", "read", {"n": 2}) == 2
        with pytest.raises(ValueError):
            reg.invoke("thor", "broken", {})
    records = [r for r in observed.records if r["kind"] == "tool"]
    assert len(records) == 4
    assert records[0]["meta"]["authorized"] is False
    assert records[0]["meta"]["executed"] is False
    assert records[1]["meta"]["approved"] is False
    assert records[1]["meta"]["executed"] is False
    assert records[2]["meta"]["executed"] is True
    assert records[3]["meta"]["executed"] is True and records[3]["meta"]["ok"] is False
    assert HOOKS is not None


def test_normalize_uses_row_tenant_not_request_tenant_and_empty_retrieval():
    from ragnarok.odin_capture import Capture, normalize

    observed = Capture()
    observed.record(
        "retrieval",
        "ask",
        "q",
        [
            {
                "contract_id": "C",
                "version": 2,
                "clause_number": "1.2",
                "company_id": "other",
                "text": "Full clause",
            }
        ],
        {},
    )
    result = normalize(observed, {"answer": "a", "citations": []}, operation="ask")
    assert result.documents.items[0].id == "C:v2:1.2"
    assert result.documents.items[0].tenant_id == "other"
    empty = Capture()
    empty.record("retrieval", "ask", "q", [], {})
    result = normalize(empty, {"answer": "none", "citations": []}, operation="ask")
    assert result.documents.state == "complete" and result.documents.items == []


def test_missing_retrieval_is_unavailable_and_ask_uses_answer_passages():
    from ragnarok.odin_capture import Capture, normalize

    observed = Capture()
    result = normalize(observed, {"answer": "a", "citations": []}, operation="ask")
    assert result.documents.state == "unavailable"
    observed.record(
        "retrieval",
        "ask",
        "q",
        [
            {
                "contract_id": "C",
                "version": 1,
                "clause_number": "1",
                "text": "full",
                "company_id": "T",
            }
        ],
        {},
    )
    result = normalize(
        observed,
        {
            "answer": "a",
            "citations": [],
            "passages": [
                {
                    "contract_id": "C",
                    "version": 1,
                    "clause_number": "1",
                    "text": "truncated",
                    "company_id": "T",
                }
            ],
        },
        operation="ask",
    )
    assert result.output == "a" and result.documents.items[0].text == "truncated"


def test_eval_guard_blocks_external_effects_but_not_internal_state():
    from odin.core.hooks import Blocked

    from ragnarok.odin_capture import EvaluationGuard

    guard = EvaluationGuard(allow_internal_writes=True)
    with pytest.raises(Blocked):
        guard.pre_tool("system", "send_system_reply", "external_send", {})
    with pytest.raises(Blocked):
        guard.pre_tool("system", "apply_amendment", "file_write", {})
    assert guard.pre_tool("thor", "save_extraction", "write_state", {"a": 1}) == {"a": 1}


def test_probe_cannot_write_without_disposable_database_opt_in():
    from odin.core.hooks import Blocked

    from ragnarok.odin_capture import EvaluationGuard

    with pytest.raises(Blocked):
        EvaluationGuard().pre_tool("loki", "save_dependency", "write_state", {})


def test_odin_configuration_requires_disposable_opt_in_for_graphs():
    from pydantic import ValidationError

    from ragnarok.config import OdinConfig

    with pytest.raises(ValidationError):
        OdinConfig(company_id="T", operation="analysis")
    assert OdinConfig(company_id="T", operation="ask").operation == "ask"
    with pytest.raises(ValidationError):
        OdinConfig(company_id="T", parameters={"company_id": "OTHER"})
    with pytest.raises(ValidationError):
        OdinConfig(company_id="T", parameters={"unknown": "option"})


def test_subprocess_cancellation_terminates_worker(tmp_path, monkeypatch):
    from ragnarok.config import OdinConfig
    from ragnarok.models import EvaluationCase
    from ragnarok.odin_adapter import OdinAdapter

    adapter = OdinAdapter(OdinConfig(company_id="T"), root=Path.cwd())
    # A real cancellable process using the same transport code as an Odin worker.
    monkeypatch.setattr(
        adapter, "worker_command", [sys.executable, "-c", "import time; time.sleep(60)"]
    )

    async def exercise():
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(adapter.execute(EvaluationCase(id="c", input="q"), "r"), 0.4)
        assert adapter.last_returncode is not None

    asyncio.run(exercise())


@pytest.fixture
def odin_db(tmp_path, monkeypatch):
    import yaml
    from odin.core import budget
    from odin.core.config import ROOT, odin_config, settings
    from odin.db.session import _factory, engine
    from odin.db.tables import Base, ClauseRow, Company, Contract
    from odin.retrieval.hybrid import _BM25

    cfg = yaml.safe_load((ROOT / "config/odin.yaml").read_text())
    cfg["retrieval"]["dense_enabled"] = False
    cfg_path = tmp_path / "odin.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg))
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(tmp_path / "odin.db"))
    monkeypatch.setenv("ODIN_CONFIG", str(cfg_path))
    monkeypatch.setenv("ODIN_FORCE_PROVIDER", "fake")
    settings.cache_clear()
    odin_config.cache_clear()
    engine.cache_clear()
    _factory.cache_clear()
    _BM25._idx.clear()
    budget._budgets.clear()
    Base.metadata.create_all(engine())
    with _factory()() as session:
        session.add_all([Company(id="T", name="Synthetic"), Company(id="OTHER", name="Other")])
        session.add(Contract(id="contract-row", company_id="T", contract_id="C", title="Synthetic"))
        for i, text in enumerate(
            [
                "renewal requires sixty days notice " + "long " * 400,
                "payment bank credit",
                "insurance liability indemnity",
                "arbitration court India",
                "confidentiality data ownership",
            ]
        ):
            session.add(
                ClauseRow(
                    id=f"row-{i}",
                    company_id="T",
                    contract_id="C",
                    version=1,
                    number=str(i + 1),
                    text=text,
                )
            )
        session.add(
            ClauseRow(
                id="foreign",
                company_id="OTHER",
                contract_id="OTHER-C",
                version=1,
                number="1",
                text="renewal forbidden foreign synthetic-canary",
            )
        )
        session.commit()
    yield tmp_path
    _factory.cache_clear()
    engine().dispose()
    engine.cache_clear()
    odin_config.cache_clear()
    settings.cache_clear()
    budget._budgets.clear()


def test_real_retriever_full_context_scope_and_empty_results(odin_db):
    from odin.core.context import run_ctx
    from odin.retrieval.hybrid import search

    from ragnarok.odin_capture import capture, normalize

    with capture() as observed, run_ctx("T"):
        hits = search("renewal")
    result = normalize(observed, None, operation="retrieval")
    assert hits[0].contract_id == "C"
    assert len(result.documents.items[0].text) > 1500
    assert {d.tenant_id for d in result.documents.items} == {"T"}
    with capture() as observed, run_ctx("empty-company"):
        assert search("renewal") == []
    assert normalize(observed, None, operation="retrieval").documents.state == "complete"


def test_ask_refuses_without_verified_citations(odin_db):
    from odin.services.ask import ask

    answer = ask("T", "renewal")
    assert answer["insufficient_evidence"] is True
    assert answer["answer"] != "n/a"
    assert answer["passages"]
    assert ask("empty-company", "renewal")["insufficient_evidence"] is True


def test_real_subprocess_retrieval_and_security_probe(odin_db):
    from ragnarok.config import OdinConfig
    from ragnarok.models import EvaluationCase
    from ragnarok.odin_adapter import OdinAdapter

    adapter = OdinAdapter(
        OdinConfig(company_id="T", operation="retrieval", backend_path="backend"),
        root=Path.cwd(),
    )
    result = asyncio.run(adapter.execute(EvaluationCase(id="r", input="renewal"), "request"))
    assert result.state == "complete", result.errors
    assert result.documents.items[0].id == "C:v1:1"
    adapter = OdinAdapter(
        OdinConfig(company_id="T", operation="tool_probe", backend_path="backend"),
        root=Path.cwd(),
    )
    result = asyncio.run(
        adapter.execute(
            EvaluationCase(id="s", input={"agent": "loki", "tool": "send_gmail"}), "request"
        )
    )
    assert result.state == "complete", result.errors
    assert result.tools.items[0].phase == "requested"
    assert result.metadata["tool_decisions"][0]["error_type"] == "ToolDenied"


def test_fake_provider_cannot_pass_golden_run(odin_db):
    from ragnarok.config import OdinConfig
    from ragnarok.models import EvaluationCase
    from ragnarok.odin_adapter import OdinAdapter

    adapter = OdinAdapter(OdinConfig(company_id="T", backend_path="backend"), root=Path.cwd())
    result = asyncio.run(adapter.execute(EvaluationCase(id="q", input="renewal"), "request"))
    assert result.state == "error" and "Fake provider rejected" in result.errors[-1]


def test_real_analysis_graph_records_agents_and_partial_status(odin_db, monkeypatch):
    # Exercise the actual compiled graph with an in-memory checkpointer, SQLite
    # and schema-only fake models. This is orchestration QA, not answer accuracy.
    from langgraph.checkpoint.memory import InMemorySaver
    from odin.graphs import analysis

    from ragnarok.config import OdinConfig
    from ragnarok.odin_worker import execute

    monkeypatch.setattr(analysis, "checkpointer", lambda: InMemorySaver())
    analysis.build.cache_clear()
    result = execute(
        OdinConfig(
            company_id="T", operation="analysis", disposable_database=True, allow_fake_provider=True
        ),
        None,
        "request",
    )
    assert result.state == "partial", result.errors
    assert any(e.kind == "odin.plan.start" for e in result.events.items)
    assert result.output["final_status"] == "partial"
    assert "artifacts" in result.output
    analysis.build.cache_clear()


@pytest.mark.parametrize(
    "name,params,expected",
    [
        ("tool_denied", {"tools": ["send_gmail"], "error_types": ["ToolDenied"]}, "passed"),
        ("tool_denied", {"tools": ["not_requested"]}, "failed"),
        ("mrr_at_k", {"k": 5}, "passed"),
        ("insufficient_evidence", {}, "passed"),
        ("json_fields", {"expected": {"contract.term": 24}}, "failed"),
    ],
)
def test_integrated_metrics(name, params, expected):
    from ragnarok.checks import evaluate_check
    from ragnarok.models import CheckSpec, EvaluationCase, ExecutionResult

    result = ExecutionResult(
        output={"contract": {"term": True}},
        documents={"state": "complete", "items": [{"id": "C:v1:1", "text": "text"}]},
        tools={"state": "complete", "items": [{"name": "send_gmail", "phase": "requested"}]},
        metadata={
            "tool_decisions": [
                {"tool": "send_gmail", "executed": False, "error_type": "ToolDenied"}
            ],
            "insufficient_evidence": True,
        },
    )
    case = EvaluationCase(id="c", input="q", expected_relevant_document_ids=["C:v1:1"])
    assert evaluate_check(CheckSpec(name=name, params=params), case, result).status == expected


def test_langsmith_observer_links_product_trace_without_raw_data():
    from unittest.mock import MagicMock
    from uuid import uuid4

    from ragnarok.config import TracingConfig
    from ragnarok.models import CaseReport, ExecutionResult
    from ragnarok.observability import LangSmithObserver

    product_id = str(uuid4())
    client = MagicMock()
    report = CaseReport(
        case_id="test",
        kind="quality",
        checks=[],
        execution=ExecutionResult(output="private", trace_id=product_id),
    )
    asyncio.run(
        LangSmithObserver(TracingConfig(enabled=True), client=client).publish(report, str(uuid4()))
    )
    assert client.create_run.call_args.kwargs["extra"]["metadata"]["product_trace_id"] == product_id
    assert "private" not in str(client.mock_calls)


def test_trace_transport_failure_does_not_hide_product_error(monkeypatch):
    from odin.core import telemetry

    monkeypatch.setattr(telemetry, "enabled", lambda: True)
    monkeypatch.setattr(telemetry, "client", lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    with telemetry.span("synthetic") as trace:
        assert trace is None
    with pytest.raises(ValueError, match="product"):
        with telemetry.span("synthetic"):
            raise ValueError("product")


def test_child_trace_errors_are_sanitized_before_transport(monkeypatch):
    from langsmith import Client
    from odin.core.telemetry import PrivateClient

    sent = []
    monkeypatch.setattr(Client, "update_run", lambda self, *a, **kw: sent.append(kw))
    monkeypatch.setattr(Client, "create_run", lambda self, *a, **kw: sent.append(kw))
    client = PrivateClient(api_key="synthetic", auto_batch_tracing=False)
    client.update_run("id", error="SYNTHETIC_PRIVATE_CONTRACT_TEXT")
    client.create_run("name", inputs={}, run_type="chain", error="SYNTHETIC_PRIVATE_CONTRACT_TEXT")
    assert all(item["error"] == "Product execution failed" for item in sent)


def test_ask_retains_tool_document_security_evidence_and_context():
    from ragnarok.checks import evaluate_check
    from ragnarok.models import CheckSpec, EvaluationCase
    from ragnarok.odin_capture import Capture, normalize

    initial = {
        "contract_id": "C",
        "version": 1,
        "clause_number": "1",
        "company_id": "T",
        "text": "initial",
    }
    foreign = {
        "contract_id": "X",
        "version": 2,
        "clause_number": "2",
        "company_id": "OTHER",
        "text": "foreign",
    }
    observed = Capture()
    observed.record("retrieval", "ask", "q", [initial], {})
    observed.record("document", "ask", None, foreign, {})
    observed.record("model_context", "ask", None, "actual serialized tool response", {})
    result = normalize(
        observed,
        {
            "answer": "a",
            "passages": [initial],
            "citations": [{"contract_id": "X", "clause_number": "2", "quote": "foreign"}],
        },
        operation="ask",
    )
    check = evaluate_check(
        CheckSpec(name="tenant_isolation", params={"allowed_tenant_ids": ["T"]}),
        EvaluationCase(id="c", input="q"),
        result,
    )
    assert check.status == "failed"
    assert result.citations.items[0].document_id == "X:v2:2"
    assert result.model_context.items == ["initial", "actual serialized tool response"]


def test_actual_langchain_child_trace_error_is_private(monkeypatch):
    from langchain_core.runnables import RunnableLambda
    from langchain_core.tracers.langchain import wait_for_all_tracers
    from langsmith import Client
    from odin.core import telemetry

    updates = []
    monkeypatch.setattr(Client, "create_run", lambda self, *a, **kw: None)
    monkeypatch.setattr(Client, "update_run", lambda self, *a, **kw: updates.append(kw))
    private = telemetry.PrivateClient(api_key="synthetic", auto_batch_tracing=False)
    monkeypatch.setattr(telemetry, "enabled", lambda: True)
    monkeypatch.setattr(telemetry, "client", lambda: private)

    def fail(_):
        raise ValueError("SYNTHETIC_PRIVATE_CONTRACT_TEXT")

    with pytest.raises(ValueError):
        with telemetry.span("synthetic-parent"):
            RunnableLambda(fail).invoke("synthetic")
    wait_for_all_tracers()
    errors = [u["error"] for u in updates if u.get("error")]
    assert len(errors) >= 2
    assert set(errors) == {"Product execution failed"}


def test_deepeval_uses_actual_tool_messages_not_unseen_candidates():
    from ragnarok.config import JudgeConfig
    from ragnarok.judges import DeepEvalEvaluator
    from ragnarok.models import CheckSpec, EvaluationCase, ExecutionResult

    seen = []

    class Metric:
        score = 1
        reason = "synthetic"

        async def a_measure(self, case):
            seen.extend(case.retrieval_context)

    execution = ExecutionResult(
        output="a",
        documents={
            "state": "complete",
            "items": [{"id": "unseen", "text": "unseen full candidate"}],
        },
        model_context={
            "state": "complete",
            "items": ["actual initial passage", "actual truncated tool message"],
        },
    )
    result = asyncio.run(
        DeepEvalEvaluator(JudgeConfig(enabled=True), metric_factory=lambda *a: Metric()).evaluate(
            CheckSpec(name="faithfulness"), EvaluationCase(id="c", input="q"), execution
        )
    )
    assert result.status == "passed"
    assert seen == execution.model_context.items


def test_recomputed_artifact_belongs_to_the_current_evaluation_run(odin_db):
    from odin.core.context import run_ctx
    from odin.db import repo

    class Artifact(BaseModel):
        id: str = "same-artifact"
        value: int

    with run_ctx("T", run_id="first"):
        repo.put("finding", Artifact(value=1))
    with run_ctx("T", run_id="second"):
        repo.put("finding", Artifact(value=2))
        assert repo.query("finding", run_id="second")[0]["value"] == 2
