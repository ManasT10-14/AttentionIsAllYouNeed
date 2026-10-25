"""On-demand golden suite: runs a ragnarok config (eval/configs/*.json) in a background thread, writes the
report under reports/ and keeps a compact summary as an `eval_suite` record."""
from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from odin.core.config import ROOT, odin_config
from odin.core.context import run_ctx
from odin.core.models import new_id
from odin.db import repo

log = logging.getLogger("odin.evals.suite")
CONFIGS = ROOT / "eval" / "configs"
REPORTS = ROOT / "reports"
DEFAULT = ["offline", "vulnerable", "odin.security"]     # no paid model calls
_busy = threading.Lock()                                 # ponytail: one suite per process (RAM), queue if needed


class SuiteJob(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str


def configs() -> list[dict]:
    allowed = set((odin_config().get("evals") or {}).get("suite_configs") or DEFAULT)
    return [{"name": p.stem, "default": p.stem in allowed} for p in sorted(CONFIGS.glob("*.json"))
            if "example" not in p.stem]


def start(company_id: str, name: str, *, allow_live: bool = False) -> dict:
    known = {c["name"]: c for c in configs()}
    if name not in known:
        raise ValueError(f"unknown suite config '{name}'")
    if not known[name]["default"] and not allow_live:
        raise ValueError(f"'{name}' makes live/paid product calls; pass allow_live=true to run it")
    if not _busy.acquire(blocking=False):
        raise RuntimeError("a golden suite is already running")
    job = {"id": new_id("suite"), "config": name, "status": "running", "started_at": datetime.utcnow().isoformat()}
    _save(company_id, job)
    threading.Thread(target=_run, args=(company_id, name, job), daemon=True, name="odin-suite").start()
    return job


def _save(company_id: str, job: dict) -> None:
    with run_ctx(company_id, scenario_id=None):
        repo.put("eval_suite", SuiteJob(**job), status=job["status"])


def get(company_id: str, job_id: str) -> dict | None:
    with run_ctx(company_id, scenario_id=None):
        return repo.get("eval_suite", job_id)


def _run(company_id: str, name: str, job: dict) -> None:
    from ragnarok.__main__ import adapter_for
    from ragnarok.config import RunConfig
    from ragnarok.datasets import load_dataset
    from ragnarok.reporting import write_report
    from ragnarok.runner import run
    try:
        path = (CONFIGS / f"{name}.json").resolve()
        config = RunConfig.model_validate_json(path.read_text(encoding="utf-8"))
        if config.odin:   # product probes run inside the caller's tenant, never a hard-coded company
            config = config.model_copy(update={"odin": config.odin.model_copy(update={"company_id": company_id})})
        dataset = load_dataset(path.parent / config.dataset)
        report = asyncio.run(run(config, dataset, adapter_for(config, path, dataset)))
        out = REPORTS / f"{job['id']}.json"
        write_report(report, out)
        job.update(status="passed" if report.exit_code == 0 else "failed", exit_code=report.exit_code,
                   counts=report.counts, report_path=str(out.relative_to(ROOT)), dataset_id=report.dataset_id,
                   synthetic=report.synthetic, latency=report.latency, security_findings=report.security_findings,
                   cases=[{"case_id": c.case_id, "kind": c.kind,
                           "checks": [{k: ch.model_dump().get(k) for k in ("name", "status", "score", "threshold",
                                                                         "reason", "category", "severity",
                                                                         "required", "method")}
                                      for ch in c.checks]} for c in report.cases])
    except Exception as e:   # noqa: BLE001
        log.exception("golden suite %s failed", name)
        job.update(status="error", error=f"{type(e).__name__}: {e}"[:500])
    finally:
        job["finished_at"] = datetime.utcnow().isoformat()
        _busy.release()
    _save(company_id, job)
