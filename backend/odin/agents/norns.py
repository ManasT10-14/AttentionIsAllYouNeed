"""NORNS — timeline (FR3). Deterministic engine + LLM only to resolve relative due rules."""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel

from odin.agents.base import agent_node, j, prompt, say, tool
from odin.db import repo
from odin.llm.call import structured
from odin.services import insights


class DueResolution(BaseModel):
    ref: str
    first_due: Optional[date] = None
    reasoning: str


class DueResolutions(BaseModel):
    items: list[DueResolution] = []


@agent_node("norns")
def timeline(state: dict) -> dict:
    cid = state["contract_id"]
    x = insights.extraction(cid)
    if not x:
        say("norns", "odin", "timeline", f"{cid}: no extraction — timeline skipped.", contract_id=cid)
        return {"errors": [f"norns: {cid} has no extraction"]}
    c = repo.contract(cid)
    eff = (x.term.effective_date if x.term else None) or c.meta.get("effective_date")

    todo = {f"payments[{i}]": p.due_rule for i, p in enumerate(x.payments)
            if p.amount and not p.first_due and p.due_rule}
    todo.update({f"obligations[{i}]": o.due_rule for i, o in enumerate(x.obligations)
                 if not o.due_date and o.due_rule and not o.recurring})
    if todo and eff:
        res = structured("norns", DueResolutions, prompt("norns"),
                         f"Effective date: {eff}\nRules:\n{j(todo)}", meta={"contract_id": cid})
        changed = 0
        for r in res.items:
            if not r.first_due or r.ref not in todo:
                continue
            kind, idx = r.ref.split("[")
            item = getattr(x, kind)[int(idx.rstrip("]"))]
            if kind == "payments":
                item.first_due = r.first_due
            else:
                item.due_date = r.first_due
            item.note = (item.note + f" | Norns derived date: {r.reasoning}").strip(" |")
            changed += 1
        if changed:
            tool("save_extraction", {"contract_id": cid, "version": c.current_version,
                                     "extraction": x.model_dump(mode="json")})

    tl = tool("compute_timeline", {"contract_id": cid})["contracts"]
    if not tl:
        return {}
    t = tl[0]
    exp = t["exposure"]
    nxt = next((e for e in t["entries"] if e["status"] in ("due", "upcoming", "missed")), None)
    say("norns", "loki", "timeline",
        f"{cid}: term ends {t['term_end']}, notice deadline {t['notice_deadline']}; expected exposure "
        f"{exp['currency']} {exp['expected']:,.0f}, worst case {exp['worst_case']:,.0f}."
        + (f" Next: {nxt['title']} on {nxt['date']} ({nxt['status']})." if nxt else ""),
        payload={"exposure": exp, "entries": len(t["entries"])}, contract_id=cid)
    return {}
