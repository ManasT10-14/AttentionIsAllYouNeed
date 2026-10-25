"""Actual corpus contracts: release safety, golden compilation, honest comparison."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2] / "corpus"


def test_validate_supplied_corpus_counts_and_hashes():
    from ragnarok.corpus import validate_corpus

    result = validate_corpus(ROOT)
    assert result == {
        "contracts": 15,
        "scenarios": 64,
        "agent_vectors": 384,
        "thor_assertions": 114,
        "citations": 276,
    }


def test_release_hides_future_contract_and_observations():
    from ragnarok.corpus import CorpusInputs

    inputs = CorpusInputs(ROOT)
    before = inputs.release("DEMO-PORTFOLIO", "2027-01-24T23:59:59Z")
    after = inputs.release("DEMO-PORTFOLIO", "2027-02-01T12:00:00Z")
    assert "C08" not in before.contract_ids
    assert "C08" in after.contract_ids
    assert all(e["received_at"] <= "2027-01-24T23:59:59Z" for e in before.events)
    assert not any(p.name == "C08.pdf" for p in before.pdfs)
    assert "oracle" not in json.dumps(before.product_input())
    assert "clock_checkpoints" not in json.dumps(before.product_input())


def test_input_paths_cannot_escape_into_answer_keys():
    from ragnarok.corpus import CorpusInputs

    loader = CorpusInputs(ROOT)
    for path in ("oracle/golden/agent_goldens.jsonl", "inputs/../../.env", "../.env"):
        with pytest.raises(ValueError):
            loader.input_path(path)


def test_compile_every_supplied_golden_without_putting_answers_in_input():
    from ragnarok.corpus import compile_datasets

    datasets = compile_datasets(ROOT)
    assert len(datasets["agent"].cases) == 384
    assert len(datasets["thor"].cases) == 15
    assert len(datasets["rag"].cases) == 276
    assert len(datasets["retrieval"].cases) == 276
    for case in datasets["agent"].cases:
        assert case.kind == "agent"
        assert "expected_output" not in case.input
        assert case.metadata["agent"] in {"odin", "thor", "norns", "loki", "heimdall", "tyr"}
        assert case.expected_output is not None
    for case in datasets["rag"].cases:
        assert case.expected_output not in case.input
        assert case.expected_relevant_document_ids


def test_exact_agent_assertions_are_recursive_minimum_typed_subsets():
    from ragnarok.corpus_checks import compare_subset

    assert (
        compare_subset(
            {"money": "40", "missing": None}, {"money": "40", "missing": None, "extra": 3}
        )
        == []
    )
    assert compare_subset({"money": "40"}, {"money": 40}) == ["money"]
    assert compare_subset({"flag": True}, {"flag": 1}) == ["flag"]
    assert compare_subset({"unknown": None}, {}) == ["unknown"]
    assert compare_subset({"a": {"b": 2}}, {"a": {"b": 3}}) == ["a.b"]


def test_missing_agent_mapping_fails_instead_of_silently_passing():
    from ragnarok.checks import evaluate_check
    from ragnarok.models import CheckSpec, EvaluationCase, ExecutionResult

    case = EvaluationCase(
        id="c",
        kind="agent",
        input="q",
        expected_output={"exact": {"case_assertions": {"principal_inr": "40000"}}},
    )
    result = evaluate_check(
        CheckSpec(name="corpus_exact"), case, ExecutionResult(output={"case_assertions": {}})
    )
    assert result.status == "failed" and "principal_inr" in result.reason


def test_every_pdf_passes_actual_product_parser_without_oracle_input():
    from odin.ingest.parse import parse_pdf

    contracts = json.loads((ROOT / "manifest.json").read_text())["contracts"]
    for record in contracts:
        doc = parse_pdf(ROOT / record["file"], fallback_id=record["contract_id"])
        assert doc.cover.contract_id == record["contract_id"]
        assert doc.clauses
        assert len({c.number for c in doc.clauses}) == len(doc.clauses)


def test_backend_dotenv_does_not_turn_quoted_empty_keys_into_live_providers(tmp_path, monkeypatch):
    from odin.core import config

    (tmp_path / ".env").write_text("GROQ_API_KEY=''\nRAGNAROK_QUOTED='abc # literal'\n")
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("RAGNAROK_QUOTED", raising=False)
    config.settings.cache_clear()
    try:
        config.settings()
        import os

        assert os.environ["GROQ_API_KEY"] == ""
        assert os.environ["RAGNAROK_QUOTED"] == "abc # literal"
    finally:
        config.settings.cache_clear()


def test_thor_mapping_uses_actual_fields_and_decimal_strings():
    from ragnarok.corpus_checks import thor_projection, thor_score

    actual = {
        "term": {"effective_date": "2027-01-03", "end_date": "2027-06-30"},
        "renewal": {"notice_days": 30, "renewal_period_months": 6},
        "payments": [
            {
                "amount": {"amount": 100000.0, "currency": "INR"},
                "frequency": "monthly",
                "payer": "Aurora",
                "first_due": "2027-01-20",
            }
        ],
    }
    projection = thor_projection(actual)
    assert projection["initial_term"] == ["2027-01-03", "2027-06-30"]
    assert projection["monthly_rent_payable_inr"] == "100000"
    assert "per_invoice_charge_cap_inr" not in projection
    score, reason = thor_score(
        {
            "field_assertions": [
                {"name": "monthly_rent_payable_inr", "value": "100000"},
                {"name": "per_invoice_charge_cap_inr", "value": "5000"},
            ]
        },
        actual,
    )
    assert score == 0.5 and "per_invoice_charge_cap_inr" in reason


def test_thor_mapping_resolves_generic_fields_to_golden_names():
    from ragnarok.corpus_checks import thor_score

    def inr(n):
        return {"amount": n, "currency": "INR"}

    actual = {
        "parties": [
            {"name": "Willow Housing Ltd", "capacity": "Controller"},
            {"name": "Aurora Software Pvt Ltd", "capacity": "Processor"},
        ],
        "penalties": [
            {
                "trigger": "late delivery",
                "basis": "per_day",
                "direction": "receivable",
                "amount": inr(2000),
                "cap": inr(20000),
                "cap_period": "per_lot",
            },
            {
                "trigger": "outage",
                "kind": "service_credit",
                "basis": "per_incident",
                "pct": 20,
                "direction": "receivable",
                "cap": inr(15000),
                "cap_period": "per_month",
            },
        ],
        "obligations": [{"description": "Deliver lot", "due_at": "2027-02-10T22:30:00+05:30"}],
        "periods": [{"purpose": "cure", "value": 10, "unit": "days"}],
        "related_contracts": [
            {"contract_ref": "C01", "relation": "depends_on"},
            {"contract_ref": "C02", "relation": "does_not_replace"},
        ],
        "forum": {"value": "Bengaluru, Karnataka"},
        "notice": {"address": "notices@willow.example"},
    }
    golden = {
        "daily_delay_recoverable_inr": "2000",
        "lot_recoverable_cap_inr": "20000",
        "monthly_credit_cap_inr": "15000",
        "recovery_credit_rate": "0.20",
        "delivery_due": "2027-02-10T17:00:00Z",
        "cure_days_after_receipt": 10,
        "depends_on_contract": "C01",
        "replaces_c02": False,
        "forum": "Bengaluru",
        "notice_address": "notices@willow.example",
        "controller_party_id": "P03",
        "processor_party_id": "P01",
    }
    score, reason = thor_score(
        {"field_assertions": [{"name": k, "value": v} for k, v in golden.items()]}, actual
    )
    assert score == 1.0, reason


def test_workspace_ingestion_uses_actual_pdf_without_embedding_download(tmp_path, monkeypatch):
    from ragnarok.corpus_runtime import initialize_workspace, seed_documents

    initialize_workspace(tmp_path, dense=False)
    from odin.retrieval import hybrid

    monkeypatch.setattr(
        hybrid,
        "embed_passages",
        lambda *a: (_ for _ in ()).throw(AssertionError("must not download embeddings")),
    )
    seed_documents(ROOT, ["C05"])
    from odin.core.context import run_ctx
    from odin.db import repo

    with run_ctx("P01"):
        assert {c.contract_id for c in repo.contracts()} == {"C05"}
        assert repo.clauses("C05")
    from ragnarok.corpus_runtime import reset_runtime_caches

    reset_runtime_caches()


def test_empty_exact_assertions_are_not_a_passing_agent_metric():
    from ragnarok.corpus import compile_datasets

    dataset = compile_datasets(ROOT)["agent"]
    for case in dataset.cases:
        if not case.expected_output.get("exact"):
            assert "corpus_exact" not in [s.name for s in case.checks]


def test_judge_supports_role_rubric_with_structured_actual_output():
    import asyncio

    from ragnarok.config import JudgeConfig
    from ragnarok.judges import DeepEvalEvaluator
    from ragnarok.models import CheckSpec, EvaluationCase, ExecutionResult

    seen = []

    class Metric:
        score = 0.8
        reason = "synthetic"

        async def a_measure(self, case):
            seen.append(case)

    case = EvaluationCase(
        id="c",
        kind="agent",
        input="Inspect a role",
        expected_output={"requirements": ["Only cited findings"]},
    )
    result = asyncio.run(
        DeepEvalEvaluator(JudgeConfig(enabled=True), metric_factory=lambda *a: Metric()).evaluate(
            CheckSpec(name="agent_rubric", threshold=0.7),
            case,
            ExecutionResult(output={"findings": []}),
        )
    )
    assert result.status == "passed" and result.category == "agent"
    assert json.loads(seen[0].actual_output) == {"findings": []}
    assert json.loads(seen[0].expected_output) == case.expected_output


def test_corpus_roles_share_real_run_and_never_transport_expected_answers(tmp_path, monkeypatch):
    import asyncio

    from ragnarok.config import CorpusConfig
    from ragnarok.corpus_adapter import CorpusAdapter
    from ragnarok.models import EvaluationCase, ExecutionResult

    adapter = CorpusAdapter(
        CorpusConfig(mode="agent", root=str(ROOT), workspace=str(tmp_path), backend_path="backend"),
        root=ROOT.parent,
    )
    sent = []

    async def execute(payload):
        sent.append(payload)
        await asyncio.sleep(0)
        return ExecutionResult(
            output={"roles": {"thor": {"extractions": []}, "tyr": {"actions": []}}}
        )

    monkeypatch.setattr(adapter, "_execute_payload", execute)

    async def exercise():
        return await asyncio.gather(
            *(
                adapter.execute(
                    EvaluationCase(
                        id=a,
                        kind="agent",
                        input="q",
                        expected_output="EVALUATOR_ONLY_ANSWER",
                        metadata={"agent": a, "corpus_case": "PAY-03"},
                    ),
                    a,
                )
                for a in ["thor", "tyr"]
            )
        )

    results = asyncio.run(exercise())
    assert len(sent) == 1 and "EVALUATOR_ONLY_ANSWER" not in json.dumps(sent)
    assert results[0].output == {"extractions": []} and results[1].output == {"actions": []}


def test_actual_corpus_worker_extracts_in_isolated_db_and_marks_fake(tmp_path, monkeypatch):
    import asyncio

    from ragnarok.config import CorpusConfig
    from ragnarok.corpus_adapter import CorpusAdapter
    from ragnarok.models import EvaluationCase

    monkeypatch.setenv("ODIN_FORCE_PROVIDER", "fake")
    adapter = CorpusAdapter(
        CorpusConfig(
            mode="thor",
            root=str(ROOT),
            workspace=str(tmp_path),
            backend_path="backend",
            allow_fake_provider=True,
        ),
        root=ROOT.parent,
    )
    result = asyncio.run(
        adapter.execute(
            EvaluationCase(id="thor::C05", input="Extract C05", metadata={"contract_id": "C05"}),
            "request",
        )
    )
    assert result.state == "complete", result.errors
    assert result.metadata["providers"] == ["fake"]
    assert any(e.kind == "thor.extract.start" for e in result.events.items)
    assert result.metadata["known_contract_ids"] == ["C05"]


def test_schedule_goldens_map_to_real_chunks_and_allow_extra_supported_citations():
    from ragnarok.corpus import compile_datasets

    data = compile_datasets(ROOT)
    row = next(c for c in data["retrieval"].cases if c.id == "retrieval::C01:Sch A, row 1")
    assert row.expected_relevant_document_ids == ["C01:v1:SCHEDULE A"]
    assert len(row.reference_context) > 1
    assert any(d.id == "C01:v1:2.1" for d in row.reference_context)


def test_corpus_citations_can_normalize_pdf_whitespace_without_relaxing_words():
    from ragnarok.checks import evaluate_check
    from ragnarok.models import CheckSpec, EvaluationCase, ExecutionResult

    case = EvaluationCase(
        id="c",
        input="q",
        reference_context=[{"id": "C", "text": "Exact\nPDF words", "clause_id": "1"}],
    )
    actual = ExecutionResult(
        citations={
            "state": "complete",
            "items": [{"document_id": "C", "clause_id": "1", "quote": "Exact PDF words"}],
        }
    )
    assert (
        evaluate_check(
            CheckSpec(name="citations", params={"normalize_whitespace": True}), case, actual
        ).status
        == "passed"
    )
    actual.citations.items[0].quote = "Wrong PDF words"
    assert (
        evaluate_check(
            CheckSpec(name="citations", params={"normalize_whitespace": True}), case, actual
        ).status
        == "failed"
    )


def test_retrieval_batches_queries_per_contract_without_transporting_labels(tmp_path, monkeypatch):
    import asyncio

    from ragnarok.config import CorpusConfig
    from ragnarok.corpus_adapter import CorpusAdapter
    from ragnarok.models import EvaluationCase, ExecutionResult

    cases = [
        EvaluationCase(
            id=str(i),
            input=f"question {i}",
            expected_output="NEVER_TRANSPORT",
            metadata={"contract_id": "C01"},
        )
        for i in range(2)
    ]
    adapter = CorpusAdapter(
        CorpusConfig(
            mode="retrieval", root=str(ROOT), workspace=str(tmp_path), backend_path="backend"
        ),
        root=ROOT.parent,
        cases=cases,
    )
    sent = []

    async def execute(payload):
        sent.append(payload)
        return ExecutionResult(
            output={
                "batch": {
                    case.id: ExecutionResult(output=case.input).model_dump(mode="json")
                    for case in cases
                }
            }
        )

    monkeypatch.setattr(adapter, "_execute_payload", execute)

    async def exercise():
        return [await adapter.execute(case, "request") for case in cases]

    result = asyncio.run(exercise())
    assert len(sent) == 1 and len(sent[0]["questions"]) == 2
    assert "NEVER_TRANSPORT" not in json.dumps(sent)
    assert [r.output for r in result] == [c.input for c in cases]


def test_memory_dense_ranking_uses_cosine_similarity_and_rejects_bad_dimensions():
    from types import SimpleNamespace

    from odin.retrieval.hybrid import memory_dense_ids

    rows = {
        "a": SimpleNamespace(embedding=[1.0, 0.0]),
        "b": SimpleNamespace(embedding=[0.0, 1.0]),
        "none": SimpleNamespace(embedding=None),
    }
    assert memory_dense_ids(rows, [1.0, 0.0], 2) == ["a", "b"]
    with pytest.raises(ValueError):
        memory_dense_ids(rows, [1.0], 2)


def test_thor_rubric_compares_facts_not_an_exhaustive_oracle_json_shape():
    import asyncio

    from ragnarok.config import JudgeConfig
    from ragnarok.judges import DeepEvalEvaluator
    from ragnarok.models import CheckSpec, EvaluationCase, ExecutionResult

    seen = []

    class Metric:
        score = 1
        reason = "synthetic"

        async def a_measure(self, case):
            seen.append(case)

    expected = {
        "party_ids": ["P01"],
        "field_assertions": [{"name": "auto_renew", "value": False}],
        "clause_inventory": [{"quote": "This is a source index, not mandatory output"}],
    }
    actual = {
        "parties": [{"name": "Aurora Software Private Limited", "role": "company"}],
        "renewal": {"auto_renew": False},
    }
    asyncio.run(
        DeepEvalEvaluator(JudgeConfig(enabled=True), metric_factory=lambda *a: Metric()).evaluate(
            CheckSpec(name="agent_rubric"),
            EvaluationCase(id="c", input="q", expected_output=expected),
            ExecutionResult(output=actual),
        )
    )
    assert "clause_inventory" not in json.loads(seen[0].expected_output)
    assert json.loads(seen[0].actual_output)["normalized_extraction"]["party_ids"] == ["P01"]


def test_actual_scenario_worker_replays_visible_events_and_retains_all_six_roles(
    tmp_path, monkeypatch
):
    import asyncio

    from ragnarok.config import CorpusConfig
    from ragnarok.corpus_adapter import CorpusAdapter
    from ragnarok.models import EvaluationCase

    monkeypatch.setenv("ODIN_FORCE_PROVIDER", "fake")
    adapter = CorpusAdapter(
        CorpusConfig(
            mode="agent",
            root=str(ROOT),
            workspace=str(tmp_path),
            backend_path="backend",
            allow_fake_provider=True,
        ),
        root=ROOT.parent,
    )
    result = asyncio.run(
        adapter.execute(
            EvaluationCase(
                id="PAY-03::odin",
                kind="agent",
                input="q",
                metadata={"agent": "odin", "corpus_case": "PAY-03"},
            ),
            "request",
        )
    )
    assert result.state in {"complete", "partial"}, result.errors
    assert result.metadata["known_contract_ids"] == ["C05"]
    assert result.output["known_contract_ids"] == ["C05"]


def test_recorded_evaluation_preserves_original_latency_and_rejects_changed_references(tmp_path):
    import asyncio

    from ragnarok.adapters import FixtureAdapter, RecordedAdapter
    from ragnarok.config import RunConfig
    from ragnarok.models import CheckSpec, Dataset, EvaluationCase, ExecutionResult
    from ragnarok.reporting import write_report
    from ragnarok.runner import run

    dataset = Dataset(
        id="d",
        cases=[
            EvaluationCase(
                id="c", input="q", expected_output="a", checks=[CheckSpec(name="exact_match")]
            )
        ],
    )
    original = asyncio.run(
        run(RunConfig(), dataset, FixtureAdapter({"c": ExecutionResult(output="a")}))
    )
    original.cases[0].execution.latency_ms = 1234
    path = tmp_path / "recorded.json"
    write_report(original, path)
    adapter = RecordedAdapter(path, dataset)
    replay = asyncio.run(run(RunConfig(adapter="recorded"), dataset, adapter))
    assert replay.cases[0].execution.latency_ms == 1234
    assert replay.cases[0].execution.metadata["recorded_run_id"] == original.run_id
    changed = dataset.model_copy(deep=True)
    changed.cases[0].expected_output = "changed"
    with pytest.raises(ValueError, match="dataset"):
        RecordedAdapter(path, changed)


def test_configured_judge_passes_schema_through_new_deepeval_methods(monkeypatch):
    import asyncio
    from types import SimpleNamespace

    from pydantic import BaseModel

    from ragnarok.compatible_judge import OdinJudge

    class Answer(BaseModel):
        value: int

    class FakeModel:
        def with_structured_output(self, schema, **kwargs):
            assert schema is Answer
            return SimpleNamespace(invoke=lambda prompt: Answer(value=4), ainvoke=self.structured)

        async def structured(self, prompt):
            return Answer(value=4)

        def invoke(self, prompt):
            return SimpleNamespace(content="unstructured text")

        async def ainvoke(self, prompt):
            return self.invoke(prompt)

    monkeypatch.setattr(OdinJudge, "load_model", lambda self: FakeModel())
    judge = OdinJudge()
    assert isinstance(judge.generate_with_schema("q", schema=Answer), Answer)
    assert isinstance(asyncio.run(judge.a_generate_with_schema("q", schema=Answer)), Answer)


def test_configured_judge_accepts_valid_json_content_when_provider_omits_tool_call(monkeypatch):
    import asyncio
    from types import SimpleNamespace

    from pydantic import BaseModel

    from ragnarok.compatible_judge import OdinJudge

    class Answer(BaseModel):
        value: int

    class JsonContentModel:
        def with_structured_output(self, schema, **kwargs):
            async def response(prompt):
                return {
                    "parsed": None,
                    "raw": SimpleNamespace(content='```json\n{"value":4}\n```'),
                    "parsing_error": None,
                }

            return SimpleNamespace(
                invoke=lambda p: {
                    "parsed": None,
                    "raw": SimpleNamespace(content='{"value":4}'),
                    "parsing_error": None,
                },
                ainvoke=response,
            )

    monkeypatch.setattr(OdinJudge, "load_model", lambda self: JsonContentModel())
    judge = OdinJudge()
    assert judge.generate_with_schema("q", schema=Answer).value == 4
    assert asyncio.run(judge.a_generate_with_schema("q", schema=Answer)).value == 4


def test_corpus_security_compiles_explicit_attack_invariants():
    from ragnarok.corpus import compile_datasets

    dataset = compile_datasets(ROOT)["security"]
    assert len(dataset.cases) == 3
    assert all(
        case.kind == "security" and case.security.required_evidence for case in dataset.cases
    )
    assert {c.metadata["attack_type"] for c in dataset.cases} == {"direct", "indirect", "tenant"}


def test_scenario_cache_and_workspace_include_the_requested_clock(tmp_path, monkeypatch):
    import asyncio

    from ragnarok.config import CorpusConfig
    from ragnarok.corpus_adapter import CorpusAdapter
    from ragnarok.models import EvaluationCase, ExecutionResult

    adapter = CorpusAdapter(
        CorpusConfig(mode="agent", root=str(ROOT), workspace=str(tmp_path), backend_path="backend"),
        root=ROOT.parent,
    )
    sent = []

    async def execute(payload):
        sent.append(payload)
        return ExecutionResult(output={"roles": {"odin": {"clock": payload["clock"]}}})

    monkeypatch.setattr(adapter, "_execute_payload", execute)

    async def exercise():
        output = []
        for clock in ["2027-01-15T09:00:00Z", "2027-01-28T12:00:00Z"]:
            case = EvaluationCase(
                id=clock,
                input="q",
                metadata={"agent": "odin", "corpus_case": "PAY-03", "clock": clock},
            )
            output.append(await adapter.execute(case, "request"))
        return output

    results = asyncio.run(exercise())
    assert len(sent) == 2 and sent[0]["workspace"] != sent[1]["workspace"]
    assert results[0].output["clock"] != results[1].output["clock"]


def test_shared_role_latency_retains_execution_duration_instead_of_cache_lookup(
    tmp_path, monkeypatch
):
    import asyncio

    from ragnarok.config import CorpusConfig, RunConfig
    from ragnarok.corpus_adapter import CorpusAdapter
    from ragnarok.models import CheckSpec, Dataset, EvaluationCase, ExecutionResult
    from ragnarok.runner import run

    adapter = CorpusAdapter(
        CorpusConfig(mode="agent", root=str(ROOT), workspace=str(tmp_path), backend_path="backend"),
        root=ROOT.parent,
    )

    async def execute(payload):
        await asyncio.sleep(0.03)
        return ExecutionResult(output={"roles": {"thor": {"value": 1}, "tyr": {"value": 1}}})

    monkeypatch.setattr(adapter, "_execute_payload", execute)
    dataset = Dataset(
        id="d",
        cases=[
            EvaluationCase(
                id=a,
                input="q",
                expected_output={"value": 1},
                checks=[CheckSpec(name="exact_match")],
                metadata={"agent": a, "corpus_case": "PAY-03"},
            )
            for a in ["thor", "tyr"]
        ],
    )
    report = asyncio.run(run(RunConfig(adapter="corpus"), dataset, adapter))
    latencies = [c.execution.latency_ms for c in report.cases]
    assert min(latencies) >= 25 and latencies[0] == latencies[1]


def test_recorded_secret_failure_is_preserved_after_report_redaction(tmp_path):
    import asyncio

    from ragnarok.adapters import FixtureAdapter, RecordedAdapter
    from ragnarok.config import RunConfig
    from ragnarok.models import CheckSpec, Dataset, EvaluationCase, ExecutionResult
    from ragnarok.reporting import write_report
    from ragnarok.runner import run

    canary = "SYNTHETIC_FOREIGN_COMPANY_CANARY_91"
    dataset = Dataset(
        id="d",
        cases=[
            EvaluationCase(
                id="c",
                input="q",
                checks=[CheckSpec(name="no_secret", params={"canaries": [canary]})],
            )
        ],
    )
    original = asyncio.run(
        run(RunConfig(), dataset, FixtureAdapter({"c": ExecutionResult(output=canary)}))
    )
    assert original.cases[0].checks[0].status == "failed"
    path = tmp_path / "source.json"
    write_report(original, path)
    assert canary not in path.read_text()
    replay = asyncio.run(
        run(RunConfig(adapter="recorded"), dataset, RecordedAdapter(path, dataset))
    )
    assert replay.cases[0].checks[0].status == "failed"


def test_recorded_redacted_text_is_not_sent_to_a_judge(tmp_path):
    import asyncio

    from ragnarok.adapters import FixtureAdapter, RecordedAdapter
    from ragnarok.config import RunConfig
    from ragnarok.models import CheckSpec, Dataset, EvaluationCase, ExecutionResult
    from ragnarok.reporting import write_report
    from ragnarok.runner import run

    canary = "SYNTHETIC_FOREIGN_COMPANY_CANARY_91"
    dataset = Dataset(
        id="d",
        cases=[
            EvaluationCase(
                id="c",
                input="q",
                checks=[
                    CheckSpec(name="no_secret", params={"canaries": [canary]}),
                    CheckSpec(name="answer_relevancy", required=False),
                ],
            )
        ],
    )
    original = asyncio.run(
        run(RunConfig(), dataset, FixtureAdapter({"c": ExecutionResult(output=canary)}))
    )
    path = tmp_path / "source.json"
    write_report(original, path)

    class Judge:
        async def evaluate(self, *args):
            raise AssertionError("Redacted evidence must not be re-judged")

    replay = asyncio.run(
        run(
            RunConfig(adapter="recorded"),
            dataset,
            RecordedAdapter(path, dataset),
            judge_evaluator=Judge(),
        )
    )
    check = next(c for c in replay.cases[0].checks if c.name == "answer_relevancy")
    assert check.status == "skipped" and "redacted" in check.reason


def test_recorded_retry_only_calls_judges_that_previously_errored(tmp_path):
    import asyncio

    from ragnarok.adapters import FixtureAdapter, RecordedAdapter
    from ragnarok.config import RunConfig
    from ragnarok.models import CheckResult, CheckSpec, Dataset, EvaluationCase, ExecutionResult
    from ragnarok.reporting import write_report
    from ragnarok.runner import run

    dataset = Dataset(
        id="d",
        cases=[
            EvaluationCase(id=i, input="q", checks=[CheckSpec(name="answer_relevancy")])
            for i in ["good", "retry"]
        ],
    )

    class FirstJudge:
        async def evaluate(self, spec, case, execution):
            return CheckResult(
                name=spec.name,
                status="passed" if case.id == "good" else "error",
                reason="prior",
                method="llm_judge",
            )

    original = asyncio.run(
        run(
            RunConfig(),
            dataset,
            FixtureAdapter({i: ExecutionResult(output="a") for i in ["good", "retry"]}),
            judge_evaluator=FirstJudge(),
        )
    )
    path = tmp_path / "source.json"
    write_report(original, path)
    called = []

    class RetryJudge:
        async def evaluate(self, spec, case, execution):
            called.append(case.id)
            return CheckResult(name=spec.name, status="passed", reason="new", method="llm_judge")

    replay = asyncio.run(
        run(
            RunConfig(adapter="recorded"),
            dataset,
            RecordedAdapter(path, dataset, retry_judge_errors=True),
            judge_evaluator=RetryJudge(),
        )
    )
    assert called == ["retry"] and replay.counts["passed"] == 2


def test_recurring_due_day_does_not_come_from_an_exceptional_first_due_date():
    from ragnarok.corpus_checks import thor_projection

    actual = {
        "payments": [
            {
                "amount": {"amount": 200000, "currency": "INR"},
                "frequency": "monthly",
                "payer": "Aurora Software",
                "first_due": "2026-12-20",
                "due_rule": "on the fifth day of that month at 17:00 UTC",
            }
        ]
    }
    assert thor_projection(actual)["monthly_payment_due_day_utc"] == 5
    actual["payments"][0]["due_rule"] = "within 5 days after invoice receipt"
    assert "monthly_payment_due_day_utc" not in thor_projection(actual)


def test_unredacted_quality_metrics_can_be_recomputed_without_changing_security_outcomes(tmp_path):
    import asyncio

    from ragnarok.adapters import FixtureAdapter, RecordedAdapter
    from ragnarok.config import RunConfig
    from ragnarok.models import CheckSpec, Dataset, EvaluationCase, ExecutionResult
    from ragnarok.reporting import write_report
    from ragnarok.runner import run

    dataset = Dataset(
        id="d",
        cases=[
            EvaluationCase(
                id="c",
                kind="agent",
                input="q",
                checks=[CheckSpec(name="json_fields", params={"expected": {"v": 1}})],
            )
        ],
    )
    original = asyncio.run(
        run(RunConfig(), dataset, FixtureAdapter({"c": ExecutionResult(output={"v": 1})}))
    )
    original.cases[0].checks[0].status = "failed"
    original.cases[0].checks[0].reason = "Older matcher had a bug"
    path = tmp_path / "source.json"
    write_report(original, path)
    replay = asyncio.run(
        run(RunConfig(adapter="recorded"), dataset, RecordedAdapter(path, dataset))
    )
    assert replay.cases[0].checks[0].status == "passed"
