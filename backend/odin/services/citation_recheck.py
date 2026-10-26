"""Recheck saved evidence without generating claims or changing source contracts."""
from pydantic import ValidationError
from sqlalchemy import select
from odin.core.citations import verify
from odin.core.models import Citation, new_id
from odin.db.session import db
from odin.db.tables import Record
from odin.services.bundle import save

KINDS = {"extraction", "finding", "verification", "ruling", "action", "alert", "report", "dependency"}


def recheck(company_id: str) -> dict:
    counts = {"checked": 0, "repaired": 0, "verified": 0, "unverified": 0}
    def walk(value, citation=False):
        if isinstance(value, list):
            return [walk(v, citation) for v in value]
        if not isinstance(value, dict):
            return value
        if citation and {"contract_id", "clause_number", "quote"} <= value.keys():
            try:
                checked = verify(Citation.model_validate(value))
            except ValidationError:
                return value
            counts["checked"] += 1
            counts["verified" if checked.verified else "unverified"] += 1
            if checked.verified and (not value.get("verified") or checked.quote != value["quote"]):
                counts["repaired"] += 1
            return {**value, **checked.model_dump(mode="json")}
        out = {k: walk(v, k in ("citation", "citations", "affected_clauses")) for k, v in value.items()}
        if out.get("status") == "unverified" and isinstance(out.get("citation"), dict) and out["citation"].get("verified"):
            out["status"] = "found"
        return out
    with db() as session:
        rows = session.scalars(select(Record).where(Record.company_id == company_id,
                Record.kind.in_(KINDS), Record.scenario_id.is_(None))).all()
        for row in rows:
            row.data = walk(row.data)
    save("citation_recheck", new_id("recheck"), counts)
    return counts
