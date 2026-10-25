"""Validated configuration. Secrets are environment variable names, never values."""

from typing import Literal

from pydantic import Field, model_validator

from .models import Model


class HTTPConfig(Model):
    base_url: str
    endpoint: str
    method: str = "POST"
    input_field: str = "input"
    payload: dict = Field(default_factory=dict)
    response_mapping: dict[str, str] = Field(default_factory=lambda: {"output": "output"})
    auth_env: str | None = None
    auth_header: str = "Authorization"
    auth_prefix: str = "Bearer "
    request_id_header: str = "X-Request-ID"
    timeout_s: float = Field(default=30, gt=0, allow_inf_nan=False)
    allow_error_responses: bool = False


class JudgeConfig(Model):
    enabled: bool = False
    model: str = "gpt-4.1-mini"
    timeout_s: float = Field(default=60, gt=0, allow_inf_nan=False)


class TracingConfig(Model):
    enabled: bool = False
    project: str = "ragnarok-evaluation"
    api_key_env: str = "LANGSMITH_API_KEY"
    endpoint: str = "https://api.smith.langchain.com"
    publish_timeout_s: float = Field(default=10, gt=0, allow_inf_nan=False)


class OdinConfig(Model):
    backend_path: str = "../../backend"
    company_id: str = Field(min_length=1)
    operation: Literal["ask", "retrieval", "analysis", "event", "update", "tool_probe"] = "ask"
    parameters: dict = Field(default_factory=dict)
    disposable_database: bool = False
    allow_fake_provider: bool = False
    product_tracing: bool = False
    trace_project: str = "ragnarok-odin"
    max_records: int = Field(default=10000, ge=1, le=100000)

    @model_validator(mode="after")
    def graph_safety(self):
        if self.operation in {"analysis", "event", "update"} and not self.disposable_database:
            raise ValueError("write-producing graphs require disposable_database=true")
        if any(k in self.parameters for k in ("company_id", "run_id", "scenario_id")):
            raise ValueError("company/run scope cannot be overridden through parameters")
        allowed = {
            "ask": {"contract_ids"},
            "retrieval": {"contract_ids", "clause_types", "top_k", "current_only"},
            "analysis": {"contract_ids", "force"},
            "event": {"event_id"},
            "update": {"contract_id", "from_version", "to_version"},
            "tool_probe": set(),
        }[self.operation]
        if set(self.parameters) - allowed:
            raise ValueError("unsupported Odin parameters for the configured operation")
        return self


class RunConfig(Model):
    dataset: str = "datasets/odin/synthetic.json"
    report: str = "reports/evaluation.json"
    adapter: str = "fixture"
    fixtures: str | None = None
    http: HTTPConfig | None = None
    odin: OdinConfig | None = None
    corpus: "CorpusConfig | None" = None
    concurrency: int = Field(default=1, ge=1, le=16)
    case_timeout_s: float = Field(default=30, gt=0, allow_inf_nan=False)
    judge: JudgeConfig = Field(default_factory=JudgeConfig)
    tracing: TracingConfig = Field(default_factory=TracingConfig)
    include_tags: list[str] = Field(default_factory=list)
    allow_side_effects: bool = False


class CorpusConfig(Model):
    root: str = "../../corpus"
    workspace: str = "../../work/evaluation"
    backend_path: str = "../../backend"
    mode: Literal["agent", "thor", "rag", "retrieval", "security"]
    dense: bool = False
    allow_fake_provider: bool = False
    product_tracing: bool = False
    trace_project: str = "ragnarok-odin"


RunConfig.model_rebuild()
