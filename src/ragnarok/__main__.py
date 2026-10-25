"""CLI: ragnarok validate DATASET, or ragnarok run --config CONFIG."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from .adapters import FixtureAdapter, HTTPAdapter
from .config import RunConfig
from .datasets import load_dataset
from .models import ExecutionResult
from .reporting import redact, write_report
from .runner import run


def _relative(base: Path, name: str) -> Path:
    path = Path(name)
    return path if path.is_absolute() else base / path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Agent/RAG evaluation and security pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    validation = sub.add_parser(
        "validate", help="Validate a JSON dataset without invoking a target"
    )
    validation.add_argument("dataset")
    evaluation = sub.add_parser("run", help="Run a configured evaluation")
    evaluation.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            dataset = load_dataset(args.dataset)
            print(f"Dataset valid: {len(dataset.cases)} cases")
            return 0
        path = Path(args.config).resolve()
        config = RunConfig.model_validate_json(path.read_text(encoding="utf-8"))
        dataset = load_dataset(_relative(path.parent, config.dataset))
        if config.adapter == "fixture":
            if not config.fixtures:
                raise ValueError("fixture adapter requires a fixtures JSON path")
            raw = json.loads(_relative(path.parent, config.fixtures).read_text(encoding="utf-8"))
            adapter = FixtureAdapter(
                {key: ExecutionResult.model_validate(value) for key, value in raw.items()}
            )
        elif config.adapter == "http":
            if config.http is None:
                raise ValueError("http adapter requires an http configuration object")
            adapter = HTTPAdapter(config.http)
        elif config.adapter == "odin":
            from .odin_adapter import OdinAdapter

            if config.odin is None:
                raise ValueError("odin adapter requires an odin configuration object")
            adapter = OdinAdapter(config.odin, root=path.parent)
        else:
            raise ValueError(
                "CLI adapter must be fixture, http or odin; use GraphAdapter through Python"
            )
        report = asyncio.run(run(config, dataset, adapter))
        write_report(report, _relative(path.parent, config.report))
        print(
            json.dumps(
                {"run_id": report.run_id, "counts": report.counts, "exit_code": report.exit_code}
            )
        )
        return report.exit_code
    except ValidationError as exc:
        issues = [
            ".".join(map(str, error["loc"])) + ": " + error["msg"]
            for error in exc.errors(include_input=False, include_url=False)
        ]
        print("Invalid configuration/data: " + "; ".join(issues), file=sys.stderr)
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print("Unable to run evaluation: " + redact(str(exc)), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
