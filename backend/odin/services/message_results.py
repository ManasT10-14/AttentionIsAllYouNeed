"""Public results captured with messages, never model private reasoning.

Snapshots are immutable message payloads; legacy enrichment is explicitly current state.
"""
from odin.core.context import current
from odin.db import repo


def capture_result(sender: str, kind: str, cid: str | None, payload: dict) -> dict:
    result = {"source": "message_time_snapshot", "run_id": current().run_id, "sections": []}
    sections = result["sections"]

    def add(title, value):
        if value is not None and value != [] and value != {}:
            sections.append({"title": title, "value": value})

    def records(name, ids=None):
        if ids is not None:
            return [x for i in ids if (x := repo.get(name, i))]
        return repo.query(name, contract_id=cid, run_id=current().run_id) if current().run_id else []

    fids = payload.get("finding_ids") or ([payload["finding_id"]] if payload.get("finding_id") else [])
    if sender == "synth":
        rep = payload.get("result_snapshot") or repo.get("report", f"report:{cid}" if cid else "report:company")
        if rep:
            add("Executive summary", rep.get("summary"))
            add("Report quality and limitations", {k: rep.get(k) for k in ("completeness", "summary_status", "gaps", "workstreams", "quality", "recovery_note")})
            add("Financial exposure and assumptions", rep.get("total_exposure") or rep.get("exposure"))
            add("Leading risks", rep.get("leading_risks") or rep.get("risks") or rep.get("conflicts"))
            add("Next actions and approval requirements", rep.get("prioritized_actions") or rep.get("actions"))
            add("Deadlines", rep.get("timeline") or rep.get("worst_case_projection"))
            add("Clause references", rep.get("references"))
            result["report_id"] = rep["id"]
    elif sender == "thor":
        from odin.services import insights
        x = insights.extraction(cid) if cid else None
        if x:
            add("Extracted terms and supporting clauses", x.model_dump(mode="json"))
        add("Clarification answers", records("clarification", [payload["clarification_id"]]) if payload.get("clarification_id") else records("clarification"))
    elif sender == "norns":
        from odin.services import insights
        add("Timeline, exposure and calculation basis", [t.model_dump(mode="json") for t in insights.timelines() if not cid or t.contract_id == cid])
    elif sender == "loki":
        add("Risk claims, scenarios and evidence", records("finding", fids) if fids else records("finding"))
        add("Clarification questions", records("clarification"))
    elif sender == "heimdall":
        add("Verification verdicts and rationale", payload.get("verification_results") or records("verification"))
        add("Event mapping and evidence", records("event"))
        add("Violations requiring review", records("violation"))
    elif sender == "tyr":
        rulings = records("ruling")
        if fids:
            rulings = [r for r in rulings if r.get("finding_id") in fids]
        add("Rulings and severity decisions", rulings)
        add("Drafted actions and approvals", records("action", payload["action_ids"]) if "action_ids" in payload else records("action"))
        add("Affected findings", records("finding", fids))
    elif sender == "odin":
        from odin.services import runs
        add("Work plan, evidence and completion gaps", [w.model_dump(mode="json") for w in runs.plan(current().run_id)])
    return result
