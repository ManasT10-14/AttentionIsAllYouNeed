"""Public contract: target observations are separate from expected evidence."""

from datetime import datetime
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, JsonValue, PrivateAttr, model_validator

Status = Literal["passed", "failed", "error", "skipped", "invalid"]
Severity = Literal["info", "low", "medium", "high", "critical"]
T = TypeVar("T")


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Evidence(Model, Generic[T]):
    state: Literal["unavailable", "partial", "complete"] = "unavailable"
    items: list[T] = Field(default_factory=list)
    reason: str | None = None

    @model_validator(mode="after")
    def validate_availability(self):
        if self.state == "unavailable" and self.items:
            raise ValueError("unavailable evidence cannot contain records")
        return self


class Document(Model):
    id: str
    text: str
    tenant_id: str | None = None
    clause_id: str | None = None


class ToolEvent(Model):
    name: str
    arguments: dict[str, JsonValue] = Field(default_factory=dict)
    phase: Literal["requested", "authorized", "attempted", "executed", "failed"]
    authorized: bool | None = None
    approved: bool | None = None
    error: str | None = None


class WorkflowEvent(Model):
    kind: str
    actor: str | None = None
    target: str | None = None


class Citation(Model):
    document_id: str
    clause_id: str | None = None
    quote: str = Field(min_length=1)


class Usage(Model):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    currency: str | None = None


class ExecutionResult(Model):
    output: JsonValue = None
    state: Literal["complete", "partial", "error"] = "complete"
    documents: Evidence[Document] = Field(default_factory=Evidence[Document])
    observed_documents: Evidence[Document] = Field(default_factory=Evidence[Document])
    model_context: Evidence[str] = Field(default_factory=Evidence[str])
    tools: Evidence[ToolEvent] = Field(default_factory=Evidence[ToolEvent])
    events: Evidence[WorkflowEvent] = Field(default_factory=Evidence[WorkflowEvent])
    citations: Evidence[Citation] = Field(default_factory=Evidence[Citation])
    latency_ms: float = Field(default=0, ge=0, allow_inf_nan=False)
    errors: list[str] = Field(default_factory=list)
    usage: Usage | None = None
    trace_id: str | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class CheckSpec(Model):
    name: str = Field(min_length=1)
    enabled: bool = True
    required: bool = True
    threshold: float = Field(default=1, ge=0, le=1, allow_inf_nan=False)
    params: dict[str, JsonValue] = Field(default_factory=dict)


class EvaluationCase(Model):
    kind: Literal["quality", "agent"] = "quality"
    id: str = Field(min_length=1)
    input: JsonValue
    expected_output: JsonValue = None
    reference_context: list[Document] | None = None
    expected_relevant_document_ids: list[str] | None = None
    checks: list[CheckSpec] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    enabled: bool = True
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unique_checks(self):
        names = [check.name for check in self.checks]
        if len(names) != len(set(names)):
            raise ValueError("check names must be unique within a case")
        return self


class SecurityScenario(Model):
    attack_category: str
    invariant: str = Field(min_length=1)
    severity: Severity = "high"
    evaluation_method: Literal["deterministic"] = "deterministic"
    required_evidence: list[
        Literal[
            "output",
            "documents",
            "observed_documents",
            "model_context",
            "tools",
            "events",
            "citations",
            "usage",
        ]
    ] = Field(default_factory=list)
    side_effecting: bool = False


class SecurityCase(EvaluationCase):
    kind: Literal["security"] = "security"
    security: SecurityScenario


Case = Annotated[SecurityCase | EvaluationCase, Field(discriminator="kind")]


class Dataset(Model):
    id: str = Field(min_length=1)
    synthetic: bool = True
    cases: list[Case]

    @model_validator(mode="after")
    def unique_ids(self):
        seen: set[str] = set()
        for case in self.cases:
            if case.id in seen:
                raise ValueError(f"duplicate case id: {case.id}")
            seen.add(case.id)
        return self


class CheckResult(Model):
    name: str
    status: Status
    reason: str
    score: float | None = Field(default=None, allow_inf_nan=False)
    threshold: float | None = None
    required: bool = True
    category: Literal["quality", "agent", "security"] = "quality"
    severity: Severity | None = None
    method: Literal["deterministic", "llm_judge"] = "deterministic"


class CaseReport(Model):
    case_id: str
    kind: Literal["quality", "agent", "security"]
    execution: ExecutionResult
    checks: list[CheckResult]
    observer_trace_id: str | None = None
    observer_warning: str | None = None


class RunReport(Model):
    _redaction_values: list[str] = PrivateAttr(default_factory=list)
    schema_version: str = "1.0"
    run_id: str
    timestamp: datetime
    dataset_id: str
    dataset_sha256: str
    config_sha256: str
    adapter: str
    synthetic: bool
    package_versions: dict[str, str]
    cases: list[CaseReport]
    counts: dict[Status, int]
    security_findings: list[dict[str, JsonValue]] = Field(default_factory=list)
    latency: dict[str, float | None]
    usage: dict[str, JsonValue]
    exit_code: int
