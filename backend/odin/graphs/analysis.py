"""Main analysis graph (plan §2.1):
  odin.plan ─Send per contract→ extract (Thor+Norns, parallel) → gate
            ─Send per contract→ review workstreams (Loki⇄Thor, Loki⇄Heimdall, Tyr)  ┐ all parallel
            ─Send───────────→ cross-contract workstream                            ┘
  → synth (parallel reports) → odin.final
Cross-contract only needs extractions, so it no longer waits for every per-contract debate to finish.
"""
from __future__ import annotations

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


def fan_extract(state: AnalysisState):
    return [Send("extract", p) for p in _payloads(state, "analysis")] or ["gate"]


def extract(payload: dict) -> dict:
    """Thor + Norns for one contract (fast phase, ~20 s)."""
    from odin.agents import norns, thor
    odin.mark_running(payload["run_id"], payload["contract_id"])
    errs = (thor.extract(payload) or {}).get("errors", [])
    errs += (norns.timeline(payload) or {}).get("errors", [])
    return {"errors": errs}


def gate(state: AnalysisState) -> dict:
    return {}


def fan_review(state: AnalysisState):
    base = {k: state.get(k) for k in ("company_id", "run_id", "scenario_id")}
    sends = [Send("workstream", p) for p in _payloads(state, "review")]
    sends.append(Send("cross", {**base, "contract_id": "cross", "mode": "analysis", "debate_round": 0}))
    return sends


def workstream(payload: dict) -> dict:
    out = contract_ws.build().invoke(payload)
    return {"ws_results": out.get("ws_results", []), "errors": out.get("errors", [])}


def cross(payload: dict) -> dict:
    out = contract_ws.build().invoke(payload)
    return {"ws_results": out.get("ws_results", []), "errors": out.get("errors", [])}


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
    g.add_node("extract", extract)
    g.add_node("gate", gate)
    g.add_node("workstream", workstream)
    g.add_node("cross", cross)
    g.add_node("synth", synth.synthesize)
    g.add_node("final", final)
    g.add_edge(START, "plan")
    g.add_conditional_edges("plan", fan_extract, ["extract", "gate"])
    g.add_edge("extract", "gate")                       # barrier: all extractions done
    g.add_conditional_edges("gate", fan_review, ["workstream", "cross"])
    g.add_edge("workstream", "synth")                   # both run in the same superstep → synth once
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
