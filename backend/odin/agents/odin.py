"""ODIN — orchestrator (FR1): work plan, delegation/tracking, completeness gate. Deterministic by design:
routing decisions must be reproducible (NFR6); the LLM work happens in the specialist agents."""
from __future__ import annotations

from odin.agents.base import agent_node, say
from odin.core import budget as budget_mod
from odin.core.config import limits
from odin.core.models import Workstream
from odin.db import repo
from odin.services import insights, runs

WS_TASKS = ["thor:extract", "norns:timeline", "loki:attack", "thor:clarify?", "heimdall:verify", "loki⇄heimdall:debate?",
            "tyr:rule?", "tyr:actions"]
CROSS_TASKS = ["loki:cross", "heimdall:verify", "tyr:rule?", "tyr:actions"]


@agent_node("odin")
def plan(state: dict) -> dict:
    cids = state.get("contract_ids") or [c.contract_id for c in repo.contracts()]
    ws = [Workstream(id=f"ws:{c}", contract_id=c, tasks=WS_TASKS) for c in cids]
    ws.append(Workstream(id="ws:cross", contract_id="cross", tasks=CROSS_TASKS))
    runs.set_plan(state["run_id"], ws)
    say("odin", "all", "plan", f"Work plan: {len(cids)} contract workstreams + 1 cross-contract workstream.",
        payload={"workstreams": [w.id for w in ws]})
    return {"contract_ids": cids}


def evidence_score(contract_id: str) -> float:
    """Mean confidence of fields whose citation is verified (unverified count as 0)."""
    if contract_id == "cross":
        fs = repo.query("finding", contract_id="cross", status=["verified", "ruled"])
        cits = [c for f in fs for c in f.get("citations", [])]
        return sum(c.get("verified", False) for c in cits) / len(cits) if cits else 1.0
    x = insights.extraction(contract_id)
    if not x:
        return 0.0
    fs = insights._fields(x)
    return sum(f.confidence for f in fs if f.citation and f.citation.verified) / len(fs) if fs else 0.0


@agent_node("odin")
def ws_check(state: dict) -> dict:
    """Decide whether a workstream is complete (FR1.4, FR7.2, NFR3: never 'done' when it is not)."""
    cid = state["contract_id"]
    score = round(evidence_score(cid), 3)
    errors = state.get("errors") or []
    reasons = []
    if errors:
        reasons.append(f"{len(errors)} agent error(s): {errors[-1][:160]}")
    if state.get("budget_hit"):
        reasons.append(f"budget: {state['budget_hit']}")
    if score < limits()["evidence_threshold"]:
        reasons.append(f"evidence score {score} < threshold {limits()['evidence_threshold']}")
    open_clar = repo.query("clarification", contract_id=cid, status="open")
    if open_clar:
        reasons.append(f"{len(open_clar)} clarification(s) unanswered (loop limit)")
    unresolved = repo.query("finding", contract_id=cid, status="challenged")
    if unresolved:
        reasons.append(f"{len(unresolved)} dispute(s) unresolved")
    if cid != "cross" and not insights.extraction(cid):
        status = "failed"
    else:
        status = "partial" if reasons else "done"
    runs.update_ws(state["run_id"], f"ws:{cid}", status=status, reason="; ".join(reasons), evidence_score=score)
    say("odin", "synth", "status", f"Workstream {cid}: {status.upper()} (evidence {score})"
        + (f" — {'; '.join(reasons)}" if reasons else ""), contract_id=cid)
    return {"ws_results": [{"contract_id": cid, "status": status, "reason": "; ".join(reasons), "evidence": score}]}


def mark_running(run_id: str, contract_id: str) -> None:
    runs.update_ws(run_id, f"ws:{contract_id}", status="running")


def budget_left(run_id: str) -> str | None:
    return budget_mod.for_run(run_id).exhausted()
