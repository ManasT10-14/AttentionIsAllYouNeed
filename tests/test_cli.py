import json
import os
import subprocess
import sys
from pathlib import Path


def invoke(*args):
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")}
    return subprocess.run(
        [sys.executable, "-m", "ragnarok", *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def test_cli_resolves_paths_relative_to_config(tmp_path):
    (tmp_path / "dataset.json").write_text(
        json.dumps(
            {
                "id": "d",
                "cases": [
                    {
                        "id": "c",
                        "input": "q",
                        "expected_output": "yes",
                        "checks": [{"name": "exact_match"}],
                    }
                ],
            }
        )
    )
    (tmp_path / "fixtures.json").write_text(json.dumps({"c": {"output": "yes"}}))
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {"dataset": "dataset.json", "fixtures": "fixtures.json", "report": "report.json"}
        )
    )
    completed = invoke("run", "--config", str(config))
    assert completed.returncode == 0, completed.stderr
    assert json.loads((tmp_path / "report.json").read_text())["counts"]["passed"] == 1


def test_cli_invalid_configuration_is_actionable(tmp_path):
    config = tmp_path / "config.json"
    config.write_text('{"concurrency": 0}')
    completed = invoke("run", "--config", str(config))
    assert completed.returncode == 2
    assert "concurrency" in completed.stderr


def test_cli_validates_dataset_without_adapter(tmp_path):
    path = tmp_path / "dataset.json"
    path.write_text('{"id":"d","cases":[]}')
    completed = invoke("validate", str(path))
    assert completed.returncode == 0 and "0 cases" in completed.stdout
