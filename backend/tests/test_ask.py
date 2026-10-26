"""Ask regression checks use synthetic clauses, stubbed models and no external network."""
import inspect
from datetime import date
from types import SimpleNamespace as NS

import pytest
from odin.core.models import Citation
from odin.llm.call import LLMFailure
from odin.retrieval import evidence
from odin.services import ask as service

ask = inspect.unwrap(service.ask)


def contract(cid, title):
    return NS(contract_id=cid, title=title, type='services', status='active', meta={'parties': [{'name': 'Sample Vendor', 'role': 'vendor'}]})


def clause(cid='TEST-1', number='7.2', body='A cure period of thirty days applies.'):
    return NS(id=f'{cid}:{number}', contract_id=cid, number=number, text=body, version=1, page=2, heading='Remedies')


@pytest.fixture
def world(monkeypatch):
    cs = [contract('TEST-1', 'Sample Hosting Agreement'), contract('TEST-10', 'Sample Support Agreement')]
    clauses = [clause(), clause('TEST-10', body='A cure period of ten days applies.')]
    monkeypatch.setattr(service.repo, 'contracts', lambda: cs)
    monkeypatch.setattr(service.repo, 'clauses', lambda cid, *a, **k: [c for c in clauses if c.contract_id == cid])
    monkeypatch.setattr(service.repo, 'sim_now', lambda: date(2026, 10, 25))
    monkeypatch.setattr(service.insights, 'exposure_summary', lambda now: {'contracts': [{'contract_id': 'TEST-1', 'expected': 10, 'worst_case': 20, 'currency': 'INR'}, {'contract_id': 'TEST-10', 'expected': 2, 'worst_case': 3, 'currency': 'USD'}], 'currency': 'INR', 'note': 'No FX conversion.'})
    monkeypatch.setattr(service.insights, 'extraction', lambda cid: None)
    monkeypatch.setattr(service.insights, 'alerts', lambda now: [{'contract_id': c.contract_id, 'title': c.title} for c in cs])
    monkeypatch.setattr(service.evidence.hybrid, 'search', lambda *a, **kw: [])
    return cs, clauses


@pytest.mark.parametrize('question, expected', [
    ('What contracts do we have?', 'portfolio'),
    ('Which contracts renew next quarter?', 'portfolio'),
    ('What needs attention this month?', 'portfolio'),
    ('How many days do we have to cure a breach?', 'clause'),
    ('Summarize clause 7.2 of TEST-1', 'clause'),
    ('What is the liability cap across these agreements?', 'mixed'),
    ('Which contracts allow subcontracting?', 'mixed'),
    ('Which contracts offer rebates?', 'mixed'),
])
def test_routing(question, expected):
    assert service.classify(question) == expected


def test_exact_ids_do_not_match_prefixes_and_common_title_words_do_not_scope(world):
    cs, _ = world
    assert service._mentioned('TEST-1', cs) == ['TEST-1']
    assert service._mentioned('What does Sample say?', cs) == []
    assert service._mentioned('What does the hosting agreement say?', cs) == ['TEST-1']


def test_followup_inherits_scope_but_new_explicit_reference_overrides_it(world):
    cs, _ = world
    history = [{'question': 'Summarize TEST-1', 'contract_ids': ['TEST-1']}]
    ids, resolved, bad = service.resolve_scope('What about its termination?', None, history, cs)
    assert ids == ['TEST-1'] and 'Summarize TEST-1' in resolved and not bad
    assert service.resolve_scope('What about TEST-10?', None, history, cs)[0] == ['TEST-10']
    assert service.resolve_scope('What about it?', ['unavailable'], history, cs)[2] == ['unavailable']


def test_snapshot_scope_filters_facts_alerts_and_currency_totals(world):
    scoped, _ = service.portfolio_context('exposure', ['TEST-1'], world[0])
    assert scoped['contract_count'] == 1
    assert [r['contract_id'] for r in scoped['contracts']] == ['TEST-1']
    assert [r['contract_id'] for r in scoped['open_alerts']] == ['TEST-1']
    assert scoped['exposure_by_currency'] == {'INR': {'expected': 10, 'worst_case': 20}}
    whole, _ = service.portfolio_context('exposure')
    assert set(whole['exposure_by_currency']) == {'USD', 'INR'}


def test_inventory_does_not_call_model_or_retrieval(world, monkeypatch):
    monkeypatch.setattr(service, 'structured', lambda *a, **k: pytest.fail('Inventory should not call a model'))
    monkeypatch.setattr(service.evidence, 'retrieve', lambda *a, **k: pytest.fail('Inventory should not retrieve'))
    out = ask('company', 'How many contracts do we have?', ['TEST-1'])
    assert '1 uploaded' in out['answer'] and out['status'] == 'answered'


def claim(body='Thirty days are allowed.', quote='A cure period of thirty days applies.', cid='TEST-1'):
    return service.AnswerClaim(text=body, basis='clause', citations=[Citation(contract_id=cid, clause_number='7.2', quote=quote)])


def test_partial_answer_retains_supported_claim_after_repair_failure(world, monkeypatch):
    draft = service.AnswerDraft(claims=[claim(), claim('Unsupported cap.', 'This quotation does not exist.')])
    calls = []
    def model(*a, **kw):
        assert not kw.get('tools')
        calls.append(a)
        if len(calls) == 2:
            raise LLMFailure('offline failure')
        return draft
    monkeypatch.setattr(service, 'structured', model)
    out = ask('company', 'What is the cure period and liability cap in TEST-1?')
    assert out['status'] == 'partial'
    assert out['answer'] == 'Thirty days are allowed.'
    assert out['citations'][0]['verified']
    assert 'Unsupported cap' not in out['answer'] and len(calls) == 2


