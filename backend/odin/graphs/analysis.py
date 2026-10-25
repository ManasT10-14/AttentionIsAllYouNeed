"""Main analysis graph (plan §2.1):
  odin.plan ─Send per contract→ pipeline: Thor+Norns → review workstream (Loki⇄Thor, Loki⇄Heimdall, Tyr)
            │                    → that contract's report                                  ┐ all parallel,
            ─Send───────────────→ cross-contract workstream (waits only for all extractions) ┘ no barriers
  → company report → odin.final
"""
from __future__ import annotations

import threading
from functools import lru_cache

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from odin.agents import odin, synth
from odin.db import repo
from odin.graphs import contract_ws
from odin.graphs.checkpoint import checkpointer
from odin.graphs.state import AnalysisState
from odin.services import runs


def _payloads(state: AnalysisState, mode: str) -> list[dict]:
    from odin.core.context import run_ctx
    base = {k: state.get(k) for k in ("company_id", "run_id", "scenario_id")}
    out = []
    with run_ctx(state["company_id"]):
        for cid in state["contract_ids"]:
            out.append({**base, "contract_id": cid, "version": repo.contract(cid).current_version, "mode": mode,
                        "force": state.get("force", False), "clarify_round": 0, "debate_round": 0})
    return out


# run_id -> {contract_id: Event set when that contract's Thor+Norns finished}; lets cross start once all
# extractions exist without holding back any per-contract pipeline. Absent after a resume -> cross doesn't wait.
_extracted: dict[str, dict[str, threading.Event]] = {}


def fan_out(state: AnalysisState):
    """One independent pipeline per contract (extract → Loki → Heimdall → Tyr → report) + cross."""
    base = {k: state.get(k) for k in ("company_id", "run_id", "scenario_id")}
    pays = _payloads(state, "review")
    _extracted[state["run_id"]] = {p["contract_id"]: threading.Event() for p in pays}
    return [Send("pipeline", p) for p in pays] + [Send("cross", {**base, "contract_id": "cross", "mode": "analysis",
                                                                  "debate_round": 0})]


def extract(payload: dict) -> dict:
    """Thor + Norns for one contract (fast phase, ~20 s)."""
    from odin.agents import norns, thor
    odin.mark_running(payload["run_id"], payload["contract_id"])
    errs = (thor.extract(payload) or {}).get("errors", [])
    errs += (norns.timeline(payload) or {}).get("errors", [])
    return {"errors": errs}


def pipeline(payload: dict) -> dict:
    """Everything for one contract, starting Loki the moment its own Thor finishes and writing its report
    as soon as its workstream is done (no cross-contract barriers)."""
    ev = _extracted.get(payload["run_id"], {}).get(payload["contract_id"])
    try:
        ext = extract(payload)
    finally:
        if ev:
            ev.set()
    out = contract_ws.build().invoke(payload)
    res = out.get("ws_results", [])
    synth.synthesize_contract({**{k: payload.get(k) for k in ("company_id", "run_id", "scenario_id", "contract_id")},
                               "ws": res[0] if res else None})
    return {"ws_results": res, "errors": ext["errors"] + out.get("errors", [])}


def cross(payload: dict) -> dict:
    for ev in list(_extracted.get(payload["run_id"], {}).values()):
        ev.wait(timeout=900)        # cross-contract review needs every extraction
    out = contract_ws.build().invoke(payload)
    return {"ws_results": out.get("ws_results", []), "errors": out.get("errors", [])}


def company_report(state: AnalysisState) -> dict:
    _extracted.pop(state["run_id"], None)
    return synth.synthesize_company(state)


def final(state: AnalysisState) -> dict:
    res = state.get("ws_results", [])
    status = "done" if res and all(r["status"] == "done" for r in res) else "partial"
    if res and all(r["status"] == "failed" for r in res):
        status = "failed"
    return {"final_status": status}


@lru_cache
def build():
    g = StateGraph(AnalysisState)
    g.add_node("plan", odin.plan)
    g.add_node("pipeline", pipeline)
    g.add_node("cross", cross)
    g.add_node("synth", company_report)
    g.add_node("final", final)
    g.add_edge(START, "plan")
    g.add_conditional_edges("plan", fan_out, ["pipeline", "cross"])
    g.add_edge("pipeline", "synth")                     # company report waits for every pipeline + cross
    g.add_edge("cross", "synth")
    g.add_edge("synth", "final")
    g.add_edge("final", END)
    return g.compile(checkpointer=checkpointer())


def run(company_id: str, contract_ids: list[str] | None = None, force: bool = False, background: bool = True) -> str:
    def go(run_id: str) -> str:
        out = build().invoke({"company_id": company_id, "run_id": run_id, "contract_ids": contract_ids or [],
                              "force": force}, config=runs.graph_config(run_id, "analysis", company_id=company_id))
        return out.get("final_status", "partial")
    return runs.start(company_id, "analysis", go, background=background)
