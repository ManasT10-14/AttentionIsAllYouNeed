"""Exact, typed corpus assertions. No model inference or oracle-driven filling."""

import re
from decimal import Decimal


def decimal_string(value):
    return format(Decimal(str(value)).normalize(), "f")


def thor_projection(extraction, names=()):
    """Explicit mappings from Odin's actual schema; unsupported concepts stay absent.

    `names` are the golden concept names being scored. Names the fixed mappings below do
    not cover are resolved by `_resolve` from Odin's generic fields (penalties, deadlines,
    periods, related contracts, forum, notice, party capacity).
    """
    result = {}
    party_ids = []
    for party in extraction.get("parties", []):
        name = party.get("name", "").casefold()
        for alias, identity in (
            ("aurora software", "P01"),
            ("forge electronics", "P02"),
            ("willow housing", "P03"),
        ):
            if alias in name:
                party_ids.append(identity)
    if party_ids:
        result["party_ids"] = sorted(set(party_ids))
    term = extraction.get("term") or {}
    start, end = term.get("effective_date"), term.get("end_date")
    if start and not end and term.get("term_months"):
        from datetime import date, timedelta

        from dateutil.relativedelta import relativedelta

        end = (
            date.fromisoformat(start)
            + relativedelta(months=term["term_months"])
            - timedelta(days=1)
        ).isoformat()
    if start and end:
        for name in ("initial_term", "exchange_period", "operating_term"):
            result[name] = [start, end]
    if start:
        result["effective_at"] = start
    if end:
        result["term_end"] = end
    renewal = extraction.get("renewal") or {}
    if type(renewal.get("auto_renew")) is bool:
        result["auto_renew"] = renewal["auto_renew"]
    if renewal.get("notice_days") is not None:
        for name in ("nonrenewal_notice_days", "renewal_notice_days"):
            result[name] = renewal["notice_days"]
    if renewal.get("renewal_period_months") is not None:
        result["renewal_months"] = renewal["renewal_period_months"]
    for payment in extraction.get("payments", []):
        amount = payment.get("amount") or {}
        if amount.get("currency") != "INR" or amount.get("amount") is None:
            continue
        value = decimal_string(amount["amount"])
        outgoing = "aurora" in payment.get("payer", "").lower() or payment.get("payer") == "P01"
        incoming = "aurora" in payment.get("payee", "").lower() or payment.get("payee") == "P01"
        if payment.get("frequency") == "monthly":
            result.setdefault("monthly_fee_inr", value)
            if outgoing:
                for name in (
                    "monthly_fee_payable_inr",
                    "monthly_rent_payable_inr",
                    "monthly_hire_payable_inr",
                ):
                    result.setdefault(name, value)
            if incoming:
                for name in ("monthly_fee_receivable_inr", "monthly_receivable_fee_inr"):
                    result.setdefault(name, value)
            rule = payment.get("due_rule", "").casefold()
            match = re.search(
                r"\b(?:on|by)\s+(?:the\s+)?(\d{1,2}(?:st|nd|rd|th)?|[a-z-]+)\s+"
                r"(?:day\s+)?(?:of\s+)?(?:(?:that|each|the|every)\s+)?(?:calendar\s+)?month\b",
                rule,
            )
            words = {
                "first": 1,
                "second": 2,
                "third": 3,
                "fourth": 4,
                "fifth": 5,
                "sixth": 6,
                "seventh": 7,
                "eighth": 8,
                "ninth": 9,
                "tenth": 10,
                "twentieth": 20,
            }
            token = match.group(1) if match else ""
            numeric = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)?", token)
            day = int(numeric.group(1)) if numeric else words.get(token)
            if day is not None and 1 <= day <= 31:
                result.setdefault("rent_due_day", day)
                result.setdefault("monthly_payment_due_day_utc", day)
        if payment.get("frequency") == "annual" and outgoing:
            result.setdefault("annual_fee_payable_inr", value)
            if payment.get("first_due"):
                result.setdefault("initial_fee_due", payment["first_due"])
    for name in names:
        if name not in result:
            value = _resolve(name, extraction)
            if value is not None:
                result[name] = value
    return result


