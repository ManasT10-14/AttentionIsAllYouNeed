"""Contract-version update graph (plan §6):
  diff → thor.patch (changed clauses only) → invalidate dependants → workstream from Norns with focus
  → tyr.amend (redlines) → synth
"""
from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from odin.agents import synth, tyr
from odin.agents.base import agent_node, j, prompt, say, tool
from odin.agents.thor import merge
from odin.core.models import ContractExtraction
from odin.db import repo
from odin.graphs import contract_ws
from odin.graphs.checkpoint import checkpointer
from odin.graphs.state import UpdateState
from odin.ingest.diff import diff_versions
from odin.llm.call import structured
from odin.services import insights, runs


@agent_node("odin")
def diff(state: UpdateState) -> dict:
    d = diff_versions(state["contract_id"], state["from_version"], state["to_version"])
    changes = [c.__dict__ for c in d.changes]
    repo.put("diff", _D(id=f"diff:{state['contract_id']}:{state['from_version']}-{state['to_version']}", **d.as_dict()),
             contract_id=state["contract_id"])
    summary = {k: sum(1 for c in d.changes if c.change == k) for k in ("added", "removed", "modified", "renumbered")}
    say("odin", "thor", "plan", f"{state['contract_id']} v{state['from_version']}→v{state['to_version']}: "
        + ", ".join(f"{v} {k}" for k, v in summary.items() if v) + " — targeted re-extraction only.",
        payload=summary, contract_id=state["contract_id"])
    return {"changes": changes, "touched": [c.number for c in d.changes if c.change != "removed"]}


class _D(dict):
    def model_dump(self, mode="json"):
        return dict(self)


class ThorPatch(BaseModel):
    updated_fields: ContractExtraction


@agent_node("thor")
def patch(state: UpdateState) -> dict:
    cid, v_from, v_to = state["contract_id"], state["from_version"], state["to_version"]
    old = insights.extraction(cid, v_from) or ContractExtraction()
    changes = state.get("changes") or []
    removed = {c["number"] for c in changes if c["change"] == "removed"} | \
              {c["old_number"] for c in changes if c["change"] == "renumbered" and c.get("old_number")}
    touched = set(state.get("touched") or [])
    if touched:
        rows = repo.clauses(cid, v_to, current_only=False, numbers=sorted(touched))
        user = (f"Previous extraction (v{v_from}):\n{j(old.model_dump(mode='json'))[:15000]}\n\n"
                f"<document contract_id=\"{cid}\">\nChanged/new clauses in v{v_to}:\n"
                + "\n".join(f"[clause {r.number}]\n{r.text}" for r in rows) + "\n</document>\n\n"
                "Re-extract ONLY fields governed by these clauses.")
        upd = structured("thor", ThorPatch, prompt("thor"), user, meta={"contract_id": cid, "version": v_to}).updated_fields
    else:
        upd = ContractExtraction()
    new = merge(old, upd, touched | removed)
    for f in insights._fields(new):     # fields citing removed clauses are now missing
        if f.citation and f.citation.clause_number in removed:
            f.status, f.confidence, f.note = "missing", 0.0, f"clause {f.citation.clause_number} removed in v{v_to}"
        if f.citation:
            f.citation.version = None   # re-verify against the current version
    tool("save_extraction", {"contract_id": cid, "version": v_to, "extraction": new.model_dump(mode="json")})
    say("thor", "loki", "extract", f"{cid} v{v_to}: re-extracted {len(touched)} changed clause(s); "
        f"{len(removed)} removed.", contract_id=cid)
    return {}


@agent_node("odin")
def invalidate(state: UpdateState) -> dict:
    cid = state["contract_id"]
    hit = set(state.get("touched") or []) | {c["number"] for c in state.get("changes") or []}
    n = 0
    for kind in ("finding", "action"):
        for r in repo.query(kind, contract_id=cid):
            if r.get("status") in ("superseded", "sent", "applied", "withdrawn"):
                continue
            if any(c.get("clause_number") in hit for c in r.get("citations", [])):
                repo.set_status(r["id"], "superseded")
                n += 1
    say("odin", "loki", "plan", f"{cid}: {n} findings/actions tied to changed clauses superseded; re-reviewing.",
        contract_id=cid)
    return {}


def rerun(state: UpdateState) -> dict:
    out = contract_ws.build().invoke({**{k: state.get(k) for k in ("company_id", "run_id", "scenario_id")},
                                      "contract_id": state["contract_id"], "version": state["to_version"],
                                      "mode": "update", "focus_clauses": state.get("touched") or None,
                                      "clarify_round": 0, "debate_round": 0})
    return {"ws_results": out.get("ws_results", []), "errors": out.get("errors", [])}


@agent_node("synth")
def report(state: UpdateState) -> dict:
    return synth.synthesize.__wrapped__({**state, "contract_ids": [state["contract_id"]]})  # type: ignore[attr-defined]


@lru_cache
def build():
    g = StateGraph(UpdateState)
    g.add_node("diff", diff)
    g.add_node("patch", patch)
    g.add_node("invalidate", invalidate)
    g.add_node("rerun", rerun)
    g.add_node("amend", tyr.amend)
    g.add_node("report", report)
    g.add_edge(START, "diff")
    g.add_edge("diff", "patch")
    g.add_edge("patch", "invalidate")
    g.add_edge("invalidate", "rerun")
    g.add_edge("rerun", "amend")
    g.add_edge("amend", "report")
    g.add_edge("report", END)
    return g.compile(checkpointer=checkpointer())


def run(company_id: str, contract_id: str, from_version: int, to_version: int, background: bool = True) -> str:
    def go(run_id: str) -> str:
        out = build().invoke({"company_id": company_id, "run_id": run_id, "contract_id": contract_id,
                              "from_version": from_version, "to_version": to_version},
                             config=runs.graph_config(run_id, "update", company_id=company_id, contract_id=contract_id))
        res = out.get("ws_results", [])
        return "done" if res and all(r["status"] == "done" for r in res) and not out.get("errors") else "partial"
    return runs.start(company_id, "update", go, background=background)
