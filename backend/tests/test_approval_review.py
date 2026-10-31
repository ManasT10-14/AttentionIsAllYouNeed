from copy import deepcopy
from test_action_approvals import store, approve
from odin.core.context import run_ctx
from odin.db import session, repo
from odin.db.tables import Company, Contract, ContractVersion, Record
from odin.services import approvals


def test_governing_document_citations_bind_each_current_source(store):
    with session.db() as s:
        s.add(Contract(id='addendum', company_id='a', contract_id='C02', current_version=1, meta={}))
        s.add(ContractVersion(id='addendum-v1', company_id='a', contract_id='C02', version=1, sha256='addendum-hash', file_path='',pdf_path='',text=''))
        row=s.get(Record,'a|act'); data=deepcopy(row.data)
        data['citations']=[{'contract_id': 'C02','clause_number':'1','version':1,'verified':True}]
        row.data=data
    with run_ctx('a', user_role='admin'):
        assert approvals.eligibility('act')['can_approve']
        approved=approve()
        assert {s['contract_id'] for s in approved['approval']['sources']} == {'C01','C02'}


def test_generated_display_names_and_multiple_documented_recipients_are_supported(store):
    with session.db() as s:
        s.get(Company,'a').context={'contacts':['legal@aurora.test']}
        row=s.get(Record,'a|act'); data=deepcopy(row.data)
        data['to']='Forge Notice <notice@forge.test>; Aurora Legal <legal@aurora.test>'
        row.data=data
    with run_ctx('a', user_role='admin'):
        assert approvals.eligibility('act')['recipients'] == 'notice@forge.test, legal@aurora.test'
        action=approve()
        assert approvals.action_payload(action)[1]['to'] == 'notice@forge.test, legal@aurora.test'


def test_preflight_explains_undocumented_recipient_without_changing_action(store):
    with session.db() as s:
        row=s.get(Record,'a|act'); data=deepcopy(row.data)
        data['to']='notice@forge.test; stranger@unrelated.test'; row.data=data
    with run_ctx('a',user_role='admin'):
        status=approvals.eligibility('act')
        assert not status['can_approve'] and 'documented' in status['reason']
        assert repo.get('action','act')['status'] == 'draft'


def test_header_injection_is_rejected_before_approval(store):
    with session.db() as s:
        row=s.get(Record,'a|act'); data=deepcopy(row.data)
        data['to']='notice@forge.test\r\nBcc: stranger@unrelated.test'; row.data=data
    with run_ctx('a',user_role='admin'):
        status=approvals.eligibility('act')
        assert not status['can_approve'] and 'control characters' in status['reason']
