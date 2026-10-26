"""Document → (text, words-with-positions) → cover meta + clauses with highlight boxes.

Everything goes through PDF: DOCX is converted first (LibreOffice if present, otherwise rendered
from python-docx text), so the viewer, page numbers and bounding boxes are always consistent.
"""
from __future__ import annotations

import html
import re
import shutil
import subprocess
import tempfile
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

import fitz  # pymupdf
from dateutil import parser as dparser

from odin.core.models import CoverMeta, Money, Party


# ───────────────────────────── conversion ─────────────────────────────
def _soffice() -> Optional[str]:
    for name in ("soffice", "libreoffice"):
        p = shutil.which(name)
        if p:
            return p
    for p in (r"C:\Program Files\LibreOffice\program\soffice.exe",):
        if Path(p).exists():
            return p
    return None


def docx_text(src: Path) -> str:
    """Body text in document order (paragraphs + tables), with Word auto-numbers written out literally."""
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    doc = Document(str(src))
    num_part = doc.part.numbering_part.element

    def fmt(num_id: str, lvl: int) -> str:
        if num_part is None:
            return ""
        r = num_part.xpath(f"w:abstractNum[@w:abstractNumId=//w:num[@w:numId='{num_id}']/w:abstractNumId/@w:val]"
                           f"/w:lvl[@w:ilvl='{lvl}']/w:numFmt/@w:val")
        return r[0] if r else ""

    counters: dict[str, list[int]] = {}
    out: list[str] = []
    for el in doc.element.body.iterchildren():
        if el.tag.endswith("}p"):
            p = Paragraph(el, doc)
            pr = el.pPr.numPr if el.pPr is not None else None
            if pr is None and p.style is not None and p.style.element.pPr is not None:
                pr = p.style.element.pPr.numPr   # numbering inherited from a style (e.g. "List Number")
            prefix = ""
            if pr is not None and pr.numId is not None and fmt(str(pr.numId.val), pr.ilvl.val if pr.ilvl is not None else 0) == "decimal":
                lvl = pr.ilvl.val if pr.ilvl is not None else 0
                c = counters.setdefault(str(pr.numId.val), [])
                del c[lvl + 1:]
                c.extend([0] * (lvl + 1 - len(c)))
                c[lvl] += 1
                prefix = ".".join(map(str, c)) + ("." if lvl == 0 else "") + " "
                if p.text.lstrip()[:1].isdigit():   # already typed literally
                    prefix = ""
            out.append(prefix + p.text)
        elif el.tag.endswith("}tbl"):
            for row in Table(el, doc).rows:
                out.append(" | ".join(c.text.strip() for c in row.cells))
    return "\n".join(out)


def docx_to_pdf(src: Path, dst: Path) -> list[str]:
    """Viewer PDF for a DOCX. LibreOffice (exact rendering) when installed; otherwise rendered from the
    python-docx text. Returns warnings."""
    office = _soffice()
    if office:
        try:
            with tempfile.TemporaryDirectory() as td:
                subprocess.run([office, "--headless", "--convert-to", "pdf", "--outdir", td, str(src)],
                               check=True, capture_output=True, timeout=120)
                shutil.move(str(Path(td) / (src.stem + ".pdf")), dst)
            return []
        except (subprocess.SubprocessError, OSError):
            pass   # fall back to python-docx text
    text_to_pdf(docx_text(src), dst)
    return []


def image_to_pdf(content: bytes, ext: str, dst: Path) -> None:
    with fitz.open(stream=content, filetype=ext.lstrip(".")) as img:
        dst.write_bytes(img.convert_to_pdf())


_OCR = None
# OCR often drops the space after "1." and inside all-caps cover keys ("CONTRACTID:")
_OCR_GLUE = re.compile(r"^(\d{1,3}(?:\.\d{1,3}){0,3}\.)(?=[A-Za-z])|^(CONTRACT|EFFECTIVE|GOVERNING)(?=ID|TITLE|TYPE|DATE|LAW)")


