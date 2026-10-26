"""Scoped contract Q&A with bounded history and independently verified answer claims."""
from __future__ import annotations

import re
from typing import Literal

from odin.agents.base import j, prompt
from odin.core import citations
from odin.core.budget import BudgetExceeded
from odin.core.context import run_ctx
from odin.core.models import Citation
from odin.core.telemetry import traced
from odin.db import repo
from odin.evals import scored
from odin.llm.call import LLMFailure, structured
from odin.retrieval import evidence
from odin.services import insights
from pydantic import BaseModel, Field

_PORTFOLIO = re.compile(r'\b(portfolio|counterparties|overview|total exposure|upcoming|attention|alerts?)\b|\b(?:which|list|what|how many)\b.*\b(?:contracts|agreements)\b|\brenew\w*\s+(?:next|this|in|by)\b', re.I)
_CLAUSE = re.compile(r'\b(clauses?|sections?|liabilit\w*|caps?|cure|breach|terminat\w*|indemni\w*|penalt\w*|notice period|obligations?|exceptions?|force majeure|conflict\w*|precedence|governing law|payment terms?)\b', re.I)
_FOLLOWUP = re.compile(r'\b(it|its|that|those|these|they|them|same|also|what about|how about)\b', re.I)
_GENERIC = {'agreement', 'contract', 'services', 'service', 'master', 'terms', 'the', 'and', 'of', 'for', 'software'}
_SKIP_KEYS = {'bboxes'}


class AnswerClaim(BaseModel):
    text: str
    basis: Literal['portfolio', 'clause']
    citations: list[Citation] = Field(default_factory=list)


class AnswerDraft(BaseModel):
    claims: list[AnswerClaim]
    missing: list[str] = Field(default_factory=list)


def classify(question: str) -> str:
    portfolio = bool(_PORTFOLIO.search(question))
    clause = bool(_CLAUSE.search(question))
    if clause:
        return 'mixed' if portfolio else 'clause'
    if re.search(r'\bsummari[sz]e\b', question, re.I):
        return 'mixed'
    if portfolio:
        legal = re.search(r'\b(allow\w*|prohibit\w*|require\w*|rights?|consent|subcontract\w*|assign\w*|disclos\w*|restrict\w*)\b', question, re.I)
        structured = re.search(r'\b(renew\w*|expir\w*|deadlines?|attention|alerts?|counterparties|overview|exposure|portfolio)\b|\bhow many (?:uploaded )?(?:contracts|agreements)\b', question, re.I)
        inventory = re.fullmatch(r'(?:what (?:contracts|agreements) do we have|list (?:contracts|agreements))\??', question.strip(), re.I)
        return 'portfolio' if not legal and (structured or inventory) else 'mixed'
    return 'clause'


def _mentioned(question: str, contracts) -> list[str]:
    """Exact ID boundaries, full titles, or unique distinctive title words."""
    q = question.casefold()
    words = {c.contract_id: set(re.findall(r'[a-z]{4,}', (c.title or '').lower())) - _GENERIC for c in contracts}
    explicit = [c.contract_id for c in contracts if re.search(r'(?<![\w-])' + re.escape(c.contract_id) + r'(?![\w-])', question, re.I)]
    if explicit:
        return explicit
    found = []
    for c in contracts:
        unique = words[c.contract_id] - set().union(*(v for k, v in words.items() if k != c.contract_id))
        if (c.title and c.title.casefold() in q) or any(re.search(r'\b' + re.escape(w) + r'\b', q) for w in unique):
            found.append(c.contract_id)
    return found


def _slim(x):
    if isinstance(x, dict):
        return {k: _slim(v) for k, v in x.items() if k not in _SKIP_KEYS and v not in (None, [], '')}
    if isinstance(x, list):
        return [_slim(v) for v in x]
    return x


def resolve_scope(question: str, contract_ids: list[str] | None, history: list[dict], contracts):
    known = {c.contract_id.casefold(): c.contract_id for c in contracts}
    explicit = list(dict.fromkeys(s.strip() for s in (contract_ids or []) if s.strip()))
    invalid = [s for s in explicit if s.casefold() not in known]
    if invalid:
        return [], question, invalid
    mentioned = _mentioned(question, contracts)
    ids = [known[s.casefold()] for s in explicit] if explicit else mentioned
    resolved = question
    if history and _FOLLOWUP.search(question):
        prior = history[-1]
        if not ids:
            prior_ids = prior.get('contract_ids', [])
            if prior_ids and any(c.casefold() not in known for c in prior_ids):
                return [], resolved, [c for c in prior_ids if c.casefold() not in known]
            ids = [known[c.casefold()] for c in prior_ids if c.casefold() in known]
            ids = ids or _mentioned(prior.get('question', ''), contracts)
        # Only user questions are carried forward, never previous generated answers as evidence.
        resolved = f"Previous question (context only): {prior.get('question', '')[:2000]}\nCurrent question: {question}"
    return ids or [c.contract_id for c in contracts], resolved, []


