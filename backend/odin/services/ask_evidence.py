"""Ask-only record provenance and deterministic incident arithmetic. No model calls."""
from __future__ import annotations

import calendar
import hashlib
import json
import re
from typing import Literal
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from odin.core.citations import canonical_span
from odin.core.models import Citation
from pydantic import Field
from odin.retrieval.evidence import facets
from odin.retrieval.hybrid import tokenize


def future_period(question: str, today: date) -> str | None:
    """Actual outage questions need delivered evidence; forecasting questions remain supported."""
    if not re.search(r'uptime|outage|downtime|credits?|\bowe|\breceiv', question, re.I) or re.search(r'hypothetical|assum\w*|what if|forecast|suppose', question, re.I):
        return None
    names = '|'.join(calendar.month_name[1:])
    match = re.search(r'\b(' + names + r')(?:\s+(\d{4}))?\b', question, re.I)
    if not match:
        return None
    month = next(i for i, name in enumerate(calendar.month_name) if name.lower() == match.group(1).lower())
    year = int(match.group(2) or today.year)
    try:
        return f'{calendar.month_name[month]} {year}' if date(year, month, 1) > today else None
    except ValueError:
        return None


class AskCitation(Citation):
    contract_id: str = Field(description='For contract quotes: document ID. For record quotes: exact source_id from source_records.')
    clause_number: str = Field(description='Contract clause number, or the literal record for company/event/ledger citations.')
    source_type: Literal['contract', 'company', 'event', 'ledger'] = Field('contract', description='Must match the source: contract for clauses; otherwise copy source_records.source_type.')


def records_for(context: dict, ids: list[str]) -> list[dict]:
    """Only use records already filtered to the tenant, scenario and simulation date."""
    records = []
    company = context.get('company_context') or {}
    raw = company.get('raw_text') or json.dumps(company, ensure_ascii=False, sort_keys=True)
    if company:
        records.append({'source_id': 'company-context', 'source_type': 'company',
                        'title': 'Company context', 'text': raw})
    for event in context.get('events_so_far', []):
        if event.get('status') in ('rejected', 'quarantined', 'pending'):
            continue
        scope = event.get('contract_ids') or ([event['contract_id']] if event.get('contract_id') else [])
        if scope and not set(scope).intersection(ids):
            continue
        identity = event.get('external_id') or event.get('id')
        if not identity:
            continue
        body = event.get('raw') or event.get('description') or ''
        # Official drops store the original JSON line. Cite the decoded body, so
        # line breaks remain source text rather than literal JSON escape sequences.
        try:
            parsed = json.loads(body)
            if isinstance(parsed, dict) and isinstance(parsed.get('body'), str):
                body = parsed['body']
        except (ValueError, TypeError):
            pass
        records.append({'source_id': str(identity), 'source_type': 'event',
                        'title': event.get('subject') or str(identity),
                        'date': event.get('occurred_at'),
                        'text': f"{event.get('subject', '')}\n{event.get('occurred_at', '')}\n{body}"})
    for row in context.get('ledger', []):
        if row.get('contract_id') and row['contract_id'] not in ids:
            continue
        body = json.dumps(row, ensure_ascii=False, sort_keys=True)
        identity = 'ledger-' + hashlib.sha256(body.encode()).hexdigest()[:12]
        records.append({'source_id': identity, 'source_type': 'ledger',
                        'title': row.get('reference') or 'Payment ledger row',
                        'date': row.get('date'), 'text': body})
    return records


def verify_record(citation: AskCitation, records: list[dict]) -> AskCitation:
    record = next((r for r in records if r['source_id'] == citation.contract_id
                   and r['source_type'] == citation.source_type), None)
    quote = canonical_span(citation.quote, record['text']) if record else None
    return citation.model_copy(update={'verified': bool(quote), 'quote': quote or citation.quote,
                                      'clause_number': 'record', 'ref': record['title'] if record else None,
                                      'page': None, 'version': None})