def _ocr_page(page) -> tuple[list[tuple[str, float, tuple[float, float, float, float]]], float]:
    """RapidOCR on one page → ([(text, conf, (x0,y0,x1,y1) in PDF points)], mean confidence)."""
    global _OCR
    if _OCR is None:
        from rapidocr_onnxruntime import RapidOCR   # lazy: onnx model load is slow
        _OCR = RapidOCR()
    zoom = 2.0
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csGRAY)
    res, _ = _OCR(pix.tobytes("png"))
    out = []
    for box, txt, conf in res or []:
        txt = _OCR_GLUE.sub(lambda m: m.group(0) + " ", txt)
        xs, ys = [pt[0] for pt in box], [pt[1] for pt in box]
        out.append((txt, float(conf), (min(xs) / zoom, min(ys) / zoom, max(xs) / zoom, max(ys) / zoom)))
    return out, (sum(o[1] for o in out) / len(out) if out else 0.0)


def text_to_pdf(text: str, dst: Path) -> None:
    body = "".join(f"<p>{html.escape(l) or '&nbsp;'}</p>" for l in text.splitlines())
    story = fitz.Story(html=f"<body style='font-family:sans-serif;font-size:10pt'>{body}</body>")
    writer = fitz.DocumentWriter(str(dst))
    rect = fitz.paper_rect("a4")
    more = 1
    while more:
        dev = writer.begin_page(rect)
        more, _ = story.place(rect + (54, 54, -54, -54))
        story.draw(dev)
        writer.end_page()
    writer.close()


# ───────────────────────────── word layout ─────────────────────────────
@dataclass
class Word:
    page: int
    x0: float
    y0: float
    x1: float
    y1: float
    start: int
    end: int


@dataclass
class Line:
    page: int
    text: str
    start: int
    words: list[Word] = field(default_factory=list)


def clean_text(s: str) -> str:
    """Ligatures (ﬁ, ﬂ) → plain letters, and drop broken surrogate/replacement chars that a PDF font
    without the ligature glyph yields. Otherwise quotes, search and re-ingested versions get garbled."""
    s = unicodedata.normalize("NFKC", s)
    return "".join(ch for ch in s if not (0xD800 <= ord(ch) <= 0xDFFF or ch == "�"))


def layout(pdf_path: Path, warnings: Optional[list[str]] = None) -> tuple[str, list[Line]]:
    """Rebuild reading-order text with a char→bbox map. Lines are grouped by visual baseline."""
    doc = fitz.open(str(pdf_path))
    lines: list[Line] = []
    parts: list[str] = []
    pos = 0
    for pno, page in enumerate(doc, start=1):
        words = page.get_text("words")
        if not words and page.get_images():   # no text layer → OCR; one "word" per recognised line
            found, conf = _ocr_page(page)
            words = [(*bb, t, 0, 0, 0) for t, _, bb in found]
            if words and warnings is not None:
                warnings.append(f"Page {pno} text recovered by OCR (confidence {conf:.2f}).")
        words = sorted(words, key=lambda w: (round((w[1] + w[3]) / 2 / 3), w[0]))
        cur: list = []
        cur_y = None
        groups = []
        for w in words:
            yc = (w[1] + w[3]) / 2
            if cur_y is None or abs(yc - cur_y) <= 3:
                cur.append(w)
                cur_y = yc if cur_y is None else cur_y
            else:
                groups.append(cur)
                cur, cur_y = [w], yc
        if cur:
            groups.append(cur)
        for g in groups:
            g.sort(key=lambda w: w[0])
            line = Line(page=pno, text="", start=pos)
            chunks = []
            for i, w in enumerate(g):
                if i:
                    chunks.append(" ")
                    pos += 1
                t = clean_text(w[4])
                line.words.append(Word(pno, w[0], w[1], w[2], w[3], pos, pos + len(t)))
                chunks.append(t)
                pos += len(t)
            line.text = "".join(chunks)
            parts.append(line.text + "\n")
            pos += 1
            lines.append(line)
    doc.close()
    return "".join(parts), lines


# ───────────────────────────── cover + clauses ─────────────────────────────
COVER_KEYS = {"CONTRACT TITLE": "title", "CONTRACT ID": "contract_id", "CONTRACT TYPE": "type",
              "EFFECTIVE DATE": "effective_date", "GOVERNING LAW": "governing_law", "VERSION": "version",
              "SUPERSEDES": "supersedes"}
