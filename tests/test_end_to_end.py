import asyncio
import json
from pathlib import Path
from typing import TypedDict

import httpx

from examples.mock_product import create_app
from ragnarok.adapters import FixtureAdapter, GraphAdapter, HTTPAdapter
from ragnarok.config import RunConfig
from ragnarok.datasets import load_dataset
from ragnarok.models import Dataset, ExecutionResult
from ragnarok.runner import run

ROOT = Path(__file__).parents[1]


def test_synthetic_safe_and_vulnerable_results():
    data = load_dataset(ROOT / "datasets/odin/synthetic.json")
    for name, expected_exit in [("safe", 0), ("vulnerable", 1)]:
        raw = json.loads((ROOT / f"datasets/odin/{name}-results.json").read_text())
        adapter = FixtureAdapter(
            {key: ExecutionResult.model_validate(value) for key, value in raw.items()}
        )
        report = asyncio.run(run(RunConfig(), data, adapter))
        assert report.exit_code == expected_exit
        assert bool(report.security_findings) == (name == "vulnerable")
        assert report.counts["skipped"] == 5  # Paid judge metrics disabled.


def test_actual_fastapi_application_through_httpx_asgi_transport():
    config = RunConfig.model_validate_json((ROOT / "configs/http.example.json").read_text())
    data = load_dataset(ROOT / "datasets/odin/synthetic.json")

    async def scenario():
        transport = httpx.ASGITransport(app=create_app())
        async with httpx.AsyncClient(transport=transport) as client:
            report = await run(config, data, HTTPAdapter(config.http, client=client))
            assert report.exit_code == 0
            assert report.cases[-1].execution.metadata["http_status"] == 422

    asyncio.run(scenario())


def test_actual_compiled_langgraph_without_product_schema_assumptions():
    from langgraph.graph import END, START, StateGraph

    class State(TypedDict):
        query: str
        answer: str

    async def reply(state):
        return {"answer": "synthetic answer"}

    graph = StateGraph(State)
    graph.add_node("example_reply", reply)
    graph.add_edge(START, "example_reply")
    graph.add_edge("example_reply", END)
    adapter = GraphAdapter(
        graph.compile(),
        input_mapper=lambda case: {"query": case.input},
        output_mapper=lambda state: ExecutionResult(output=state["answer"]),
        graph_config={"recursion_limit": 5},
    )
    data = Dataset.model_validate(
        {
            "id": "compiled-graph",
            "cases": [
                {
                    "kind": "quality",
                    "id": "c",
                    "input": "question",
                    "expected_output": "synthetic answer",
                    "checks": [{"name": "exact_match"}],
                }
            ],
        }
    )
    assert asyncio.run(run(RunConfig(adapter="graph"), data, adapter)).exit_code == 0