def select_records(question: str, records: list[dict], limit: int = 12) -> list[dict]:
    """Keep explicit IDs and diverse decision dependencies; avoid dumping the whole ledger."""
    selected = [r for r in records if r['source_type'] == 'company' or re.search(r'(?<!\w)' + re.escape(r['source_id']) + r'(?!\w)', question, re.I)]
    queries = [question, *facets(question)]
    for query in queries:
        words = set(tokenize(query))
        ranked = sorted(records, key=lambda r: -len(words & set(tokenize(r['text']))))
        for record in ranked[:3]:
            if record not in selected and words & set(tokenize(record['text'])):
                selected.append(record)
    return selected[:limit]


def incident_calculations(records: list[dict]) -> list[dict]:
    """Compute only explicit complete-unavailability intervals; never infer SLA eligibility.

    Merge overlapping intervals before summing. Results are observed downtime, not a
    guarantee of complete monthly logs or a decision about contractual exclusions.
    """
    months = {}
    for record in records:
        body = record['text']
        if record['source_type'] != 'event' or not re.search(r'complete unavailability', body, re.I):
            continue
        times = [re.search(r'Incident ' + label + r':\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})', body, re.I)
                 for label in ('start', 'end')]
        if not all(times):
            continue
        start, end = [datetime.strptime(t.group(1), '%Y-%m-%d %H:%M') for t in times]
        if end <= start:
            continue
        while start < end:
            boundary = datetime(start.year + (start.month == 12), start.month % 12 + 1, 1)
            stop = min(boundary, end)
            months.setdefault((start.year, start.month), []).append((start, stop, record['source_id']))
            start = stop
    results = []
    for (year, month), intervals in sorted(months.items()):
        merged = []
        for start, end, _ in sorted(intervals):
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
            else:
                merged.append((start, end))
        minutes = sum((end - start).total_seconds() / 60 for start, end in merged)
        total = calendar.monthrange(year, month)[1] * 1440
        results.append({'month': f'{year}-{month:02}', 'observed_downtime_minutes': minutes,
                        'calendar_minutes': total, 'uptime_if_no_other_countable_downtime': round((total-minutes)/total*100, 6),
                        'source_ids': sorted({r[2] for r in intervals}),
                        'limitation': 'Observed complete outages only; verify exclusions and completeness before treating as final monthly uptime.'})
    return results


def deadline_calculations(passages: list[dict], records: list[dict], incidents: list[dict]) -> list[dict]:
    """Date arithmetic from explicit month-end request clauses, with source IDs.

    Keep original/amended windows separate: arithmetic does not decide precedence.
    """
    results = []
    for incident in incidents:
        year, month = map(int, incident['month'].split('-'))
        end = date(year, month, calendar.monthrange(year, month)[1])
        for passage in passages:
            match = re.search(r'within\s+(?:[a-z-]+\s+)*?(?:\((\d+)\)|(\d+))\s*days\s+after\s+the\s+end\s+of\s+the\s+calendar\s+month', passage['text'], re.I)
            if not match:
                continue
            days = int(match.group(1) or match.group(2))
            deadline = end + timedelta(days=days)
            dates = []
            for record in records:
                if record['source_type'] != 'event' or not re.search(r'credit request', record['title'], re.I):
                    continue
                try:
                    submitted = date.fromisoformat(str(record.get('date', ''))[:10])
                except ValueError:
                    continue
                dates.append({'source_id': record['source_id'], 'record_date': str(submitted),
                              'days_after_month_end': (submitted-end).days,
                              'days_after_deadline': (submitted-deadline).days,
                              'note': 'Check requesting party and claimed month before applying this record.'})
            results.append({'month': incident['month'], 'month_end': str(end),
                            'contract_id': passage['contract_id'], 'clause_number': passage['clause_number'],
                            'request_window_days': days, 'deadline': str(deadline), 'request_records': dates})
    return results


