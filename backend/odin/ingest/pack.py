"""Official dev-pack contract format: canonical .txt (citation anchor) + identical .pdf twin (viewer/boxes).

Headings: `Section A — Title` cover sections, `SECTION 1 — TITLE` groups with `1.1  Title. text` items
(also `§3.1` / `I.1` items inside cover sections), ALL-CAPS info blocks underlined with dashes
(PROVIDER INFORMATION, SIGNATURES), `EXHIBIT A — …`. Clause text is always the exact span of the source
text, so every clause (and every quote taken from it) is findable by plain text search.
"""
from __future__ import annotations

import bisect
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from odin.core.models import CoverMeta, Party, clause_ref

_GROUP = re.compile(r"^SECTION\s+(\d+)\s+[—–?-]+\s+(\S.*?)\s*$")   # the PDF twin renders "—" as "?"
_COVER = re.compile(rf"^Section\s+([A-Z])\s+[—–?-]+\s+(\S.*?)\s*$")
_EXHIBIT = re.compile(rf"^((?:EXHIBIT|SCHEDULE|ANNEX|APPENDIX)\s+[A-Z0-9]{{1,3}})\s+[—–?-]+\s+(\S.*?)\s*$")
_ITEM = re.compile(r"^( {0,4})(§?)(\d{1,2}\.\d{1,2}|[A-Z]\.\d{1,2})\s+(\S.*)$")
_CAPS = re.compile(r"^[A-Z][A-Z0-9 &/'(),.-]{2,60}$")
_RULE = re.compile(r"^(?:={5,}|-{5,})\s*$")
_UNDER = re.compile(r"^\s*-{3,}\s*$")
_CHROME = re.compile(r"Contract Twin\b|^ODIN DEV PACK|Contract Analysis Dataset|^Page \d+ of \d+$")   # PDF page header
_EXT_ID = re.compile(r"\b(?:CONTRACT|DOCUMENT) ID:\s*([A-Z0-9][A-Z0-9-]+)")


@dataclass
class Span:
    number: str
    ref: str
    heading: str
    start: int
    end: int
    parent_ref: Optional[str] = None


def is_pack(text: str) -> bool:
    heads = sum(1 for ln in text.splitlines() if _GROUP.match(ln) or _COVER.match(ln))
    return heads >= 2 or (heads >= 1 and bool(_EXT_ID.search(text)))


def number_to_ref(number: str) -> str:
    """Display reference as written: §3.2 / Section B / Section I.1 / SIGNATURES (shared models.clause_ref)."""
    return clause_ref(number)


def ref_to_number(ref: str) -> str:
    """'§3.2' / 'Section 4.3' / 'Sec. B' / 'clause 3.2.' / 'Special Terms §1' / 'Signatures' → stored number."""
    s = (ref or "").strip().rstrip(".")
    m = re.search(r"§\s*([0-9A-Z]+(?:\.\d+)*)", s)
    if m:
        return m.group(1)
    m = re.fullmatch(r"(?:(?:section|sec\.?|clause|article|para(?:graph)?)\s+)?([0-9]+(?:\.\d+)*|[A-Z](?:\.\d+)?)",
                     s, re.I)
    if m:
        v = m.group(1)
        return v.upper() if v[:1].isalpha() else v
    return s.upper()


def _heading(rest: str, fallback: str) -> str:
    m = re.match(r'^"([^"]{1,60})"', rest)
    if m:
        return m.group(1)
    m = re.match(r"^([A-Z][^.:;,]{1,70}?)\.(?:\s|$)", rest)
    if m and len(m.group(1).split()) <= 8:
        return m.group(1)
    return fallback


