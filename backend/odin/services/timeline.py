"""Norns' deterministic engine (FR3). Pure Python on top of Thor's extraction — so the time slider
recomputes instantly and results are reproducible (NFR6). The LLM part of Norns only interprets
relative due rules (see agents/norns.py)."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Optional

import holidays
from dateutil.relativedelta import relativedelta

from odin.core.models import (Citation, ContractExtraction, Event, Exposure, ExposureLine, Money, TimelineEntry,
                              Violation)

FREQ_MONTHS = {"monthly": 1, "quarterly": 3, "half_yearly": 6, "annual": 12}
LAW_TO_COUNTRY = [("india", "IN"), ("delaware", "US"), ("new york", "US"), ("california", "US"), ("united states", "US"),
                  ("england", "GB"), ("united kingdom", "GB"), ("singapore", "SG"), ("germany", "DE"), ("uae", "AE")]


@lru_cache(maxsize=16)
def _hol(country: str):
    try:
        return holidays.country_holidays(country)
    except (KeyError, NotImplementedError):
        return holidays.country_holidays("IN")


def country_for(law: str) -> str:
    l = (law or "").lower()
    return next((c for k, c in LAW_TO_COUNTRY if k in l), "IN")


def prev_business_day(d: date, country: str) -> date:
    """Notice 'at least N days before' must land on a working day → roll backwards."""
    h = _hol(country)
    while d.weekday() >= 5 or d in h:
        d -= timedelta(days=1)
    return d


def _eid(*parts) -> str:
    return "tl-" + hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:12]


def fmt_date(d: date) -> str:
    """Human date used in all generated prose ("12 Nov 2026") — same format as the UI."""
    return f"{d.day} {d:%b %Y}"


def _status(d: date, now: date) -> str:
    if d < now:
        return "past"
    return "due" if (d - now).days <= 7 else "upcoming"


@dataclass
class ContractInputs:
    contract_id: str
    extraction: ContractExtraction
    effective_date: Optional[date] = None
    governing_law: str = ""
    events: list[Event] = field(default_factory=list)
    violations: list[Violation] = field(default_factory=list)
    actions: list[dict] = field(default_factory=list)     # approved / sent ActionDraft dicts
    currency: str = "INR"
    owners: dict = field(default_factory=dict)            # timeline id → owner
    company_names: list[str] = field(default_factory=list)

    def incoming(self, payee: str) -> bool:
        """Money paid TO the company is a receivable, not exposure."""
        p = (payee or "").lower()
        return bool(p) and any(n and (n.lower() in p or p in n.lower()) for n in self.company_names)


@dataclass
class ContractTimeline:
    contract_id: str
    entries: list[TimelineEntry]
    exposure: Exposure
    term_end: Optional[date]
    notice_deadline: Optional[date]


def _cite(f) -> Optional[Citation]:
    return f.citation if f is not None else None


def compute(ci: ContractInputs, now: date, horizon_months: int = 12, apply_actions: bool = True) -> ContractTimeline:
    x = ci.extraction
    cur = ci.currency
    country = country_for(ci.governing_law or (x.governing_law.value if x.governing_law else ""))
    entries: list[TimelineEntry] = []
    lines: list[ExposureLine] = []
    assumptions: list[str] = []
    acts = {a.get("kind") for a in ci.actions} if apply_actions else set()
    horizon = now + relativedelta(months=horizon_months)

    eff = (x.term.effective_date if x.term and x.term.effective_date else None) or ci.effective_date
    term_months = x.term.term_months if x.term else None
    # "24 months from 1 Jan 2025" ends 31 Dec 2026 (last day inclusive)
    # computed beats LLM arithmetic (models drift by a day); explicit end_date only when no term length
    end = (eff + relativedelta(months=term_months) - timedelta(days=1) if eff and term_months else None) or (
        x.term.end_date if x.term and x.term.end_date else None)

    # ── term / renewal / notice ──
    notice_deadline = None
    rn = x.renewal
    if end:
        if rn and rn.auto_renew and rn.renewal_period_months:
            k = 0
            while end < now and k < 50:      # contract silently rolled over
                entries.append(TimelineEntry(id=_eid(ci.contract_id, "renewed", end), contract_id=ci.contract_id,
                                             date=end, kind="renewal", title="Auto-renewed", status="past",
                                             citation=_cite(rn)))
                end = end + relativedelta(months=rn.renewal_period_months)
                k += 1
        entries.append(TimelineEntry(id=_eid(ci.contract_id, "expiry", end), contract_id=ci.contract_id, date=end,
                                     kind="expiry", title="Current term ends", status=_status(end, now),
                                     citation=_cite(x.term)))
        if rn and rn.notice_days is not None:
            notice_deadline = prev_business_day(end - timedelta(days=rn.notice_days), country)
            sent = "non_renewal_notice" in acts or "termination_notice" in acts
            st = "done" if sent else ("missed" if notice_deadline < now else _status(notice_deadline, now))
            entries.append(TimelineEntry(
                id=_eid(ci.contract_id, "notice", notice_deadline), contract_id=ci.contract_id, date=notice_deadline,
                kind="notice_deadline", status=st, citation=_cite(rn),
                title=f"Last day to send non-renewal notice ({rn.notice_days} days before {fmt_date(end)}, "
                      f"business-day adjusted, {country})"))
            if rn.auto_renew and not sent:
                commit = rn.renewal_value or _annualised(ci, rn.renewal_period_months or 12, cur)
                if commit:
                    entries.append(TimelineEntry(id=_eid(ci.contract_id, "renew", end), contract_id=ci.contract_id,
                                                 date=end, kind="renewal", status=_status(end, now), amount=commit,
                                                 title=f"Auto-renewal for {rn.renewal_period_months} months",
                                                 citation=_cite(rn)))
                    lines.append(ExposureLine(contract_id=ci.contract_id, label="Locked-in renewal if no notice sent",
                                              amount=commit, month=end.strftime("%Y-%m"), clause_type="renewal",
                                              citation=_cite(rn)))
                    assumptions.append(f"{ci.contract_id}: no non-renewal notice is sent before {fmt_date(notice_deadline)}.")

    # ── payments ──
    missed_dates = sorted(e.occurred_at.date() for e in ci.events if e.event_type in ("PAYMENT_LATE", "PAYMENT_MISSED"))
    paid_dates = sorted(e.occurred_at.date() for e in ci.events if e.event_type == "PAYMENT_MADE")
    for i, p in enumerate(x.payments):
        if not p.amount:
            continue
        step = FREQ_MONTHS.get(p.frequency)
        first = p.first_due or (p.first_due_at.date() if p.first_due_at else None) or eff
        if not first:
            assumptions.append(f"{ci.contract_id}: payment '{p.description}' has no first due date — not scheduled.")
            continue
        dates = [first] if not step else []
        if step:
            d, n = first, 0
            last = horizon
            if end:   # payments stop at term end (plus one renewal period if it auto-renews)
                renew = rn.renewal_period_months if rn and rn.auto_renew and rn.renewal_period_months else 0
                last = min(horizon, end + relativedelta(months=renew))
            while d <= last and n < 120:
                dates.append(d)
                d = first + relativedelta(months=step * (n + 1))
                n += 1
        incoming = ci.incoming(p.payee)
        for d in dates:
            st = _status(d, now)
            missed = any(abs((m - d).days) <= 45 and m >= d for m in missed_dates)
            paid = any(abs((m - d).days) <= 45 and m >= d for m in paid_dates)
            if missed and not paid and "payment_instruction" not in acts:
                st = "missed"
            elif paid:
                st = "done"
            eid = _eid(ci.contract_id, "pay", i, d)
            label = p.description or (f"Receivable from {p.payer}" if incoming else f"Payment to {p.payee}")
            entries.append(TimelineEntry(id=eid, contract_id=ci.contract_id, date=d, kind="payment", status=st,
                                         amount=p.amount, title=("Receivable: " if incoming else "") + label,
                                         citation=p.citation, owner=ci.owners.get(eid, ""),
                                         due_at=datetime.combine(d, p.first_due_at.timetz()) if p.first_due_at else None))
            if incoming:
                continue
            if d >= now and d <= horizon:
                lines.append(ExposureLine(contract_id=ci.contract_id, label=f"Scheduled: {p.description or 'payment'}",
                                          amount=p.amount, month=d.strftime("%Y-%m"), clause_type="payment",
                                          citation=p.citation))
            if st == "missed":
                months_late = max(1, (now - d).days // 30)
                fee = 0.0
                if p.late_fee_pct_per_month:
                    fee += p.amount.amount * p.late_fee_pct_per_month / 100 * months_late
                if p.late_fee_flat:
                    fee += p.late_fee_flat.amount
                if fee:
                    entries.append(TimelineEntry(id=_eid(ci.contract_id, "latefee", i, d), contract_id=ci.contract_id,
                                                 date=max(d, now), kind="penalty_trigger", status="due",
                                                 amount=Money(amount=round(fee, 2), currency=p.amount.currency),
                                                 title=f"Late-payment charge accruing ({months_late} mo)",
                                                 citation=p.citation))
                    lines.append(ExposureLine(contract_id=ci.contract_id, label="Late-payment charges accrued",
                                              amount=Money(amount=round(fee, 2), currency=p.amount.currency),
                                              month=now.strftime("%Y-%m"), clause_type="penalty", citation=p.citation))

    # ── obligations with dates ──
    for i, o in enumerate(x.obligations):
        due = o.due_date or (o.due_at.date() if o.due_at else None)
        if due:
            entries.append(TimelineEntry(id=_eid(ci.contract_id, "obl", i, due), contract_id=ci.contract_id,
                                         date=due, kind="obligation", status=_status(due, now), due_at=o.due_at,
                                         title=f"{o.owner}: {o.description}"[:160], citation=o.citation,
                                         owner=ci.owners.get(_eid(ci.contract_id, "obl", i, due), "")))

    # ── violations from events (Heimdall) ──
    worst_extra: list[ExposureLine] = []
    for v in ci.violations:
        if v.status == "dismissed" or not v.exposure:
            continue
        line = ExposureLine(contract_id=ci.contract_id, label=f"{v.breach_type} ({v.status})", amount=v.exposure,
                            month=now.strftime("%Y-%m"), clause_type="penalty",
                            citation=Citation(contract_id=v.contract_id, clause_number=v.clause_number, quote=v.quote,
                                              page=v.page, version=v.version, verified=True))
        entries.append(TimelineEntry(id=_eid(ci.contract_id, "viol", v.id), contract_id=ci.contract_id, date=now,
                                     kind="penalty_trigger", status="due", amount=v.exposure,
                                     title=f"Breach exposure: {v.breach_type}", citation=line.citation))
        (lines if v.status == "confirmed" else worst_extra).append(line)

    # ── worst case: every un-triggered penalty with a number fires once ──
    for pen in x.penalties:
        amt = pen.amount or pen.cap
        if amt:
            worst_extra.append(ExposureLine(contract_id=ci.contract_id, label=f"Penalty if triggered: {pen.trigger}"[:120],
                                            amount=amt, month=(end or horizon).strftime("%Y-%m"), clause_type="penalty",
                                            citation=pen.citation))
    if worst_extra:
        assumptions.append(f"{ci.contract_id}: worst case assumes every quantified penalty fires once and suspected "
                           f"breaches are upheld.")

    expected = sum(l.amount.amount for l in lines)
    worst = expected + sum(l.amount.amount for l in worst_extra)
    entries.sort(key=lambda e: e.date)
    return ContractTimeline(ci.contract_id, entries,
                            Exposure(as_of=now, expected=round(expected, 2), worst_case=round(worst, 2), currency=cur,
                                     lines=lines + worst_extra, assumptions=assumptions),
                            end, notice_deadline)


def _annualised(ci: ContractInputs, months: int, cur: str) -> Optional[Money]:
    """Outgoing spend over `months` (renewal lock-in when no explicit renewal value)."""
    total = 0.0
    ccy = cur
    for p in ci.extraction.payments:
        if p.amount and p.frequency in FREQ_MONTHS and not ci.incoming(p.payee):
            total += p.amount.amount * months / FREQ_MONTHS[p.frequency]
            ccy = p.amount.currency
    return Money(amount=round(total, 2), currency=ccy) if total else None


def counterfactual(ci: ContractInputs, now: date, action_kind: str) -> dict:
    """Exposure if this action is taken vs not (feature: counterfactual action value)."""
    base = compute(ContractInputs(**{**ci.__dict__, "actions": []}), now)
    with_act = compute(ContractInputs(**{**ci.__dict__, "actions": [{"kind": action_kind}]}), now)
    return {"without_action": base.exposure.worst_case, "with_action": with_act.exposure.worst_case,
            "avoided": round(base.exposure.worst_case - with_act.exposure.worst_case, 2),
            "currency": base.exposure.currency}
