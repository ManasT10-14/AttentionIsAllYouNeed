"""Exact, typed corpus assertions. No model inference or oracle-driven filling."""

import re
from decimal import Decimal


def decimal_string(value):
    return format(Decimal(str(value)).normalize(), "f")


def thor_projection(extraction):
    """Explicit mappings from Odin's actual schema; unsupported concepts stay absent."""
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
    return result


def thor_score(expected, actual):
    fields = expected.get("field_assertions")
    if not isinstance(fields, list) or not fields:
        raise ValueError("Thor golden requires nonempty field_assertions")
    projected = thor_projection(actual)
    differences = [
        f["name"]
        for f in fields
        if f["name"] not in projected or compare_subset(f["value"], projected[f["name"]], f["name"])
    ]
    return (len(fields) - len(differences)) / len(fields), (
        "Typed extraction fields matched"
        if not differences
        else "Missing/unmatched extraction concepts: " + ", ".join(differences)
    )


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
