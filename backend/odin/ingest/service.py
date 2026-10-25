"""Upload → files on disk → parsed version → clause rows (+embeddings). Detects new vs updated contracts."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select, update

from odin.core.config import DATA_DIR
from odin.core.hooks import HOOKS
from odin.core.models import CompanyContext, new_id
from odin.db.session import db
from odin.db.tables import ClauseRow, Company, Contract, ContractVersion
from odin.ingest.parse import docx_to_pdf, parse_money, parse_pdf, text_to_pdf
from odin.retrieval.hybrid import chunk_header, embed_passages


@dataclass
class IngestResult:
    contract_id: str
    version: int
    is_update: bool
    previous_version: int | None
    clause_count: int
    warnings: list[str]
    duplicate: bool = False


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)[:80]


def ingest_contract(company_id: str, filename: str, content: bytes) -> IngestResult:
    ext = Path(filename).suffix.lower()
    if ext not in (".pdf", ".docx", ".txt", ".md"):
        raise ValueError(f"Unsupported file type {ext} — use PDF or DOCX.")
    sha = hashlib.sha256(content).hexdigest()
    stage = DATA_DIR / company_id / "_staging" / sha[:16]
    stage.mkdir(parents=True, exist_ok=True)
    src = stage / f"original{ext}"
    src.write_bytes(content)
    pdf = stage / "document.pdf"
    warnings: list[str] = []
    if ext == ".pdf":
        pdf.write_bytes(content)
    elif ext == ".docx":
        warnings += docx_to_pdf(src, pdf)
    else:
        text_to_pdf(content.decode("utf-8", errors="replace"), pdf)

    doc = parse_pdf(pdf, fallback_id=_safe(Path(filename).stem).upper())
    HOOKS.on_ingest(doc.text, {"company_id": company_id, "filename": filename})
    warnings += doc.warnings
    cover = doc.cover
    cid = cover.contract_id.strip()

    with db() as s:
        existing = s.scalar(select(Contract).where(Contract.company_id == company_id, Contract.contract_id == cid))
        if existing:
            last = s.scalar(select(ContractVersion).where(ContractVersion.company_id == company_id,
                                                          ContractVersion.contract_id == cid,
                                                          ContractVersion.version == existing.current_version))
            if last and last.sha256 == sha:
                return IngestResult(cid, existing.current_version, False, None, 0, ["Identical file already ingested."],
                                    duplicate=True)
            prev = existing.current_version
            version = max(prev + 1, cover.version or 0)
        else:
            prev = None
            version = cover.version or 1

    final = DATA_DIR / company_id / _safe(cid) / f"v{version}"
    final.mkdir(parents=True, exist_ok=True)
    (final / src.name).write_bytes(src.read_bytes())
    (final / "document.pdf").write_bytes(pdf.read_bytes())

    headers = [chunk_header(cid, version, c.number, c.heading) + "\n" + c.text[:1800] for c in doc.clauses]
    vectors = embed_passages(headers) if headers else []

    cover_json = cover.model_dump(mode="json")
    cover_json["version"] = version
    with db() as s:
        if prev is None:
            s.add(Contract(id=new_id("ctr"), company_id=company_id, contract_id=cid, title=cover.title or cid,
                           type=cover.type, current_version=version, meta=cover_json, status="ingested"))
        else:
            s.execute(update(Contract).where(Contract.company_id == company_id, Contract.contract_id == cid)
                      .values(current_version=version, meta=cover_json, title=cover.title or cid,
                              type=cover.type, status="updated"))
            s.execute(update(ClauseRow).where(ClauseRow.company_id == company_id, ClauseRow.contract_id == cid)
                      .values(is_current=False))
        s.add(ContractVersion(id=new_id("ver"), company_id=company_id, contract_id=cid, version=version,
                              file_path=str(final / src.name), pdf_path=str(final / "document.pdf"), sha256=sha,
                              text=doc.text, cover=cover_json, parse_warnings=warnings))
        for c, v in zip(doc.clauses, vectors):
            s.add(ClauseRow(id=f"{company_id}:{cid}:v{version}:{c.number}", company_id=company_id, contract_id=cid,
                            version=version, is_current=True, number=c.number, heading=c.heading, text=c.text,
                            clause_type=c.clause_type, page=c.page, char_start=c.char_start,
                            char_end=c.char_end, bboxes=c.bboxes, embedding=v))
    return IngestResult(cid, version, prev is not None, prev, len(doc.clauses), warnings)


# ───────────────────────────── company context ─────────────────────────────
_CTX_KEYS = {"COMPANY NAME": "name", "INDUSTRY": "industry", "HQ / JURISDICTIONS": "jurisdictions",
             "JURISDICTIONS": "jurisdictions", "FISCAL YEAR START": "fiscal_year_start", "BASE CURRENCY": "base_currency",
             "RISK APPETITE": "risk_appetite", "APPROVAL THRESHOLD": "approval_threshold", "KEY CONTACTS": "contacts",
             "STRATEGIC PRIORITIES": "priorities", "CRITICAL DEPENDENCIES": "critical_deps"}


def parse_company_context(text: str) -> CompanyContext:
    vals: dict = {"raw_text": text}
    for line in text.splitlines():
        m = re.match(r"^\s*([A-Z][A-Z /]+?)\s*:\s*(.+?)\s*$", line)
        if not m or m.group(1).strip().upper() not in _CTX_KEYS:
            continue
        key, val = _CTX_KEYS[m.group(1).strip().upper()], m.group(2)
        if key in ("jurisdictions", "contacts"):
            vals[key] = [v.strip() for v in re.split(r"[;,]", val) if v.strip()]
        elif key == "approval_threshold":
            vals[key] = parse_money(val)
        elif key == "risk_appetite":
            v = val.strip().lower()
            vals[key] = v if v in ("low", "medium", "high") else "medium"
        else:
            vals[key] = val.strip()
    return CompanyContext(**vals)


def ingest_company_context(company_id: str, filename: str, content: bytes) -> CompanyContext:
    if filename.lower().endswith(".pdf"):
        import fitz
        with fitz.open(stream=content, filetype="pdf") as d:
            text = "\n".join(p.get_text() for p in d)
    elif filename.lower().endswith(".docx"):
        import io
        from docx import Document
        text = "\n".join(p.text for p in Document(io.BytesIO(content)).paragraphs)
    else:
        text = content.decode("utf-8", errors="replace")
    text = HOOKS.on_ingest(text, {"company_id": company_id, "filename": filename, "kind": "company_context"})
    ctx = parse_company_context(text)
    with db() as s:
        c = s.get(Company, company_id)
        c.context = ctx.model_dump(mode="json")
        if ctx.name:
            c.name = ctx.name
    return ctx