_KV = re.compile(r"^\s*([A-Z][A-Z /]+?)\s*:\s*(.+?)\s*$")
_CLAUSE = re.compile(r"^(\d{1,3}(?:\.\d{1,3}){0,3})(\.?)\s+(\S.*)$")
_SCHED = re.compile(r"^((?:SCHEDULE|ANNEX|ANNEXURE|EXHIBIT|APPENDIX)\s+[A-Z0-9]{1,3})\b\s*[-–—:]?\s*(.*)$", re.I)

CLAUSE_TYPES = [
    ("renewal", r"renew"), ("term", r"\bterm\b|duration|commencement"), ("payment", r"payment|fee|price|invoice|rent|charges|compensation|salary"),
    ("penalty", r"penalt|liquidated|late|interest|service credit"), ("sla", r"service level|\bsla\b|uptime|availability"),
    ("liability", r"liabilit|limitation"), ("indemnity", r"indemn"), ("termination", r"terminat"),
    ("confidentiality", r"confidential|non-disclosure"), ("compliance", r"complian|regulat|data protection|privacy|gdpr|dpdp|audit"),
    ("governing_law", r"governing law|jurisdiction"), ("dispute", r"dispute|arbitration"), ("exclusivity", r"exclusiv|non-compete|non-solicit"),
    ("force_majeure", r"force majeure"), ("assignment", r"assign|change of control"), ("delivery", r"deliver|supply|shipment"),
    ("insurance", r"insurance"), ("ip", r"intellectual property|\bip\b|licen[cs]e"), ("definitions", r"definition|interpretation"),
]


def classify(heading: str, text: str) -> str:
    h = heading.lower()
    for name, pat in CLAUSE_TYPES:
        if re.search(pat, h):
            return name
    t = text.lower()[:400]
    for name, pat in CLAUSE_TYPES:
        if re.search(pat, t):
            return name
    return "general"


@dataclass
class ParsedClause:
    number: str
    heading: str
    text: str
    page: int
    char_start: int
    char_end: int
    clause_type: str
    bboxes: list[list[float]]
    ref: Optional[str] = None           # display reference as written (§3.2, Section B)
    parent_ref: Optional[str] = None    # enclosing section for sub-clauses (Section D)


@dataclass
class ParsedDoc:
    text: str
    cover: CoverMeta
    clauses: list[ParsedClause]
    warnings: list[str]
    extra: dict = field(default_factory=dict)   # cover meta beyond CoverMeta (external_id, canonical, ...)


def parse_date(s: str) -> Optional[date]:
    try:   # ISO first — dayfirst=True would turn 2026-04-01 into 4 January
        return date.fromisoformat(s.strip()[:10])
    except ValueError:
        pass
    try:
        return dparser.parse(s, dayfirst=True, fuzzy=True).date()
    except (ValueError, OverflowError):
        return None


_MONEY = re.compile(r"(INR|USD|EUR|GBP|Rs\.?|₹|\$|€|£)\s*([\d,]+(?:\.\d+)?)", re.I)
_CUR = {"rs": "INR", "rs.": "INR", "₹": "INR", "$": "USD", "€": "EUR", "£": "GBP"}


def parse_money(s: str) -> Optional[Money]:
    m = _MONEY.search(s or "")
    if not m:
        return None
    cur = _CUR.get(m.group(1).lower(), m.group(1).upper())
    return Money(amount=float(m.group(2).replace(",", "")), currency=cur)


def _accept_number(num: str, dot: str, rest: str, top: int) -> bool:
    parts = [int(p) for p in num.split(".")]
    if len(parts) == 1:
        # "3. PAYMENT" — needs the trailing dot, an upper-case start, and to be the next top-level number
        return bool(dot) and rest[:1].isupper() and (top == 0 or parts[0] == top + 1)
    return parts[0] in (top, top + 1) and all(p > 0 for p in parts[1:])