_PARTY_IDS = (("aurora software", "P01"), ("forge electronics", "P02"), ("willow housing", "P03"))
_COMPANY = "aurora"
# Words in a golden name that point at the matching clause wording, e.g. "daily_demo_delay".
_KEYWORDS = {
    "delivery": "deliver",
    "funding": "fund",
    "approved_plan": "plan",
    "return": "return|hand ?back",
    "handback": "return|hand ?back",
    "amendment": "amend",
    "demo": "demo",
    "replacement": "replac",
    "disclosure": "disclos|recipient",
    "repair": "repair",
    "purchase": "purchase|price",
    "sale": "sale|price",
    "project": "project|price",
    "milestone": "milestone",
    "procurement": "procure",
    "hosting": "hosting",
}
_UNITS = ("minutes", "hours", "days", "months", "years")


def _money(value):
    if (
        isinstance(value, dict)
        and value.get("currency") == "INR"
        and value.get("amount") is not None
    ):
        return decimal_string(value["amount"])
    return None


def _utc(value):
    from datetime import datetime, timezone

    if not value:
        return None
    moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _keyword(name):
    hits = [pattern for word, pattern in _KEYWORDS.items() if word in name]
    return re.compile("|".join(hits), re.I) if hits else None


def _text(item, *keys):
    return " ".join(str(item.get(k) or "") for k in keys)


def _direction(name):
    if "payable" in name:
        return "payable"
    if "recoverable" in name or "receivable" in name:
        return "receivable"
    return None


def _penalty(name, extraction):
    pens = extraction.get("penalties") or []
    direction, keyword = _direction(name), _keyword(name)

    def pick(**want):
        for pen in pens:
            if direction and pen.get("direction") != direction:
                continue
            if any(pen.get(k) != v for k, v in want.items()):
                continue
            text = _text(pen, "trigger", "note", "pct_base")
            if keyword and len(pens) > 1 and not keyword.search(text):
                continue
            return pen
        return None

    if name.endswith("_rate"):
        pen = pick(basis="per_day") if name.startswith("daily_") else pick(kind="service_credit")
        pen = pen or pick()
        if pen and pen.get("pct") is not None:
            return decimal_string(Decimal(str(pen["pct"])) / 100)
        return None
    if name.endswith("_cap_inr"):
        periods = (("monthly", "per_month"), ("lot", "per_lot"), ("per_invoice", "per_invoice"))
        period = next((p for w, p in periods if name.startswith(w)), None)
        want = {"cap_period": period} if period else {}
        if "credit" in name:
            want["kind"] = "service_credit"
        pen = pick(**want) or (None if want else pick())
        if not pen:  # cap period worded differently: accept the only capped remedy on that side
            capped = [
                p
                for p in pens
                if p.get("cap") and (not direction or p.get("direction") == direction)
            ]
            pen = capped[0] if len(capped) == 1 else None
        return _money(pen.get("cap")) if pen else None
    if name.startswith("daily_"):
        pen = pick(basis="per_day")
        return _money(pen.get("amount")) if pen else None
    if "per_incident" in name or name.startswith("per_"):
        pen = pick(basis="per_incident")
        return _money(pen.get("amount")) if pen else None
    return None


def _payment(name, extraction):
    keyword, direction = _keyword(name), _direction(name)
    side = "payer" if direction == "payable" else "payee"
    pays = [
        p
        for p in extraction.get("payments") or []
        if not direction or _COMPANY in (p.get(side) or "").lower()
    ]
    matched = [
        p
        for p in pays
        if not keyword or keyword.search(_text(p, "description", "due_rule", "note"))
    ]
    if not matched and len(pays) == 1:  # unlabelled but the only payment on that side
        matched = pays
    if not matched:
        return None
    if name.endswith("_due"):
        return _utc(matched[0].get("first_due_at"))
    return _money(matched[0].get("amount"))


def _deadline(name, extraction):
    keyword = _keyword(name)
    for item in extraction.get("obligations") or []:
        if keyword and not keyword.search(_text(item, "description", "due_rule", "note")):
            continue
        if item.get("due_at"):
            return _utc(item["due_at"])
    return _payment(name, extraction) if name.endswith("_due") else None


