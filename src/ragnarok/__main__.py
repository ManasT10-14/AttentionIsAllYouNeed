"""CLI: ragnarok validate DATASET, or ragnarok run --config CONFIG."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from .adapters import FixtureAdapter, HTTPAdapter, RecordedAdapter
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
    corpus_validation = sub.add_parser(
        "corpus-validate", help="Validate corpus hashes, citations and release visibility"
    )
    corpus_validation.add_argument("root", nargs="?", default="corpus")
    corpus_build = sub.add_parser("corpus-build", help="Compile evaluator-only golden datasets")
    corpus_build.add_argument("root", nargs="?", default="corpus")
    corpus_build.add_argument("--output", default="datasets/corpus")
    evaluation = sub.add_parser("run", help="Run a configured evaluation")
    evaluation.add_argument("--config", required=True)
    evaluation.add_argument(
        "--recorded-report",
        help="Re-score matching recorded observations without executing the product",
    )
    evaluation.add_argument(
        "--output", help="Optional output report path relative to the current directory"
    )
    evaluation.add_argument(
        "--retry-judge-errors",
        action="store_true",
        help="With recorded-report, retry only errored judges and retain other outcomes",
    )
    args = parser.parse_args(argv)
    try:
        if args.command in {"corpus-validate", "corpus-build"}:
            from .corpus import compile_datasets, validate_corpus

            summary = validate_corpus(args.root)
            if args.command == "corpus-build":
                destination = Path(args.output)
                destination.mkdir(parents=True, exist_ok=True)
                datasets = compile_datasets(args.root)
                for name, dataset in datasets.items():
                    (destination / f"{name}.json").write_text(
                        dataset.model_dump_json(indent=2), encoding="utf-8"
                    )
                summary["compiled"] = {key: len(value.cases) for key, value in datasets.items()}
            print(json.dumps(summary))
            return 0
        if args.command == "validate":
            dataset = load_dataset(args.dataset)
            print(f"Dataset valid: {len(dataset.cases)} cases")
            return 0
        path = Path(args.config).resolve()
        config = RunConfig.model_validate_json(path.read_text(encoding="utf-8"))
        dataset = load_dataset(_relative(path.parent, config.dataset))
        if args.recorded_report:
            output_path = (
                Path(args.output).resolve()
                if args.output
                else _relative(path.parent, config.report).resolve()
            )
            if output_path == Path(args.recorded_report).resolve():
                raise ValueError("Rescore output must differ from the source report")
            adapter = RecordedAdapter(
                args.recorded_report, dataset, retry_judge_errors=args.retry_judge_errors
            )
            config = config.model_copy(update={"adapter": "recorded"})
            if args.retry_judge_errors:
                config = config.model_copy(update={"concurrency": 1})
        elif args.retry_judge_errors:
            raise ValueError("retry-judge-errors requires recorded-report")
        elif config.adapter == "fixture":
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
        elif config.adapter == "corpus":
            from .corpus_adapter import CorpusAdapter

            if config.corpus is None:
                raise ValueError("corpus adapter requires a corpus configuration object")
            adapter = CorpusAdapter(config.corpus, root=path.parent, cases=dataset.cases)
        else:
            raise ValueError(
                "CLI adapter must be fixture, http or odin; use GraphAdapter through Python"
            )
        report = asyncio.run(run(config, dataset, adapter))
        write_report(
            report, Path(args.output) if args.output else _relative(path.parent, config.report)
        )
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