def segment(text: str, lines: list[Line]) -> tuple[CoverMeta | None, list[ParsedClause], list[str]]:
    warnings: list[str] = []
    starts: list[tuple[int, str, str]] = []      # (line index, number, heading-ish rest)
    top = 0
    for i, ln in enumerate(lines):
        t = ln.text.strip()
        m = _CLAUSE.match(t)
        if m and _accept_number(m.group(1), m.group(2), m.group(3), top):
            num = m.group(1)
            top = int(num.split(".")[0])
            starts.append((i, num, m.group(3)))
            continue
        s = _SCHED.match(t)
        if s and (t.isupper() or s.group(1).isupper()):
            starts.append((i, s.group(1).upper(), s.group(2)))

    cover_lines = lines[: starts[0][0]] if starts else lines
    cover = _parse_cover([l.text for l in cover_lines], warnings)

    clauses: list[ParsedClause] = []
    heading_of_top: dict[str, str] = {}
    seen: dict[str, int] = {}
    for k, (li, num, rest) in enumerate(starts):
        end_li = starts[k + 1][0] if k + 1 < len(starts) else len(lines)
        seg = lines[li:end_li]
        c0, c1 = seg[0].start, seg[-1].start + len(seg[-1].text)
        body = text[c0:c1].strip()
        is_heading = rest.isupper() and len(rest) < 80
        topnum = num.split(".")[0]
        if is_heading and "." not in num:
            heading_of_top[topnum] = rest.strip()
        heading = rest.strip() if is_heading else heading_of_top.get(topnum, "")
        if num in seen:
            seen[num] += 1
            warnings.append(f"Duplicate clause number {num} (renamed {num}#{seen[num]}) — check numbering.")
            num = f"{num}#{seen[num]}"
        else:
            seen[num] = 1
        clauses.append(ParsedClause(number=num, heading=heading, text=body, page=seg[0].page, char_start=c0,
                                    char_end=c1, clause_type=classify(heading, body), bboxes=_boxes(seg)))
    if not clauses:
        warnings.append("No numbered clauses found — whole document stored as one clause (spec §3.1).")
        if lines:
            clauses.append(ParsedClause("1", "Document", text.strip(), lines[0].page, 0, len(text), "general",
                                        _boxes(lines)))
    return cover, clauses, warnings


def _boxes(seg: list[Line]) -> list[list[float]]:
    out = []
    for ln in seg:
        if ln.words:
            out.append([ln.page, min(w.x0 for w in ln.words), min(w.y0 for w in ln.words),
                        max(w.x1 for w in ln.words), max(w.y1 for w in ln.words)])
    return out


def _parse_cover(cover_lines: list[str], warnings: list[str]) -> CoverMeta | None:
    vals: dict = {}
    parties: list[Party] = []
    for raw in cover_lines:
        m = _KV.match(raw)
        if not m:
            continue
        key, val = m.group(1).strip().upper(), m.group(2).strip()
        if key.startswith("PARTY"):
            name = re.sub(r"\(.*?\)", "", val).strip()
            alias = (re.search(r'"([^"]+)"', val) or [None, None])[1]
            role = "company" if key.endswith(" A") else "counterparty"
            parties.append(Party(name=name, role=role, alias=alias))
        elif key in COVER_KEYS:
            vals[COVER_KEYS[key]] = val
    if "contract_id" not in vals:
        return None
    if "effective_date" in vals:
        d = parse_date(vals["effective_date"])
        if not d:
            warnings.append(f"Unparseable EFFECTIVE DATE '{vals['effective_date']}'.")
        vals["effective_date"] = d
    if "version" in vals:
        try:
            vals["version"] = int(re.sub(r"\D", "", vals["version"]) or 1)
        except ValueError:
            vals.pop("version")
    vals["type"] = (vals.get("type") or "other").split("|")[0].strip().lower()
    if vals.get("supersedes", "").lower() in ("", "none", "n/a", "-"):
        vals["supersedes"] = None
    return CoverMeta(parties=parties, **vals)


def parse_pdf(pdf_path: Path, fallback_id: str) -> ParsedDoc:
    warnings: list[str] = []
    text, lines = layout(pdf_path, warnings)
    if not text.strip():
        raise ValueError("Document has no extractable text, even after OCR.")
    from odin.ingest import pack
    if pack.is_pack(text):              # official dev-pack layout (e.g. an uploaded PDF twin)
        doc, extra = pack.parse_pack(text, pdf_path, None, fallback_id)
        doc.warnings[:0] = warnings
        doc.extra = extra
        return doc
    cover, clauses, w = segment(text, lines)
    warnings += w
    if cover is None:
        warnings.append(f"No 'CONTRACT ID:' in cover block — using '{fallback_id}'.")
        cover = CoverMeta(contract_id=fallback_id, title=fallback_id)
    return ParsedDoc(text=text, cover=cover, clauses=clauses, warnings=warnings)
