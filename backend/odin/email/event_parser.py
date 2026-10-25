"""Strict parser for the Heimdall email event format (spec §3.3) + template used in auto-replies."""
from __future__ import annotations

import re
from datetime import datetime, timezone

from dateutil import parser as dparser

from odin.core.config import odin_config
from odin.core.models import EVENT_TYPES, ParsedEvent
from odin.ingest.parse import parse_money

TEMPLATE = """Subject: [ODIN-EVENT] <EVENT_TYPE> <CONTRACT_ID|ALL>

EVENT_ID: EVT-0001                      (optional)
EVENT_TYPE: PAYMENT_LATE                (required)
OCCURRED_AT: 2026-11-03T10:30:00+05:30  (required, ISO 8601)
CONTRACT_ID: MSA-2026-001               (or ALL / comma list / UNKNOWN)
COUNTERPARTY: Nimbus Cloud Ltd          (optional)
AMOUNT: INR 2,50,000                    (optional)
REFERENCE: Invoice INV-2231             (optional)
SEVERITY_HINT: low|medium|high          (optional)
DESCRIPTION:
Free text until the end of the email.

EVENT_TYPE is one of: """ + ", ".join(EVENT_TYPES)

KEYS = ("EVENT_ID", "EVENT_TYPE", "OCCURRED_AT", "CONTRACT_ID", "COUNTERPARTY", "AMOUNT", "REFERENCE",
        "SEVERITY_HINT", "DESCRIPTION")
_KV = re.compile(r"^\s*([A-Z_]+)\s*:\s*(.*)$")


class EventParseError(Exception):
    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


def is_event_subject(subject: str) -> bool:
    return (subject or "").strip().upper().startswith(odin_config()["email"]["subject_prefix"].upper())


def strip_quoted(body: str) -> str:
    """Drop quoted replies / signatures that mail clients append."""
    out = []
    for line in body.replace("\r\n", "\n").split("\n"):
        if line.startswith(">") or re.match(r"^On .+ wrote:$", line.strip()) or line.strip() == "--":
            break
        out.append(line)
    return "\n".join(out).strip()


def parse(subject: str, body: str) -> ParsedEvent:
    problems: list[str] = []
    prefix = odin_config()["email"]["subject_prefix"]
    rest = (subject or "").strip()[len(prefix):].strip().split() if is_event_subject(subject) else []
    vals: dict[str, str] = {}
    desc: list[str] = []
    in_desc = False
    for line in strip_quoted(body).split("\n"):
        if in_desc:
            desc.append(line)
            continue
        m = _KV.match(line)
        if m and m.group(1) in KEYS:
            if m.group(1) == "DESCRIPTION":
                in_desc = True
                if m.group(2).strip():
                    desc.append(m.group(2))
            else:
                vals[m.group(1)] = m.group(2).strip()

    etype = (vals.get("EVENT_TYPE") or (rest[0] if rest else "")).upper()
    if etype not in EVENT_TYPES:
        problems.append(f"EVENT_TYPE '{etype or '(missing)'}' is not one of the allowed types")
    occurred = None
    if vals.get("OCCURRED_AT"):
        try:
            occurred = dparser.isoparse(vals["OCCURRED_AT"])
        except (ValueError, OverflowError):
            try:
                occurred = dparser.parse(vals["OCCURRED_AT"], dayfirst=True)
            except (ValueError, OverflowError):
                problems.append(f"OCCURRED_AT '{vals['OCCURRED_AT']}' is not a valid date/time (use ISO 8601)")
    else:
        problems.append("OCCURRED_AT is missing")
    raw_ids = vals.get("CONTRACT_ID") or (rest[1] if len(rest) > 1 else "")
    ids = [] if raw_ids.upper() in ("", "UNKNOWN") else ["ALL"] if raw_ids.upper() == "ALL" else \
        [c.strip() for c in raw_ids.split(",") if c.strip()]
    amount = None
    if vals.get("AMOUNT"):
        amount = parse_money(vals["AMOUNT"])
        if not amount:
            problems.append(f"AMOUNT '{vals['AMOUNT']}' not understood (use e.g. 'INR 2,50,000' or 'USD 1200')")
    if problems:
        raise EventParseError(problems)
    if occurred.tzinfo is None:
        occurred = occurred.replace(tzinfo=timezone.utc)
    return ParsedEvent(event_type=etype, occurred_at=occurred, contract_ids=ids, amount=amount,
                       counterparty=vals.get("COUNTERPARTY", ""), reference=vals.get("REFERENCE", ""),
                       severity_hint=vals.get("SEVERITY_HINT", ""), description="\n".join(desc).strip(),
                       external_id=vals.get("EVENT_ID", ""))


def reply_body(problems: list[str]) -> str:
    return ("Odin could not process your event email:\n\n" + "\n".join(f"  - {p}" for p in problems)
            + "\n\nPlease resend using this format:\n\n" + TEMPLATE + "\n\n— Heimdall (automated)")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