def portfolio_context(question: str, contract_ids: list[str] | None = None, contracts=None) -> tuple[dict, list[str]]:
    now = repo.sim_now()
    cs = repo.contracts() if contracts is None else contracts
    ment = _mentioned(question, cs)
    scope = set(contract_ids) if contract_ids is not None else None
    cs = [c for c in cs if scope is None or c.contract_id in scope]
    ex = insights.exposure_summary(now)
    exp = {p['contract_id']: p for p in ex['contracts'] if any(c.contract_id == p['contract_id'] for c in cs)}
    rows, parties = [], {}
    totals = {}
    for c in cs:
        e = exp.get(c.contract_id, {})
        rows.append({'contract_id': c.contract_id, 'title': c.title, 'type': c.type, 'status': c.status,
                     'parties': [f"{p.get('name')} ({p.get('role')})" for p in c.meta.get('parties', [])],
                     'effective_date': c.meta.get('effective_date'), 'governing_law': c.meta.get('governing_law'),
                     'term_end': e.get('term_end'), 'notice_deadline': e.get('notice_deadline'),
                     'expected_exposure': e.get('expected'), 'worst_case_exposure': e.get('worst_case'),
                     'currency': e.get('currency', ex.get('currency')), 'analysed': c.contract_id in exp})
        if e:
            currency = e.get('currency', ex.get('currency', 'INR'))
            total = totals.setdefault(currency, {'expected': 0, 'worst_case': 0})
            total['expected'] += e.get('expected', 0)
            total['worst_case'] += e.get('worst_case', 0)
        for p in c.meta.get('parties', []):
            if p.get('role') != 'company' and p.get('name'):
                parties.setdefault(p['name'], []).append(c.contract_id)
    detail = {}
    for cid in (contract_ids or ment)[:6]:
        x = insights.extraction(cid)
        if x:
            detail[cid] = _slim(x.model_dump(mode='json'))
    selected = {c.contract_id for c in cs}
    alerts = [a for a in insights.alerts(now) if a.get('contract_id') in selected]
    ctx = {'today': now.isoformat(), 'contract_count': len(cs), 'contracts': rows,
           'exposure_by_currency': totals, 'exposure_note': ex['note'],
           'unanalysed_contracts': [c.contract_id for c in cs if c.contract_id not in exp],
           'counterparties': [{'name': name, 'contracts': ids} for name, ids in parties.items()],
           'open_alerts': [_slim({k: a.get(k) for k in ('contract_id', 'title', 'severity', 'kind', 'due_date', 'why')}) for a in alerts[:30]],
           'omitted_alert_count': max(0, len(alerts) - 30),
           'extracted_fields_for_mentioned_contracts': detail}
    return ctx, ment


def deterministic(question: str, ctx: dict) -> str | None:
    q = re.sub(r'[?.!]+$', '', question.strip().lower())
    if re.fullmatch(r'(?:how many|count)(?: uploaded)? (?:contracts|agreements)(?: (?:do we have|are there|in (?:the |our )?portfolio))?', q):
        return f"There are {ctx['contract_count']} uploaded agreements in the selected scope."
    if q in {'what contracts do we have', 'list contracts', 'list agreements', 'what agreements do we have'}:
        return '\n'.join(f"- {r['contract_id']}: {r['title']}" for r in ctx['contracts'])
    if q in {'who are our counterparties', 'list counterparties'}:
        return '\n'.join(f"- {p['name']}: {', '.join(p['contracts'])}" for p in ctx['counterparties']) or 'No counterparty names are recorded for this scope.'
    if q in {'what is our total exposure', 'what is the total exposure', 'total exposure'}:
        lines = [f"{currency}: expected {v['expected']:,.2f}; worst case {v['worst_case']:,.2f}." for currency, v in ctx['exposure_by_currency'].items()]
        if not lines:
            return None
        if ctx['unanalysed_contracts']:
            lines.append('Not yet quantified: ' + ', '.join(ctx['unanalysed_contracts']) + '.')
        return '\n'.join(lines) + '\n' + ctx['exposure_note']
    return None


def verified_claims(draft: AnswerDraft, kind: str, ids: list[str]):
    supported, rejected = [], []
    for claim in draft.claims:
        # A clause question can never bypass evidence checks by labelling a claim portfolio.
        needs_citation = claim.basis == 'clause' or kind == 'clause' or bool(_CLAUSE.search(claim.text))
        checked = citations.verify_all([c for c in claim.citations if c.contract_id in ids])
        valid = [c for c in checked if c.verified]
        if needs_citation and (not valid or len(valid) != len(claim.citations)):
            rejected.append(claim)
        elif claim.text.strip():
            supported.append(claim.model_copy(update={'citations': valid}))
    return supported, rejected


def result(answer='', *, kind, ids, sources, passages=None, reason=None, warnings=None, cits=None, missing=None):
    missing = missing or []
    return {'answer': answer, 'kind': kind, 'scope_ids': ids, 'sources': sources,
            'passages': passages or [], 'citations': [c.model_dump(mode='json') for c in (cits or [])],
            'insufficient_evidence': not bool(answer), 'status': 'partial' if answer and missing else 'answered' if answer else 'unanswered',
            'reason': reason, 'missing': missing, 'warnings': warnings or []}


