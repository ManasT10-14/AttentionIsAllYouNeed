"""A fixture-serving FastAPI app for testing the HTTP integration path.

This does not call a model or implement Odin. All records are synthetic.
Run: uv run uvicorn --app-dir eval examples.mock_product:app --host 127.0.0.1 --port 8000
"""

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, JsonValue

ROOT = Path(__file__).resolve().parents[1]


class Request(BaseModel):
    input: JsonValue


def create_app(*, vulnerable: bool = False) -> FastAPI:
    dataset = json.loads((ROOT / "datasets/odin/synthetic.json").read_text(encoding="utf-8"))
    results_file = "vulnerable-results.json" if vulnerable else "safe-results.json"
    results = json.loads((ROOT / "datasets/odin" / results_file).read_text(encoding="utf-8"))
    application = FastAPI(title="Synthetic Odin integration fixture")

    @application.post("/evaluate")
    async def evaluate(request: Request):
        for case in dataset["cases"]:
            if case["input"] == request.input:
                result = results[case["id"]]
                status = result.get("metadata", {}).get("http_status", 200)
                return JSONResponse(content=result, status_code=status)
        return JSONResponse(
            content={"output": "No synthetic fixture for this input"}, status_code=404
        )

    return application


app = create_app()
