"""Isolated product execution. Cancellation kills and reaps the worker."""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

from .config import OdinConfig
from .models import ExecutionResult


class OdinAdapter:
    def __init__(self, config: OdinConfig, *, root: Path):
        self.config = config
        self.root = root.resolve()
        self.backend = (self.root / config.backend_path).resolve()
        self.worker_command = [sys.executable, "-m", "ragnarok.odin_worker"]
        self.last_returncode = None

    async def execute(self, case, request_id):
        case_parameters = case.metadata.get("odin_parameters", {})
        if not isinstance(case_parameters, dict):
            raise ValueError("metadata.odin_parameters must be an object")
        config = OdinConfig.model_validate(
            {
                **self.config.model_dump(),
                "parameters": {**self.config.parameters, **case_parameters},
            }
        )
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            [str(Path(__file__).resolve().parents[1]), str(self.backend)]
        )
        env["LANGSMITH_TRACING"] = "true" if self.config.product_tracing else "false"
        env["LANGCHAIN_TRACING_V2"] = "false"
        env["LANGSMITH_PROJECT"] = self.config.trace_project
        env["DEEPEVAL_TELEMETRY_OPT_OUT"] = "YES"
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        proc = await asyncio.create_subprocess_exec(
            *self.worker_command,
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            creationflags=flags,
        )
        # Golden outputs/check definitions never cross the product boundary.
        payload = json.dumps(
            {"config": config.model_dump(), "input": case.input, "request_id": request_id}
        ).encode()
        try:
            stdout, _ = await proc.communicate(payload)
        except BaseException:
            if proc.returncode is None:
                proc.kill()
            await proc.wait()
            raise
        finally:
            self.last_returncode = proc.returncode
        if proc.returncode != 0:
            return ExecutionResult(
                state="error",
                errors=["Odin worker failed; verify backend dependencies/configuration"],
            )
        try:
            return ExecutionResult.model_validate_json(stdout)
        except ValueError:
            return ExecutionResult(
                state="error", errors=["Odin worker returned an invalid execution envelope"]
            )