def test_repair_can_recover_a_bad_quote(world, monkeypatch):
    drafts = iter([service.AnswerDraft(claims=[claim(quote='Invented quotation.')]), service.AnswerDraft(claims=[claim()])])
    monkeypatch.setattr(service, 'structured', lambda *a, **kw: next(drafts))
    out = ask('company', 'What is TEST-1 cure period?')
    assert out['status'] == 'answered' and len(out['citations']) == 1


def test_citations_cannot_escape_selected_agreement(world):
    good, bad = service.verified_claims(service.AnswerDraft(claims=[claim(cid='TEST-10')]), 'clause', ['TEST-1'])
    assert not good and len(bad) == 1
    good, bad = service.verified_claims(service.AnswerDraft(claims=[service.AnswerClaim(text='Unsupported interpretation', basis='portfolio')]), 'clause', ['TEST-1'])
    assert not good and bad


def test_provider_failure_preserves_retrieved_evidence(world, monkeypatch):
    def fail(*a, **k):
        raise LLMFailure('Do not leak provider credentials or internals')
    monkeypatch.setattr(service, 'structured', fail)
    out = ask('company', 'What is TEST-1 cure period?')
    assert out['reason'] == 'provider_failure' and out['passages']
    assert out['answer'] == '' and 'credentials' not in str(out)


def test_invalid_selection_never_falls_back_to_all_agreements(world, monkeypatch):
    monkeypatch.setattr(service, 'structured', lambda *a, **k: pytest.fail('Invalid scope must not call the model'))
    assert ask('company', 'What is the cap?', ['unknown'])['reason'] == 'invalid_scope'


def test_full_text_search_finds_tail_of_long_clause_and_survives_dense_failure(world, monkeypatch):
    row = clause(body=('Unrelated introductory wording. ' * 330) + 'Exceptional zephyr reimbursement requires a receipt.')
    monkeypatch.setattr(evidence.repo, 'clauses', lambda cid: [row])
    def unavailable(*a, **k):
        raise RuntimeError('embedding unavailable')
    monkeypatch.setattr(evidence.hybrid, 'search', unavailable)
    passages, warnings = evidence.retrieve('zephyr reimbursement', ['TEST-1'])
    assert 'zephyr reimbursement' in passages[0]['text']
    assert passages[0]['excerpt_start'] > 1800 and passages[0]['truncated'] and warnings


def test_explicit_clause_reference_and_linked_clause_are_retrieved(world, monkeypatch):
    rows = [clause(number='7.2', body='Cure is subject to clause 9.1.'), clause(number='9.1', body='Delivery proof is mandatory.')]
    monkeypatch.setattr(evidence.repo, 'clauses', lambda cid: rows)
    passages, _ = evidence.retrieve('Explain clause 7.2', ['TEST-1'], limit=1)
    assert {p['clause_number'] for p in passages} == {'7.2', '9.1'}


def test_request_validation_bounds_conversation():
    from odin.api.routes import AskReq
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        AskReq(question='x' * 4001)
    with pytest.raises(ValidationError):
        AskReq(question='question', history=[{'question': 'prior'}] * 5)

def test_scoped_prompt_does_not_include_other_agreement_data(world, monkeypatch):
    seen = []
    def model(agent, schema, system, payload, **kwargs):
        seen.append(payload)
        return service.AnswerDraft(claims=[claim()])
    monkeypatch.setattr(service, 'structured', model)
    ask('company', 'What is the cure period?', ['TEST-1'])
    assert 'TEST-10' not in seen[0] and 'Support Agreement' not in seen[0]


def test_unsupported_claims_are_never_returned_as_answer_text(world, monkeypatch):
    monkeypatch.setattr(service, 'structured', lambda *a, **k: service.AnswerDraft(claims=[claim('Unsupported statement.', 'Invented quotation.')]))
    out = ask('company', 'What is the cure period?', ['TEST-1'])
    assert out['reason'] == 'citation_failure' and out['status'] == 'unanswered'
    assert out['answer'] == '' and not out['citations']


def test_ask_endpoint_validates_and_forwards_scope_and_history(world, monkeypatch):
    from fastapi import HTTPException
    from odin.api import routes
    monkeypatch.setattr(routes.ask_svc, 'ask', ask)
    req = routes.AskReq(question='How many contracts do we have?', contract_ids=['TEST-1'],
                        history=[{'question': 'Tell me about TEST-1', 'contract_ids': ['TEST-1']}])
    out = routes.ask(req, NS(company_id='company'))
    assert out['scope_ids'] == ['TEST-1']
    assert '1 uploaded' in out['answer']
    with pytest.raises(HTTPException) as err:
        routes.ask(routes.AskReq(question=' '), NS(company_id='company'))
    assert err.value.status_code == 400


def test_mixed_answer_cannot_label_legal_interpretation_as_portfolio(world):
    draft = service.AnswerDraft(claims=[service.AnswerClaim(text='The liability cap is unlimited.', basis='portfolio')])
    supported, rejected = service.verified_claims(draft, 'mixed', ['TEST-1'])
    assert not supported and rejected


def test_removed_history_scope_never_silently_expands_to_portfolio(world):
    ids, _, invalid = service.resolve_scope('What about its notice?', None,
        [{'question': 'Explain removed agreement', 'contract_ids': ['REMOVED']}], world[0])
    assert ids == [] and invalid == ['REMOVED']
