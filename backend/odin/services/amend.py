"""Apply an approved amendment: redlines → new DOCX version → re-ingest → update graph (closes the loop)."""
from __future__ import annotations

import io

from odin.core.context import current
from odin.db import repo


def build_docx(contract_id: str, redlines: dict[str, str]) -> bytes:
    from docx import Document

    c = repo.contract(contract_id)
    meta = dict(c.meta)
    doc = Document()
    cover = [("CONTRACT TITLE", meta.get("title") or c.title), ("CONTRACT ID", contract_id),
             ("CONTRACT TYPE", meta.get("type", "other")), ("EFFECTIVE DATE", meta.get("effective_date") or "")]
    for i, p in enumerate(meta.get("parties", [])):
        alias = f' (the "{p["alias"]}")' if p.get("alias") else ""
        cover.append((f"PARTY {chr(65 + i)}", p["name"] + alias))
    cover += [("GOVERNING LAW", meta.get("governing_law", "")), ("VERSION", str(c.current_version + 1)),
              ("SUPERSEDES", f"{contract_id} v{c.current_version}")]
    for k, v in cover:
        doc.add_paragraph(f"{k}: {v}")
    doc.add_paragraph("")
    for cl in repo.clauses(contract_id):
        text = redlines.get(cl.number, cl.text)
        if not text.lstrip().startswith(cl.number.split("#")[0]):
            text = f"{cl.number} {text}"
        for line in text.split("\n"):
            doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def apply(action_id: str) -> dict:
    from odin.graphs import update as update_graph
    from odin.ingest.service import ingest_contract

    a = repo.get("action", action_id)
    if not a or a.get("kind") != "amendment" or not a.get("redlines"):
        raise ValueError("not an amendment with redlines")
    red = {r["clause_number"]: r["after"] for r in a["redlines"]}
    company_id = current().company_id
    content = build_docx(a["contract_id"], red)
    res = ingest_contract(company_id, f"{a['contract_id']}_amended.docx", content)
    repo.set_status(action_id, "applied", applied_version=res.version)
    run_id = update_graph.run(company_id, res.contract_id, res.previous_version, res.version) if res.is_update else None
    return {"contract_id": res.contract_id, "version": res.version, "run_id": run_id, "warnings": res.warnings}
