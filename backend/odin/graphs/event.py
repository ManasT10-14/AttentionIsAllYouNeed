"""Event graph (plan §2.3) — one run per incoming event:
  heimdall.map_event ─noise→ END
                     └→ norns.recompute → loki.reassess → heimdall.verify ⇄ loki.rebut → (tyr.rule) → tyr.decide_event
"""
from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from odin.agents import heimdall, loki, tyr
from odin.agents.base import agent_node, say
from odin.core import budget as budget_mod
from odin.core.config import limits
from odin.graphs.checkpoint import checkpointer
from odin.graphs.state import EventState
from odin.services import insights, runs


@agent_node("norns")
def recompute(state: EventState) -> dict:
    exp = insights.exposure_summary()
    per = {c["contract_id"]: c for c in exp["contracts"]}
    lines = [f"{cid}: worst case {per[cid]['currency']} {per[cid]['worst_case']:,.0f}"
             for cid in state.get("contract_ids", []) if cid in per]
    say("norns", "loki", "timeline", "Recomputed after event — " + "; ".join(lines),
        payload={cid: per[cid] for cid in state.get("contract_ids", []) if cid in per})
    return {}


def _stop(s):
    return bool(s.get("budget_hit")) or budget_mod.for_run(s.get("run_id")).exhausted() is not None


def after_map(s: EventState) -> str:
    return END if s.get("noise") or _stop(s) or s.get("errors") else "recompute"


def after_verify(s: EventState) -> str:
    if _stop(s):
        return "decide"
    if s.get("disputed"):
        return "rebut" if s.get("debate_round", 0) < limits()["max_debate_rounds"] else "rule"
    return "decide"


@lru_cache
def build():
    g = StateGraph(EventState)
    g.add_node("map", heimdall.map_event)
    g.add_node("recompute", recompute)
    g.add_node("reassess", loki.reassess_event)
    g.add_node("verify", heimdall.verify)
    g.add_node("rebut", loki.rebut)
    g.add_node("rule", tyr.rule)
    g.add_node("decide", tyr.decide_event)
    g.add_edge(START, "map")
    g.add_conditional_edges("map", after_map, ["recompute", END])
    g.add_edge("recompute", "reassess")
    g.add_edge("reassess", "verify")
    g.add_conditional_edges("verify", after_verify, ["rebut", "rule", "decide"])
    g.add_edge("rebut", "verify")
    g.add_edge("rule", "decide")
    g.add_edge("decide", END)
    return g.compile(checkpointer=checkpointer())


def run(company_id: str, event_id: str, scenario_id: str | None = None, background: bool = True) -> str:
    def go(run_id: str) -> str:
        out = build().invoke({"company_id": company_id, "run_id": run_id, "scenario_id": scenario_id,
                              "event_id": event_id, "debate_round": 0, "finding_ids": []},
                             config=runs.graph_config(run_id, "whatif" if scenario_id else "event",
                                                      company_id=company_id, event_id=event_id))
        if out.get("noise"):
            return "done"
        return "partial" if out.get("errors") or out.get("budget_hit") else "done"
    return runs.start(company_id, "whatif" if scenario_id else "event", go, scenario_id=scenario_id,
                      background=background)