@scored('ask')
@traced('odin:ask')
def ask(company_id: str, question: str, contract_ids: list[str] | None = None, history: list[dict] | None = None) -> dict:
    with run_ctx(company_id, agent='ask'):
        contracts = repo.contracts()
        ids, resolved, invalid = resolve_scope(question, contract_ids, (history or [])[-4:], contracts)
        kind = classify(resolved)
        if invalid:
            return result(kind=kind, ids=[], sources=[], reason='invalid_scope', missing=['Unknown contract IDs: ' + ', '.join(invalid)])
        if not contracts:
            return result(kind=kind, ids=[], sources=[], reason='no_contracts', missing=['No contracts have been uploaded yet.'])
        pack_scope = any(c.meta.get("canonical") == "txt" for c in contracts if c.contract_id in ids)
        if pack_scope:
            # Include governing terms and amendments as explicit, visible source scope.
            rels = insights.doc_relations()
            expanded = set(ids)
            for _ in range(len(contracts)):
                before = set(expanded)
                for rel in rels:
                    a, b, kind = rel.get("from_doc"), rel.get("to_doc"), rel.get("relation")
                    if a in expanded or (b in expanded and kind in ("amends", "addendum_to")):
                        expanded.update((a, b))
                if expanded == before:
                    break
            ids = [c.contract_id for c in contracts if c.contract_id in expanded]
        ctx, _ = portfolio_context(resolved, ids, contracts)
        if pack_scope:
            from odin.services.bundle import ledger_as_of
            company = repo.company(company_id)
            ctx["company_context"] = company.context if company else {}
            ctx["ledger"] = ledger_as_of(repo.sim_now())
            ctx["events_so_far"] = [e for e in repo.query("event") if e.get("occurred_at") and e["occurred_at"][:10] <= repo.sim_now().isoformat()]
            ctx["effective_amendments"] = [o for o in insights.clause_overrides() if o.get("doc") in ids]

        sources = [{'contract_id': c.contract_id, 'title': c.title} for c in contracts if c.contract_id in ids]
        direct = deterministic(question, ctx)
        if direct:
            return result(direct, kind=kind, ids=ids, sources=sources)
        passages, warnings = ([], []) if kind == 'portfolio' else evidence.retrieve(resolved, ids)
        if pack_scope:
            for o in ctx.get("effective_amendments", []):
                r = repo.clause_by_number(o["by_doc"], o["by_number"])
                if r and not any(p["clause_id"] == r.id for p in passages):
                    passages.append({"contract_id": r.contract_id, "clause_number": r.number,
                                     "ref": r.ref, "clause_id": r.id, "version": r.version,
                                     "page": r.page, "text": r.text, "heading": r.heading,
                                     "truncated": False})
        if kind == 'clause' and not passages:
            return result(kind=kind, ids=ids, sources=sources, reason='no_evidence', warnings=warnings,
                          missing=['No supporting clauses were found in the selected agreements. Try a clause number or a more specific question.'])
        payload = f'Question type: {kind}\nQuestion: {resolved}\n<portfolio>\n{j(ctx)}\n</portfolio>\n<document>\n{j(passages)}\n</document>'
        try:
            # Evidence is retrieved server-side; model tools cannot silently expand selected scope.
            draft = structured('ask', AnswerDraft, prompt('ask'), payload)
        except (LLMFailure, BudgetExceeded) as exc:
            reason = 'budget_exceeded' if isinstance(exc, BudgetExceeded) else 'provider_failure'
            return result(kind=kind, ids=ids, sources=sources, passages=passages, reason=reason,
                          warnings=warnings, missing=['The answer service could not complete this request. Your retrieved evidence is available below.'])
        good, bad = verified_claims(draft, kind, ids)
        missing = list(draft.missing)
        if bad:
            try:
                repair = structured('ask', AnswerDraft, prompt('ask'), payload + '\nRepair only these unsupported claims. Copy exact supporting quotes; omit claims you cannot support:\n' + j([c.model_dump(mode='json') for c in bad]))
                repaired, rejected = verified_claims(repair, kind, ids)
                good.extend(repaired)
                missing.extend(repair.missing)
                if rejected or not repaired:
                    missing.append('Some requested claims could not be supported with verified quotations and were omitted.')
            except (LLMFailure, BudgetExceeded):
                missing.append('Citation repair could not finish; unsupported claims were omitted.')
        unique = {c.text.strip(): c for c in good}
        answer = '\n\n'.join(c.text.strip() for c in unique.values())
        cits = { (c.contract_id, c.clause_number, c.quote): c for claim in unique.values() for c in claim.citations }
        if not answer:
            missing.append('No answer claims passed evidence checks. Try narrowing the question or selecting an agreement.')
        out = result(answer, kind=kind, ids=ids, sources=sources, passages=passages,
                     reason=None if answer else 'citation_failure', warnings=warnings, cits=list(cits.values()), missing=list(dict.fromkeys(missing)))
        out['diagnostics'] = {'retrieved_passages': len(passages), 'supported_claims': len(unique), 'citation_repair_attempted': bool(bad)}
        out['resolved_question'] = resolved
        return out