def _period(name, extraction):
    unit = next((u for u in _UNITS if f"_{u}" in f"_{name}"), None)
    if not unit:
        return None
    words = [w for w in name.split(f"_{unit}")[0].split("_") if len(w) > 3]
    for period in extraction.get("periods") or []:
        if period.get("unit") != unit:
            continue
        purpose = str(period.get("purpose", "")).lower()
        if any(w in purpose or purpose in w for w in words):
            value = Decimal(str(period["value"]))
            return int(value) if value == value.to_integral_value() else decimal_string(value)
    return None


def _related(name, extraction):
    links = extraction.get("related_contracts") or []
    if name.startswith("replaces_"):
        target = name.removeprefix("replaces_").upper()
        mentioned = [r for r in links if str(r.get("contract_ref", "")).upper() == target]
        return any(r.get("relation") == "replaces" for r in mentioned) if mentioned else None
    relation = "separate_agreement" if name.startswith("separate_") else "depends_on"
    return next((r["contract_ref"] for r in links if r.get("relation") == relation), None)


def _resolve(name, extraction):
    """Map one golden concept name onto Odin's generic extraction fields, or None."""
    if name.startswith("forum"):
        forum = (extraction.get("forum") or {}).get("value") or ""
        city = re.sub(
            r"\b(courts?|tribunals?|arbitration|seat)\b", "", forum.split(",")[0], flags=re.I
        )
        return " ".join(city.split()) or None
    if name.startswith("notice_"):
        notice = extraction.get("notice") or {}
        return notice.get("address" if name.endswith("address") else "authorized_sender") or None
    if name.endswith("_party_id"):
        capacity = name.removesuffix("_party_id")
        for party in extraction.get("parties") or []:
            if capacity in str(party.get("capacity") or "").lower():
                lowered = party.get("name", "").lower()
                return next((pid for alias, pid in _PARTY_IDS if alias in lowered), None)
        return None
    if name.startswith(("replaces_", "separate_")) or "dependency" in name or "depends_on" in name:
        return _related(name, extraction)
    if name.endswith(("_due", "_at")):
        return _deadline(name, extraction)
    if any(f"_{u}" in f"_{name}" for u in _UNITS):
        return _period(name, extraction)
    if name.endswith(("_rate", "_cap_inr")) or name.startswith(("daily_", "per_")):
        return _penalty(name, extraction)
    if "per_incident" in name:
        return _penalty(name, extraction)
    if name.endswith("_inr"):
        return _payment(name, extraction)
    return None


def thor_score(expected, actual):
    fields = expected.get("field_assertions")
    if not isinstance(fields, list) or not fields:
        raise ValueError("Thor golden requires nonempty field_assertions")
    projected = thor_projection(actual, [f["name"] for f in fields])
    differences = [
        f["name"]
        for f in fields
        if f["name"] not in projected
        or compare_subset(_numeric(f["value"]), _numeric(projected[f["name"]]), f["name"])
    ]
    return (len(fields) - len(differences)) / len(fields), (
        "Typed extraction fields matched"
        if not differences
        else "Missing/unmatched extraction concepts: " + ", ".join(differences)
    )


def _numeric(value):
    """Compare decimal strings by value, so "0.20" matches "0.2"."""
    if isinstance(value, str) and re.fullmatch(r"-?\d+(\.\d+)?", value):
        return decimal_string(value)
    return value


def compare_subset(expected, actual, prefix=""):
    missing = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [prefix or "$output"]
        for key, value in expected.items():
            path = f"{prefix}.{key}" if prefix else key
            if key not in actual:
                missing.append(path)
            else:
                missing.extend(compare_subset(value, actual[key], path))
        return missing
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return [prefix]
        for i, (a, b) in enumerate(zip(expected, actual)):
            missing.extend(compare_subset(a, b, f"{prefix}.{i}"))
        return missing
    return [] if type(expected) is type(actual) and expected == actual else [prefix]


def exact_score(case, execution):
    expected = case.expected_output
    if not isinstance(expected, dict) or "exact" not in expected:
        raise ValueError("Corpus agent case requires expected_output.exact")
    if not expected["exact"]:
        from .checks import MissingEvidence

        raise MissingEvidence(
            "This role has narrative rubrics only; exact assertions are not defined"
        )
    differences = compare_subset(expected["exact"], execution.output)
    return float(not differences), (
        "Exact minimum assertion subset matched"
        if not differences
        else "Missing or mismatched corpus fields: " + ", ".join(differences[:30])
    )
