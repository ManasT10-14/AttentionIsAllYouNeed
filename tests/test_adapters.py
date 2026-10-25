import asyncio

import httpx
import pytest

from ragnarok.adapters import FixtureAdapter, GraphAdapter, HTTPAdapter
from ragnarok.config import HTTPConfig
from ragnarok.models import EvaluationCase, ExecutionResult

CASE = EvaluationCase(id="one", input="When does it renew?")


def test_http_configurable_request_and_response(monkeypatch):
    monkeypatch.setenv("TEST_PRODUCT_TOKEN", "synthetic-token")

    async def handler(request):
        assert request.url.path == "/analyze"
        assert b'"question":"When does it renew?"' in request.content
        assert request.headers["Authorization"] == "Bearer synthetic-token"
        assert request.headers["X-Request-ID"] == "request-one"
        return httpx.Response(200, json={"result": {"answer": "December", "docs": []}})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = HTTPAdapter(
                HTTPConfig(
                    base_url="http://product.test",
                    endpoint="/analyze",
                    input_field="question",
                    auth_env="TEST_PRODUCT_TOKEN",
                    response_mapping={"output": "result.answer", "documents": "result.docs"},
                ),
                client=client,
            )
            result = await adapter.execute(CASE, "request-one")
            assert result.output == "December"
            assert result.documents.state == "complete"
            assert result.tools.state == "unavailable"

    asyncio.run(scenario())


def test_malformed_evidence_does_not_become_unavailable():
    async def handler(request):
        return httpx.Response(200, json={"output": "ok", "docs": "not a list"})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = HTTPAdapter(
                HTTPConfig(
                    base_url="http://p.test",
                    endpoint="/",
                    response_mapping={"output": "output", "documents": "docs"},
                ),
                client=client,
            )
            with pytest.raises(ValueError):
                await adapter.execute(CASE, "r")

    asyncio.run(scenario())


def test_cross_origin_endpoint_rejected():
    with pytest.raises(ValueError, match="origin"):
        HTTPAdapter(HTTPConfig(base_url="https://p.test", endpoint="https://other.test/"))


def test_http_does_not_follow_redirects():
    async def handler(request):
        return httpx.Response(307, headers={"Location": "https://other.test/"})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = HTTPAdapter(HTTPConfig(base_url="http://p.test", endpoint="/"), client=client)
            with pytest.raises(httpx.HTTPStatusError):
                await adapter.execute(CASE, "r")

    asyncio.run(scenario())


def test_fixture_results_are_independent():
    adapter = FixtureAdapter({"one": ExecutionResult(output="ok")})
    first = asyncio.run(adapter.execute(CASE, "r"))
    first.errors.append("changed")
    assert not asyncio.run(adapter.execute(CASE, "r2")).errors


def test_graph_is_invoked_once_with_user_mapping():
    class Graph:
        calls = 0

        async def ainvoke(self, state, config):
            self.calls += 1
            assert state == {"query": CASE.input}
            assert config["recursion_limit"] == 7
            return {"answer": "December"}

    graph = Graph()
    adapter = GraphAdapter(
        graph,
        input_mapper=lambda c: {"query": c.input},
        output_mapper=lambda raw: ExecutionResult(output=raw["answer"]),
        graph_config={"recursion_limit": 7},
    )
    assert asyncio.run(adapter.execute(CASE, "r")).output == "December"
    assert graph.calls == 1


def test_expected_rejection_can_be_evaluated_instead_of_adapter_error():
    async def handler(request):
        return httpx.Response(403, json={"detail": "Access denied"})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = HTTPAdapter(
                HTTPConfig(base_url="http://p.test", endpoint="/", allow_error_responses=True),
                client=client,
            )
            result = await adapter.execute(CASE, "r")
            assert result.state == "complete"
            assert result.metadata["http_status"] == 403
            assert result.output is None

    asyncio.run(scenario())
