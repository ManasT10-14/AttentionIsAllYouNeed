"""Adapters observe the product; they never manufacture missing telemetry."""

import os
from collections.abc import Callable, Mapping
from typing import Any, Protocol
from urllib.parse import urljoin, urlsplit

import httpx

from .config import HTTPConfig
from .models import EvaluationCase, ExecutionResult


class Adapter(Protocol):
    async def execute(self, case: EvaluationCase, request_id: str) -> ExecutionResult: ...


class FixtureAdapter:
    """Recorded synthetic responses, not a simulated live product integration."""

    def __init__(self, results: Mapping[str, ExecutionResult]):
        self.results = results

    async def execute(self, case: EvaluationCase, request_id: str) -> ExecutionResult:
        return self.results[case.id].model_copy(deep=True)


def field_at(value: Any, path: str) -> Any:
    """Read dotted object keys/list indexes; never evaluate expressions."""
    for part in path.split("."):
        if isinstance(value, list):
            value = value[int(part)]
        elif isinstance(value, dict):
            value = value[part]
        else:
            raise KeyError(path)
    return value


class HTTPAdapter:
    def __init__(self, config: HTTPConfig, *, client: httpx.AsyncClient | None = None):
        self.config = config
        self.client = client
        self.url = urljoin(config.base_url.rstrip("/") + "/", config.endpoint)
        origin = urlsplit(config.base_url)
        target = urlsplit(self.url)
        if origin.scheme not in {"http", "https"} or not origin.netloc:
            raise ValueError("base_url must have an HTTP(S) origin")
        if (origin.scheme, origin.netloc) != (target.scheme, target.netloc):
            raise ValueError("endpoint must stay on the configured origin")
        if origin.username or origin.password:
            raise ValueError("credentials belong in environment variables, not URLs")
        allowed = set(ExecutionResult.model_fields)
        if set(config.response_mapping) - allowed:
            raise ValueError("response_mapping contains an unknown execution field")
        if "output" not in config.response_mapping:
            raise ValueError("response_mapping must map output")

    async def execute(self, case: EvaluationCase, request_id: str) -> ExecutionResult:
        headers = {self.config.request_id_header: request_id}
        if self.config.auth_env:
            credential = os.environ.get(self.config.auth_env)
            if not credential:
                raise ValueError("Product authentication environment variable is missing")
            headers[self.config.auth_header] = self.config.auth_prefix + credential
        payload = dict(self.config.payload)
        payload[self.config.input_field] = case.input
        if self.client is not None:
            return await self._request(self.client, headers, payload)
        async with httpx.AsyncClient(trust_env=False) as client:
            return await self._request(client, headers, payload)

    async def _request(self, client, headers, payload) -> ExecutionResult:
        response = await client.request(
            self.config.method,
            self.url,
            json=payload,
            headers=headers,
            timeout=self.config.timeout_s,
            follow_redirects=False,
        )
        if not self.config.allow_error_responses or response.status_code < 400:
            response.raise_for_status()
        try:
            raw = response.json()
        except ValueError:
            if not self.config.allow_error_responses or response.status_code < 400:
                raise
            raw = {}
        normalized: dict[str, Any] = {}
        for name, path in self.config.response_mapping.items():
            try:
                value = field_at(raw, path)
            except (KeyError, IndexError):
                if name == "output":
                    if response.status_code >= 400 and self.config.allow_error_responses:
                        normalized["output"] = None
                        continue
                    raise ValueError("Configured output mapping was absent") from None
                continue
            if name in {
                "documents",
                "observed_documents",
                "model_context",
                "tools",
                "events",
                "citations",
            } and isinstance(value, list):
                value = {"state": "complete", "items": value}
            normalized[name] = value
        normalized.setdefault("metadata", {})["http_status"] = response.status_code
        return ExecutionResult.model_validate(normalized)


class GraphAdapter:
    """Pass a compiled graph and product-specific mappers, without product imports."""

    def __init__(
        self,
        graph: Any,
        *,
        input_mapper: Callable[[EvaluationCase], Any],
        output_mapper: Callable[[Any], ExecutionResult],
        graph_config: dict | None = None,
    ):
        self.graph = graph
        self.input_mapper = input_mapper
        self.output_mapper = output_mapper
        self.graph_config = graph_config or {}

    async def execute(self, case: EvaluationCase, request_id: str) -> ExecutionResult:
        config = {
            **self.graph_config,
            "metadata": {
                **self.graph_config.get("metadata", {}),
                "evaluation_request_id": request_id,
            },
        }
        raw = await self.graph.ainvoke(self.input_mapper(case), config=config)
        result = self.output_mapper(raw)
        if not isinstance(result, ExecutionResult):
            raise TypeError("output_mapper must return ExecutionResult")
        return result
