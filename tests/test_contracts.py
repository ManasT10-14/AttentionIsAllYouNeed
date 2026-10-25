import json

import pytest
from pydantic import ValidationError

from ragnarok.config import RunConfig
from ragnarok.datasets import load_dataset
from ragnarok.models import Document, EvaluationCase, Evidence, ExecutionResult, SecurityCase


def test_unavailable_is_not_known_empty():
    unknown = ExecutionResult()
    known_empty = ExecutionResult(documents=Evidence[Document](state="complete"))
    assert unknown.documents.state == "unavailable"
    assert known_empty.documents.state == "complete"
    assert unknown.documents.items == known_empty.documents.items == []


def test_unavailable_cannot_contain_records():
    with pytest.raises(ValidationError, match="unavailable"):
        Evidence[Document](items=[Document(id="a", text="clause")])


@pytest.mark.parametrize("payload", [{"latency_ms": -1}, {"invented": True}])
def test_bad_execution_is_rejected(payload):
    with pytest.raises(ValidationError):
        ExecutionResult(**payload)


def test_security_case_requires_an_explicit_invariant():
    with pytest.raises(ValidationError):
        SecurityCase(id="s", input="attack", checks=[])


def test_disabled_metric_stays_explicit():
    case = EvaluationCase(id="x", input="q", checks=[{"name": "faithfulness", "enabled": False}])
    assert not case.checks[0].enabled


@pytest.mark.parametrize("kwargs", [{"concurrency": 0}, {"case_timeout_s": 0}, {"unknown": 1}])
def test_config_rejects_invalid_settings(kwargs):
    with pytest.raises(ValidationError):
        RunConfig(**kwargs)


def test_duplicate_ids_are_actionable(tmp_path):
    path = tmp_path / "cases.json"
    path.write_text(
        json.dumps(
            {"id": "d", "cases": [{"id": "same", "input": "q"}, {"id": "same", "input": "q2"}]}
        )
    )
    with pytest.raises(ValueError, match="duplicate.*same"):
        load_dataset(path)


def test_loader_identifies_bad_file(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{broken")
    with pytest.raises(ValueError, match="broken.json"):
        load_dataset(path)