def sla_calculations(passages: list[dict], incidents: list[dict]) -> list[dict]:
    """Check explicit uptime commitments and flat credit arithmetic at the stated fee.

    Conditional exposure only: request conditions, fee changes and amendments remain
    visible evidence that must be applied before calling an amount payable.
    """
    results = []
    for target in passages:
        if not re.search(r'uptime commitment', target.get('heading', ''), re.I):
            continue
        percent = re.search(r'(\d+(?:\.\d+)?)%', target['text'])
        if not percent:
            continue
        threshold = float(percent.group(1))
        family = [p for p in passages if p['contract_id'] == target['contract_id']]
        fee = next((re.search(r'Monthly Fee:\s*\$([\d,]+(?:\.\d+)?)', p['text'], re.I)
                    for p in family if re.search(r'Monthly Fee:\s*\$([\d,]+(?:\.\d+)?)', p['text'], re.I)), None)
        credit_source = next((p for p in family if not re.search(r'not exceed|maximum|credit cap', p['text'], re.I)
                              and re.search(r'percent\s*\(\d+(?:\.\d+)?%\)\s+of\s+the\s+Monthly Fee', p['text'], re.I)), None)
        credit = re.search(r'percent\s*\((\d+(?:\.\d+)?)%\)\s+of\s+the\s+Monthly Fee', credit_source['text'], re.I) if credit_source else None
        cap_source = next((p for p in family if re.search(r'not exceed\s+(?:[a-z-]+\s+)*percent\s*\(\d+(?:\.\d+)?%\)\s+of\s+the\s+Monthly Fee', p['text'], re.I)), None)
        for incident in incidents:
            observed = incident['uptime_if_no_other_countable_downtime']
            met = observed >= threshold
            item = {'contract_id': target['contract_id'], 'clause_number': target['clause_number'],
                    'month': incident['month'], 'observed_uptime': observed,
                    'target_percent': threshold, 'target_met': met,
                    'comparison': f'{observed:.3f}% ' + ('>=' if met else '<') + f' {threshold}%',
                    'note': 'Observed outages only. Nominal exposure; verify active period, amendments and claim conditions.'}
            if fee and credit:
                amount = Decimal(fee.group(1).replace(',', ''))
                rate = Decimal(credit.group(1))
                applied_rate = rate
                if cap_source:
                    cap = Decimal(re.search(r'percent\s*\((\d+(?:\.\d+)?)%\)', cap_source['text'], re.I).group(1))
                    applied_rate = min(rate, cap)
                    item.update(credit_cap_percent=float(cap), cap_clause_number=cap_source['clause_number'])
                item.update(stated_monthly_fee=float(amount), flat_credit_percent=float(rate),
                            flat_credit_clause_number=credit_source['clause_number'],
                            nominal_credit=0 if met else float((amount*applied_rate/100).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)))
            results.append(item)
    return results


def invalid_comparison(text: str) -> bool:
    match = re.search(r'(\d+(?:\.\d+)?)%[^%\n]{0,150}?\b(exceed\w*|above|below|less than|greater than)\b[^%\n]{0,150}?(\d+(?:\.\d+)?)%', text, re.I)
    if not match:
        return False
    left, right = float(match.group(1)), float(match.group(3))
    greater = match.group(2).lower().startswith(('exceed', 'above', 'greater'))
    return not (left > right if greater else left < right)