def segment_pack(text: str) -> tuple[list[Span], list[str]]:
    lines, pos = [], 0
    for raw in text.splitlines(keepends=True):
        ln = raw.rstrip("\r\n")
        lines.append((pos, "" if _CHROME.search(ln.strip()) else ln))   # page chrome is invisible to matching
        pos += len(raw)
    n = len(lines)
    nodes: list[tuple[int, str, str, str, str, Optional[str], str]] = []  # (line, kind, number, ref, heading, parent, title)
    group: tuple[str, str, str] | None = None        # (kind, number, title)
    for i, (_, ln) in enumerate(lines):
        nxt = next((lines[j][1] for j in range(i + 1, min(i + 4, n)) if lines[j][1].strip()), "")
        if m := _GROUP.match(ln):
            group = ("group", m.group(1), m.group(2))
            nodes.append((i, "group", m.group(1), f"Section {m.group(1)}", m.group(2), None, m.group(2)))
        elif m := _COVER.match(ln):
            group = ("cover", m.group(1), m.group(2))
            nodes.append((i, "cover", m.group(1), f"Section {m.group(1)}", m.group(2), None, m.group(2)))
        elif m := _EXHIBIT.match(ln):
            group = None
            num = re.sub(r"\s+", " ", m.group(1).upper())
            nodes.append((i, "exhibit", num, num, m.group(2), None, m.group(2)))
        elif _CAPS.match(ln) and _UNDER.match(nxt) and not _RULE.match(ln):
            group = None
            name = ln.strip()
            nodes.append((i, "block", name, name, name.title(), None, name))
        elif (m := _ITEM.match(ln)) and group:
            num, kind, gnum = m.group(3), group[0], group[1]
            ok = (num.split(".")[0] == gnum if kind == "group"
                  else (num[0].isdigit() or num[0] == gnum))
            if ok:
                ref = clause_ref(num)
                nodes.append((i, "item", num, ref, _heading(m.group(4), group[2]), f"Section {gnum}", group[2]))

    spans: list[Span] = []
    warnings: list[str] = []
    covered = [False] * n
    for k, (li, kind, num, ref, heading, parent, _) in enumerate(nodes):
        stop = nodes[k + 1][0] if k + 1 < len(nodes) else n
        body0 = li + 1
        if kind != "item":
            j = next((j for j in range(body0, stop) if lines[j][1].strip()), stop)
            if j < stop and _UNDER.match(lines[j][1]):
                body0 = j + 1
        end_li = body0
        while end_li < stop and not _RULE.match(lines[end_li][1]):
            end_li += 1
        for j in range(li, end_li):
            covered[j] = True
        has_body = any(lines[j][1].strip() for j in range(body0, end_li))
        has_items = k + 1 < len(nodes) and nodes[k + 1][1] == "item" and nodes[k + 1][5] == ref
        if kind in ("group", "cover") and has_items and not has_body:
            continue                                  # the items carry the text
        spans.append(_span(lines, li, end_li, num, ref, heading, parent))

    # text outside any heading: preamble before the first heading, NOTE blocks after it
    first = nodes[0][0] if nodes else n
    pre = [j for j in range(first) if lines[j][1].strip() and not _RULE.match(lines[j][1])]
    if pre:
        title = next((lines[j][1].strip() for j in pre), "")
        spans.insert(0, _span(lines, pre[0], pre[-1] + 1, "PREAMBLE", "PREAMBLE", title, None))
    run: list[int] = []
    notes = 0
    for j in list(range(first, n)) + [n]:
        blank = j == n or covered[j] or _RULE.match(lines[j][1]) or not lines[j][1].strip()
        if not blank:
            run.append(j)
            continue
        if run and (j == n or covered[j] or _RULE.match(lines[j][1])):
            body = " ".join(lines[x][1] for x in run)
            if re.search(r"[a-z]{3,}", body) and not body.strip().startswith("END OF"):
                notes += 1
                num = "NOTE" if notes == 1 else f"NOTE {notes}"
                spans.append(_span(lines, run[0], run[-1] + 1, num, num, "Unnumbered text", None))
            run = []
    spans.sort(key=lambda s: s.start)
    seen: dict[str, int] = {}
    for s in spans:
        if s.number in seen:
            seen[s.number] += 1
            warnings.append(f"Duplicate clause reference {s.ref} (stored as {s.number}#{seen[s.number]}).")
            s.number = f"{s.number}#{seen[s.number]}"
        else:
            seen[s.number] = 1
    if not spans:
        warnings.append("No pack-format headings found — whole document stored as one clause.")
        spans.append(Span("1", "Section 1", "Document", 0, len(text.rstrip())))
    return spans, warnings


def _span(lines, a: int, b: int, number, ref, heading, parent) -> Span:
    while b > a + 1 and not lines[b - 1][1].strip():
        b -= 1
    s0 = lines[a][0] + (len(lines[a][1]) - len(lines[a][1].lstrip()))
    e0 = lines[b - 1][0] + len(lines[b - 1][1].rstrip())
    return Span(number, ref, heading, s0, e0, parent)


