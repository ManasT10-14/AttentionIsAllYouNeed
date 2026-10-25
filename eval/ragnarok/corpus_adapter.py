"""Corpus worker transport and one real graph execution per scenario, shared by roles."""

import asyncio
import sys
import time
from pathlib import Path
from uuid import uuid4

from .config import OdinConfig
from .models import ExecutionResult
from .odin_adapter import OdinAdapter


class CorpusAdapter(OdinAdapter):
    preserve_execution_latency = True

    def __init__(self, config, *, root, cases=None):
        super().__init__(
            OdinConfig(
                company_id="P01",
                backend_path=config.backend_path,
                product_tracing=config.product_tracing,
                trace_project=config.trace_project,
            ),
            root=root,
        )
        self.corpus_config = config
        self.corpus_root = (Path(root) / config.root).resolve()
        self.workspace = (Path(root) / config.workspace / str(uuid4())).resolve()
        if self.workspace.is_relative_to(self.corpus_root):
            raise ValueError("Evaluation workspace must be outside the corpus")
        self.worker_command = [sys.executable, "-m", "ragnarok.corpus_worker"]
        self._results = {}
        self._locks = {}
        self._batch = {}
        if config.mode == "retrieval" and cases is not None:
            for case in cases:
                cid = case.metadata.get("contract_id")
                self._batch.setdefault(cid, {})[case.id] = case.input

    async def execute(self, case, request_id):
        mode = self.corpus_config.mode
        batching = mode == "retrieval" and case.metadata.get("contract_id") in self._batch
        key = (
            ("retrieval:" + case.metadata["contract_id"])
            if batching
            else (case.metadata.get("corpus_case") if mode == "agent" else case.id)
        )
        if not key:
            raise ValueError("Corpus agent cases require metadata.corpus_case")
        if mode == "agent":
            key = f"{key}@{case.metadata.get('clock') or 'final'}"
        # Agent vectors share actual upstream state; never inject reference fixtures.
        lock_key = case.metadata.get("contract_id", key) if mode in {"retrieval", "rag"} else key
        lock = self._locks.setdefault(lock_key, asyncio.Lock())
        async with lock:
            if key not in self._results:
                unit = (
                    key
                    if mode in {"agent", "thor", "security"}
                    else case.metadata.get("contract_id", "sources")
                )
                unit = "".join(c if c.isalnum() or c in "_-" else "_" for c in unit)
                payload = {
                    "mode": mode,
                    "corpus_root": str(self.corpus_root),
                    "workspace": str(self.workspace / unit),
                    "dense": self.corpus_config.dense,
                    "allow_fake_provider": self.corpus_config.allow_fake_provider,
                    "case_id": case.metadata.get("corpus_case"),
                    "clock": case.metadata.get("clock"),
                    "contract_id": case.metadata.get("contract_id"),
                    "question": case.input,
                    "parameters": case.metadata.get("odin_parameters", {}),
                    "request_id": request_id,
                    "attack_type": case.metadata.get("attack_type"),
                }
                if batching:
                    payload["questions"] = self._batch[case.metadata["contract_id"]]
                try:
                    started = time.perf_counter()
                    self._results[key] = await self._execute_payload(payload)
                    self._results[key].latency_ms = (time.perf_counter() - started) * 1000
                    self._results[key].metadata["latency_scope"] = (
                        "shared_scenario_worker" if mode == "agent" else "worker_elapsed"
                    )
                except asyncio.CancelledError:
                    self._results[key] = ExecutionResult(
                        state="error", errors=["Scenario worker timed out or was cancelled"]
                    )
                    raise
            result = self._results[key].model_copy(deep=True)
        if batching and result.state != "error":
            selected = ExecutionResult.model_validate(result.output["batch"][case.id])
            selected.trace_id = result.trace_id
            selected.metadata = {**result.metadata, **selected.metadata}
            result = selected
        if mode == "agent" and result.state != "error":
            agent = case.metadata.get("agent")
            result.output = result.output["roles"][agent]
            result.tools.items = [tool for tool in result.tools.items if tool.actor == agent]
            result.events.items = [
                event
                for event in result.events.items
                if event.actor == agent or event.target == agent
            ]
            result.metadata["agent"] = agent
        return result
