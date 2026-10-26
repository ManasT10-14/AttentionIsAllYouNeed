"""Import the organiser bundle without touching the separate original corpus."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

from pydantic import BaseModel

from odin.core.config import ROOT
from odin.core.context import run_ctx
from odin.db import repo
from odin.db.session import db
from odin.db.tables import Company
from odin.ingest.pack import DocInfo, detect_relations
from odin.ingest.service import ingest_company_context, ingest_contract

PACK = ROOT / "corpus" / "odin_dev_pack"


def save(kind: str, identity: str, data: dict):
    # repo.put accepts a model; retain a flat payload for existing agent readers.
    class Document(BaseModel):
        model_config = {"extra": "allow"}
    return repo.put(kind, Document(**data), rid=identity)


def inventory(root: Path = PACK) -> list[dict]:
    """Validate every manifest item, PDF twin and clock before starting an import."""
    bundle = (root / "bundle").resolve()
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8-sig"))
    paths = {"README.md", "docs/format_spec.md", "clock.json", "bundle/manifest.json"}
    for item in manifest["files"]:
        p = (bundle / item["path"]).resolve()
        if not p.is_relative_to(bundle):
            raise ValueError("Bundle manifest contains a path outside the bundle")
        paths.add("bundle/" + item["path"])
        if item["path"].startswith("contracts/") and p.suffix == ".txt":
            paths.add("bundle/" + str(Path(item["path"]).with_suffix(".pdf")).replace("\\", "/"))
    out = []
    for rel in sorted(paths):
        content = (root / rel).read_bytes()
        out.append({"path": rel, "size": len(content), "sha256": hashlib.sha256(content).hexdigest()})
    clock = json.loads((root / "clock.json").read_text(encoding="utf-8-sig"))
    from datetime import date
    dates = [date.fromisoformat(x) for x in [clock["start_date"], *clock["checkpoints"]]]
    if dates != sorted(set(dates)):
        raise ValueError("Clock checkpoints must increase after the start date")
    return out


def csv_rows(name: str, root: Path = PACK) -> list[dict]:
    return list(csv.DictReader(io.StringIO((root / "bundle" / "data" / name).read_text(encoding="utf-8-sig"))))


def import_bundle(company_id: str, *, analyze: bool = False, root: Path = PACK) -> dict:
    files = inventory(root)
    manifest = json.loads((root / "bundle/manifest.json").read_text(encoding="utf-8-sig"))
    with run_ctx(company_id, agent="system"):
        existing = repo.get("bundle", "official")
        if not existing and repo.contracts():
            raise ValueError("Import the official pack into an empty workspace to keep corpora separate")
        if not existing:
            save("bundle", "official", {"status": "importing", "files": files})
        ingest_company_context(company_id, "context.txt", (root / "bundle/company/context.txt").read_bytes())
        results, docs, warnings = [], [], []
        for item in manifest["files"]:
            path = root / "bundle" / item["path"]
            if not item["path"].startswith("contracts/") or path.suffix != ".txt":
                continue
            r = ingest_contract(company_id, path.name, path.read_bytes(), twin_pdf=path.with_suffix(".pdf").read_bytes(),
                                doc_id=path.stem, title=item["title"])
            results.append(asdict(r))
            warnings.extend(f"{path.stem}: {w}" for w in r.warnings if not r.duplicate)
            c = repo.contract(path.stem)
            v = repo.version_row(path.stem, c.current_version)
            docs.append(DocInfo(path.stem, v.text, c.title, c.meta.get("external_id"),
                                __import__('datetime').date.fromisoformat(c.meta["effective_date"]) if c.meta.get("effective_date") else None,
                                [SimpleNamespace(**{k: getattr(cl, k) for k in ("number", "ref", "char_start", "char_end", "text")})
                                 for cl in repo.clauses(path.stem)]))
        relations, overrides, rw = detect_relations(docs)
        warnings.extend(rw)
        with db() as session:
            for doc in docs:
                from odin.db.tables import Contract
                from sqlalchemy import select
                c = session.scalar(select(Contract).where(Contract.company_id == company_id, Contract.contract_id == doc.doc_id))
                c.meta = {**c.meta, "relations": [r for r in relations if doc.doc_id in (r["from_doc"], r["to_doc"])]}
        for i, rel in enumerate(relations):
            save("doc_relation", f"official:relation:{i}", rel)
        for i, override in enumerate(overrides):
            save("clause_override", f"official:override:{i}", override)
        ledger = csv_rows("payments_ledger.csv", root)
        external_ids = {d.external_id: d.doc_id for d in docs if d.external_id}
        for i, row in enumerate(ledger):
            row["amount"] = float(row["amount"])
            row["currency"] = "USD"
            row["contract_id"] = next((cid for ext, cid in external_ids.items() if ext in row["reference"]), "")
            save("ledger", f"official:ledger:{i}", row)
        hol = csv_rows("holidays.csv", root)
        for i, row in enumerate(hol):
            save("holiday", f"official:holiday:{i}", row)
        clock = json.loads((root / "clock.json").read_text(encoding="utf-8-sig"))
        if not repo.get("simulation", "official:simulation"):
            from datetime import date
            with db() as s:
                s.get(Company, company_id).sim_now = date.fromisoformat(clock["start_date"])
            save("simulation", "official:simulation", {**clock, "drops_loaded": []})
            from odin.core import bus
            bus.publish(company_id, "clock", {"sim_now": clock["start_date"]})
        counts = {"documents": len(docs), "clauses": sum(len(d.clauses) for d in docs),
                  "relations": len(relations), "ledger": len(ledger), "holidays": len(hol)}
        result = {"counts": counts, "results": results, "relations": relations, "overrides": overrides,
                  "warnings": warnings, "files": files, "clock": clock}
        save("bundle", "official", result)
        if analyze:
            from odin.graphs import analysis
            result["run_id"] = analysis.run(company_id, [d.doc_id for d in docs])
        return result


def ledger_as_of(now):
    """Rows are dated source facts, not inferred contractual due dates."""
    rows = []
    for item in repo.query("ledger"):
        if item["date"] > now.isoformat():
            continue
        row = dict(item)
        status = row.get("status", "").lower()
        row["late"] = "late" in status or "overdue" in status
        row["unpaid"] = any(x in status for x in ("unpaid", "missed", "overdue", "pending"))
        rows.append(row)
    return rows
