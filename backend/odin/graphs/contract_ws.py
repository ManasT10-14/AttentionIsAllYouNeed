"""Per-contract workstream subgraph (plan §2.2):

  thor.extract → norns.timeline → loki.attack ─┬─(clarifications, round<max)→ thor.clarify → loki.revisit ─┐
                                               └──────────────────────────────────────────────────────────┴→ heimdall.verify
  heimdall.verify ─(challenged & round<max)→ loki.rebut → heimdall.verify      (debate loop, FR7.1)
                  ─(challenged, rounds spent)→ tyr.rule → tyr.actions → odin.ws_check
                  ─(no dispute)──────────────────────→ tyr.actions → odin.ws_check
Any node that hits the budget routes straight to odin.ws_check (FR7.2).
The cross-contract workstream enters at loki.cross instead of thor.
"""
from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from odin.agents import heimdall, loki, norns, odin, thor, tyr
from odin.core import budget as budget_mod
from odin.core.config import limits
from odin.db import repo
from odin.graphs.state import WSState


def _stop(state: WSState) -> bool:
    return bool(state.get("budget_hit")) or budget_mod.for_run(state.get("run_id")).exhausted() is not None


def route_start(state: WSState) -> str:
    odin.mark_running(state["run_id"], state["contract_id"])
    if state["contract_id"] == "cross":
        return "loki_cross"
    if state.get("mode") == "review":       # analysis graph already ran Thor + Norns in the extract phase
        return "loki_attack"
    return "norns" if state.get("mode") == "update" else "thor_extract"


def after(next_node: str):
    def r(state: WSState) -> str:
        return "odin_check" if _stop(state) else next_node
    return r


def after_attack(state: WSState) -> str:
    if _stop(state):
        return "odin_check"
    from odin.core.context import run_ctx
    with run_ctx(state["company_id"], run_id=state["run_id"], scenario_id=state.get("scenario_id")):
        pending = repo.query("clarification", contract_id=state["contract_id"], status="open")
    return "thor_clarify" if pending and state.get("clarify_round", 0) <= limits()["max_clarify_rounds"] else "heimdall_verify"


def after_verify(state: WSState) -> str:
    if _stop(state):
        return "odin_check"
    if state.get("disputed"):
        return "loki_rebut" if state.get("debate_round", 0) < limits()["max_debate_rounds"] else "tyr_rule"
    return "tyr_actions"


@lru_cache
def build():
    g = StateGraph(WSState)
    g.add_node("thor_extract", thor.extract)
    g.add_node("norns", norns.timeline)
    g.add_node("loki_attack", loki.attack)
    g.add_node("loki_cross", loki.cross)
    g.add_node("thor_clarify", thor.clarify)
    g.add_node("loki_revisit", loki.revisit)
    g.add_node("heimdall_verify", heimdall.verify)
    g.add_node("loki_rebut", loki.rebut)
    g.add_node("tyr_rule", tyr.rule)
    g.add_node("tyr_actions", tyr.actions)
    g.add_node("odin_check", odin.ws_check)

    g.add_conditional_edges(START, route_start, ["thor_extract", "norns", "loki_cross", "loki_attack"])
    g.add_conditional_edges("thor_extract", after("norns"), ["norns", "odin_check"])
    g.add_conditional_edges("norns", after("loki_attack"), ["loki_attack", "odin_check"])
    g.add_conditional_edges("loki_attack", after_attack, ["thor_clarify", "heimdall_verify", "odin_check"])
    g.add_conditional_edges("loki_cross", after("heimdall_verify"), ["heimdall_verify", "odin_check"])
    g.add_conditional_edges("thor_clarify", after("loki_revisit"), ["loki_revisit", "odin_check"])
    g.add_conditional_edges("loki_revisit", after("heimdall_verify"), ["heimdall_verify", "odin_check"])
    g.add_conditional_edges("heimdall_verify", after_verify, ["loki_rebut", "tyr_rule", "tyr_actions", "odin_check"])
    g.add_conditional_edges("loki_rebut", after("heimdall_verify"), ["heimdall_verify", "odin_check"])
    g.add_conditional_edges("tyr_rule", after("tyr_actions"), ["tyr_actions", "odin_check"])
    g.add_edge("tyr_actions", "odin_check")
    g.add_edge("odin_check", END)
    return g.compile()