def calculation_claims(question: str, context: dict, passages: list[dict], records: list[dict]) -> list[dict]:
    """Expose checked arithmetic with its source quotes, independent of generated prose."""
    if not re.search(r'uptime|outage|downtime', question, re.I) or not any(q.startswith('uptime measurement') for q in facets(question)):
        return []
    claims = []
    for calculation in context.get('sla_calculations', []):
        cid = calculation['contract_id']
        family = [p for p in passages if p['contract_id'] == cid]
        target = next((p for p in family if p['clause_number'] == calculation['clause_number']), None)
        if not target:
            continue
        citations = []
        def cite(passage, pattern):
            found = re.search(pattern, passage['text'], re.I)
            if found:
                citations.append({'contract_id': cid, 'clause_number': passage['clause_number'],
                                  'quote': found.group(), 'source_type': 'contract',
                                  'version': passage.get('version')})
        cite(target, r'[^.]*\(\d+(?:\.\d+)?%\)[^.]*\.')
        if not citations:
            continue
        incident = next((r for r in context.get('incident_calculations', []) if r['month'] == calculation['month']), None)
        if incident:
            for identity in incident['source_ids']:
                record = next((r for r in records if r['source_id'] == identity), None)
                if record:
                    span = re.search(r'Incident start:[\s\S]*?Duration:\s*\d+\s*minutes', record['text'], re.I)
                    if span:
                        citations.append({'contract_id': identity, 'clause_number': 'record',
                                          'quote': span.group(), 'source_type': record['source_type']})
        if not any(c['source_type'] == 'event' for c in citations):
            continue
        text = (f"{cid}: uptime {calculation['observed_uptime']:.3f}%; "
                f"{calculation['target_percent']:g}% target {'met' if calculation['target_met'] else 'missed'}. ")
        if 'nominal_credit' in calculation:
            fee_source = next((p for p in family if re.search(r'Monthly Fee:\s*\$', p['text'], re.I)), None)
            rate_source = next((p for p in family if p['clause_number'] == calculation['flat_credit_clause_number']), None)
            if fee_source and rate_source:
                cite(fee_source, r'Monthly Fee:\s*\$[\d,]+(?:\.\d+)?')
                cite(rate_source, r'percent\s*\(\d+(?:\.\d+)?%\)\s+of\s+the\s+Monthly Fee')
                if 'cap_clause_number' in calculation:
                    cap_source = next(p for p in family if p['clause_number'] == calculation['cap_clause_number'])
                    cite(cap_source, r'not exceed\s+(?:[a-z-]+\s+)*percent\s*\(\d+(?:\.\d+)?%\)\s+of\s+the\s+Monthly Fee')
                text = (f"{cid}: uptime {calculation['observed_uptime']:.3f}%; "
                        f"nominal credit ${calculation['nominal_credit']:,.2f}; eligibility unverified.")
        claims.append({'text': text.strip(), 'basis': 'clause', 'citations': citations})
    return claims


def incorrect_deadline(text: str, citations: list, context: dict) -> bool:
    """Reject explicit deadline dates that contradict the cited window's calculation."""
    if not re.search(r'deadline', text, re.I):
        return False
    cited = {c.contract_id for c in citations if c.source_type == 'contract'}
    windows = [r for r in context.get('deadline_calculations', []) if r['contract_id'] in cited]
    for window in windows:
        if not re.search(r'\b' + str(window['request_window_days']) + r'[-\s]+days?\b', text, re.I):
            continue
        allowed = {window['deadline'], window['month_end']}
        allowed.update(r['record_date'] for r in window['request_records'])
        for match in re.finditer(r'\b([A-Z][a-z]+ \d{1,2},? \d{4})\b', text):
            try:
                mentioned = datetime.strptime(match.group(1).replace(',', ''), '%B %d %Y').date().isoformat()
            except ValueError:
                continue
            if mentioned not in allowed:
                return True
    return False


def coverage_claims(question: str, passages: list[dict], records: list[dict]) -> list[dict]:
    """Connect an explicit expiry record to the conditional lapse rule, without inventing renewal status."""
    if not re.search(r'insurance|default|breach|complian', question, re.I):
        return []
    company = next((r for r in records if r['source_type'] == 'company'), None)
    if not company:
        return []
    expiry = re.search(r'Expiry:\s*([A-Z][a-z]+ \d{1,2}, \d{4})', company['text'])
    if not expiry:
        return []
    for passage in passages:
        rule = re.search(r'A lapse in required\s+insurance coverage constitutes a material breach of this Agreement\.', passage['text'], re.I)
        if rule:
            return [{'text': f"Company records list insurance expiry on {expiry.group(1)}; expiry alone does not prove lapse. "
                     f"If required coverage lapsed without renewal or replacement, {passage['contract_id']} "
                     'treats it as material breach.',
                     'basis': 'clause', 'citations': [
                         {'contract_id': company['source_id'], 'clause_number': 'record', 'source_type': 'company', 'quote': expiry.group()},
                         {'contract_id': passage['contract_id'], 'clause_number': passage['clause_number'],
                          'source_type': 'contract', 'quote': rule.group(), 'version': passage.get('version')}]}]
    return []
