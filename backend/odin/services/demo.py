"""Demo mode: seed sample contracts + company context, and replay a scripted email feed (Gmail backup)."""
from __future__ import annotations

import threading
import time
from datetime import date

from odin.core.config import ROOT
from odin.db.session import db
from odin.db.tables import Company
from odin.graphs import analysis as analysis_graph
from odin.ingest.service import ingest_company_context, ingest_contract
from odin.services import events

SAMPLES = ROOT / "samples"
DEMO_START = date(2026, 10, 20)


def seed(company_id: str, analyze: bool = True) -> dict:
    ctx = SAMPLES / "company_context.md"
    if ctx.exists():
        ingest_company_context(company_id, ctx.name, ctx.read_bytes())
    with db() as s:
        s.get(Company, company_id).sim_now = DEMO_START
    results, new = [], []
    for f in sorted((SAMPLES / "contracts").glob("*")):
        if f.suffix.lower() not in (".pdf", ".docx"):
            continue
        try:
            r = ingest_contract(company_id, f.name, f.read_bytes())
            results.append({"file": f.name, **r.__dict__})
            if not r.duplicate:
                new.append(r.contract_id)
        except Exception as e:   # noqa: BLE001
            results.append({"file": f.name, "error": str(e)})
    run_id = analysis_graph.run(company_id, new) if analyze and new else None
    return {"sim_now": DEMO_START, "results": results, "run_id": run_id}


def scripted_emails() -> list[tuple[str, str]]:
    out = []
    for f in sorted((SAMPLES / "emails").glob("*.txt")):
        text = f.read_text(encoding="utf-8")
        head, _, body = text.partition("\n\n")
        subject = head.split(":", 1)[1].strip() if head.lower().startswith("subject:") else head.strip()
        out.append((subject, body))
    return out


def play(company_id: str, delay_seconds: float = 20) -> dict:
    mails = scripted_emails()

    def go():
        for subject, body in mails:
            events.receive(company_id, subject=subject, body=body, sender="demo@judges.example", method="demo",
                           background=False)
            time.sleep(delay_seconds)
    threading.Thread(target=go, daemon=True, name="demo-play").start()
    return {"queued": len(mails), "delay_seconds": delay_seconds, "subjects": [m[0] for m in mails]}