# ───────────────────────────── cover meta ─────────────────────────────
_ENTITY = re.compile(r"((?:[A-Z][\w&.'-]*\s+){0,5}?(?:Inc\.|LLC|Corporation|Corp\.))(?:,[^\"()]*?)?\s*\(\s*\"(\w+)\"\s*\)")


def pack_cover(text: str, doc_id: str, title: str = "", company_name: str = "Quillhub") -> tuple[CoverMeta, dict, list[str]]:
    """CoverMeta (contract_id = doc id) + extra meta (external_id, doc_title) + warnings."""
    warnings: list[str] = []
    ext = _EXT_ID.search(text)
    first_title = next((ln.strip() for ln in text.splitlines() if ln.strip() and not _RULE.match(ln)), doc_id)
    eff = None
    m = re.search(r"EFFECTIVE DATE:\s+(.+)", text, re.I) or re.search(r"as of ([A-Z][a-z]+ \d{1,2}, \d{4}) \(the \"Effective Date\"\)", text)
    if m:
        raw = m.group(1).strip()
        from odin.ingest.parse import parse_date
        eff = parse_date(raw) if re.search(r"\d{4}", raw) else None
        if eff is None:
            warnings.append(f"Effective date not set in {doc_id}: '{raw}'.")
    gov = re.search(r"Governing Law:\s+(.+)", text) or re.search(r"governed by the laws of (?:the )?(State\s+of\s+\w+)", text)
    parties: list[Party] = []

    def add(name: str, capacity: str | None):
        name = " ".join(name.split()).strip(" ,")
        if name and all(p.name != name for p in parties):
            role = "company" if company_name.lower() in name.lower() else "counterparty"
            parties.append(Party(name=name, role=role, capacity=capacity))
    for blk in re.finditer(r"^(PROVIDER|CUSTOMER) INFORMATION\s*\n-+\s*\n\s*Legal Name:\s+(.+)$", text, re.M):
        add(blk.group(2), blk.group(1).title())
    if not parties:
        head = text[: text.find("SECTION 1") if "SECTION 1" in text else 3000]
        for em in _ENTITY.finditer(head):
            add(em.group(1), em.group(2))
    low = (title or first_title).lower()
    typ = ("amendment" if "amendment" in low else "sla" if "service level" in low
           else "dpa" if "data processing" in low else "standard_terms" if "standard terms" in low
           else "services" if "contractor" in low else "cloud_service" if "cover page" in low else "other")
    cover = CoverMeta(contract_id=doc_id, title=title or first_title, type=typ, effective_date=eff, parties=parties,
                      governing_law=" ".join(gov.group(1).split()) if gov else "")
    extra = {"external_id": ext.group(1) if ext else None, "doc_title": first_title, "canonical": "txt"}
    return cover, extra, warnings


# ───────────────────────────── text ↔ PDF boxes ─────────────────────────────
_QUOTES = {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2014": "-", "\u2013": "-"}


def fold(s: str, *, ascii_only: bool = False) -> tuple[str, list[int]]:
    """Whitespace-collapsed copy of s + map from each folded char to its offset in s. With ascii_only,
    drop non-ASCII and '?' (the PDF twin's font loses "—", "§", "≥")."""
    out, idx, space = [], [], False
    for i, ch in enumerate(s):
        if ch.isspace():
            space = bool(out)
            continue
        ch = _QUOTES.get(ch, ch)
        if ascii_only and (ord(ch) > 127 or ch == "?"):
            continue
        if space:
            out.append(" ")
            idx.append(i)
            space = False
        out.append(ch)
        idx.append(i)
    return "".join(out), idx


def pdf_boxes(text: str, spans: list[Span], pdf_path: Path) -> list[tuple[int, list[list[float]]]]:
    """For each span: (page, [[page,x0,y0,x1,y1], ...]) found by searching its lines in the PDF in order."""
    from odin.ingest.parse import layout
    ptxt, plines = layout(pdf_path)
    pf, pidx = fold(ptxt, ascii_only=True)
    starts = [ln.start for ln in plines]
    cur = 0
    out = []
    for sp in spans:
        boxes: list[list[float]] = []
        for raw in text[sp.start:sp.end].splitlines():
            q, _ = fold(raw, ascii_only=True)
            if len(q) < 4:
                continue
            at = pf.find(q, cur)
            if at < 0:
                continue
            a, b = pidx[at], pidx[at + len(q) - 1] + 1
            cur = at + len(q)
            li = max(0, bisect.bisect_right(starts, a) - 1)
            while li < len(plines) and plines[li].start < b:
                ws = [w for w in plines[li].words if w.start < b and w.end > a]
                if ws:
                    boxes.append([plines[li].page, min(w.x0 for w in ws), min(w.y0 for w in ws),
                                  max(w.x1 for w in ws), max(w.y1 for w in ws)])
                li += 1
        out.append((boxes[0][0] if boxes else 1, boxes))
    return out


def parse_pack(text: str, pdf_path: Path, doc_id: str | None, fallback_id: str, title: str = ""):
    """ParsedDoc for a pack-format text. doc_id None → cover CONTRACT/DOCUMENT ID, else fallback_id."""
    from odin.ingest.parse import ParsedClause, ParsedDoc, classify
    spans, warnings = segment_pack(text)
    ext = _EXT_ID.search(text)
    cover, extra, w = pack_cover(text, doc_id or (ext.group(1) if ext else fallback_id), title)
    warnings += w
    boxes = pdf_boxes(text, spans, pdf_path)
    missing = sum(1 for _, b in boxes if not b)
    if missing:
        warnings.append(f"{missing} clause(s) could not be located in the PDF twin (no highlight boxes).")
    clauses = [ParsedClause(number=s.number, heading=s.heading, text=text[s.start:s.end], page=pg,
                            char_start=s.start, char_end=s.end, clause_type=classify(s.heading, text[s.start:s.end]),
                            bboxes=bx, ref=s.ref, parent_ref=s.parent_ref)
               for s, (pg, bx) in zip(spans, boxes)]
    return ParsedDoc(text=text, cover=cover, clauses=clauses, warnings=warnings), extra


# ───────────────────────────── relations / amendments ─────────────────────────────
@dataclass
class DocInfo:
    doc_id: str
    text: str
    title: str
    external_id: Optional[str]
    effective: Optional[date]
    clauses: list            # objects with number, ref, char_start, char_end, text


def _clause_at(d: DocInfo, pos: int):
    return next((c for c in d.clauses if c.char_start <= pos < c.char_end), None)


def _para(text: str, pos: int) -> tuple[int, int]:
    a = text.rfind("\n\n", 0, pos)
    b = text.find("\n\n", pos)
    a = 0 if a < 0 else a + 2
    b = len(text) if b < 0 else b
    while a < b and text[a].isspace():
        a += 1
    return a, b


def _cite(d: DocInfo, pos: int) -> dict:
    a, b = _para(d.text, pos)
    if b - a > 400:                               # long paragraph → just the line with the mention
        a = d.text.rfind("\n", 0, pos) + 1
        b = d.text.find("\n", pos)
        b = len(d.text) if b < 0 else b
        while d.text[a].isspace():
            a += 1
    c = _clause_at(d, pos)
    num = c.number if c else ""
    return {"contract_id": d.doc_id, "clause_number": num, "ref": (c.ref or number_to_ref(num)) if c else "",
            "quote": d.text[a:b].rstrip(), "verified": True}


_OVR = re.compile(r"Section\s+(\d+(?:\.\d+)?|[A-Z])\s+of\s+the\s+(SLA|Cover\s+Page|Agreement|Standard\s+Terms|DPA|Addendum)"
                  r"(?:\s*\((?:Contract|Document)\s+ID:\s*([A-Z0-9-]+)\))?\s+is\s+(?:hereby\s+)?"
                  r"(deleted\s+in\s+its\s+entirety\s+and\s+replaced\s+with\s+the\s+following|amended\s+as\s+follows"
                  r"|amended\s+and\s+restated|deleted)")
_ADD = re.compile(r"(?:new\s+)?Section\s+(\d+(?:\.\d+)?|[A-Z])\s+is\s+(?:hereby\s+)?added\s+to\s+the\s+"
                  r"(SLA|Cover\s+Page|Agreement|Standard\s+Terms|DPA|Addendum)")


def detect_relations(docs: list[DocInfo]) -> tuple[list[dict], list[dict], list[str]]:
    """doc_relation + clause_override payloads (shared contract) found from cross-document mentions."""
    by_ext = {d.external_id: d for d in docs if d.external_id}
    rels: dict[tuple, dict] = {}
    warnings: list[str] = []

    def add(frm: str, to: str, rel: str, detail: str, cit: dict):
        if frm != to:
            rels.setdefault((frm, to, rel), {"from_doc": frm, "to_doc": to, "relation": rel, "detail": detail,
                                             "citation": cit})
    for x in docs:
        is_amend = "amendment" in x.title.lower()
        is_add = "addendum" in x.title.lower() or "addendum" in x.text[:600].lower()
        targets = [(y, m.start()) for y in docs if y is not x
                   for pat in ([re.escape(y.external_id)] if y.external_id else []) + [rf"\b{re.escape(y.doc_id)}\.(?:txt|pdf)\b"]
                   for m in re.finditer(pat, x.text)]
        for y, pos in sorted(targets, key=lambda t: t[1]):
            a, b = _para(x.text, pos)
            para = " ".join(x.text[a:b].split()).lower()
            label = f"{y.doc_id} ({y.external_id})" if y.external_id else y.doc_id
            if is_amend and "amend" in para:
                add(x.doc_id, y.doc_id, "amends", f"{x.doc_id} amends {label}", _cite(x, pos))
            elif is_add and ("supplement" in para or "addendum" in para):
                add(x.doc_id, y.doc_id, "addendum_to", f"{x.doc_id} is an addendum to {label}", _cite(x, pos))
            elif "is incorporated by reference into" in para:
                add(y.doc_id, x.doc_id, "incorporates", f"{y.doc_id} incorporates {x.doc_id} by reference "
                    f"(stated in {x.doc_id})", _cite(x, pos))
            elif "incorporat" in para:
                add(x.doc_id, y.doc_id, "incorporates", f"{x.doc_id} incorporates {label} by reference", _cite(x, pos))

    overrides: list[dict] = []
    for x in docs:
        amended = [t for (f, t, r) in rels if f == x.doc_id and r == "amends"]
        if not amended:
            continue
        for c in x.clauses:
            for m in list(_OVR.finditer(c.text)) + list(_ADD.finditer(c.text)):
                num, target_name = m.group(1), " ".join(m.group(2).split()).lower()
                ext = m.group(3) if m.re is _OVR else None
                mode = ("added" if m.re is _ADD else "replaced" if "replaced" in m.group(4)
                        else "deleted" if m.group(4).startswith("deleted") else "amended")
                tgt = by_ext.get(ext) if ext else None
                if tgt is None:
                    want = {"sla": "service level", "cover page": "cover page", "agreement": "cover page",
                            "standard terms": "standard terms"}.get(target_name, target_name)
                    tgt = next((d for d in docs if d.doc_id in amended and want in d.title.lower()), None)
                if tgt is None:
                    warnings.append(f"{x.doc_id} {c.ref or c.number}: cannot resolve amended document "
                                    f"'{m.group(2)}' for Section {num}.")
                    continue
                rest = c.text[m.end():]
                if mode == "replaced" and '"' in rest:
                    qa = c.text.index('"', m.end()) + 1
                    qb = c.text.rindex('"')
                    new_text = c.text[qa:qb].strip()
                elif mode == "deleted":
                    new_text = ""
                else:
                    new_text = rest.lstrip(" :\n").rstrip()
                pos = c.char_start + m.start()
                line_a = x.text.rfind("\n", 0, pos) + 1
                line_b = x.text.find("\n", pos)
                overrides.append({"doc": tgt.doc_id, "number": num, "target_ref": number_to_ref(num),
                                  "by_doc": x.doc_id, "by_ref": c.ref or number_to_ref(c.number),
                                  "by_number": c.number, "mode": mode,
                                  "effective": x.effective.isoformat() if x.effective else None,
                                  "new_text": new_text,
                                  "citation": {"contract_id": x.doc_id, "clause_number": c.number,
                                               "ref": c.ref or number_to_ref(c.number),
                                               "quote": x.text[line_a:line_b if line_b > 0 else None].strip(),
                                               "verified": True}})
    return list(rels.values()), overrides, warnings
