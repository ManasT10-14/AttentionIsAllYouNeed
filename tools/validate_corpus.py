"""Validate files and independent fixture arithmetic; does not run or score Odin."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from collections import Counter
from email import policy
from email.parser import BytesParser
import csv
import hashlib
import json
from pathlib import Path
import re

from pypdf import PdfReader
from contracts import CONTRACTS
from build_corpus import clause_records, render
from build_emails import strict_fields, TYPES

ROOT=Path(__file__).resolve().parents[1]
C=ROOT/'corpus'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def norm(text):
    return ' '.join(text.split())


def instant(text):
    value=datetime.fromisoformat(text.replace('Z','+00:00'))
    assert value.tzinfo, text
    return value


def allowed_file(path):
    p=(C/path).resolve()
    assert p.is_relative_to((C/'inputs').resolve()),path
    assert p.is_file(),path
    return p


def validate():
    manifest=read(C/'manifest.json')
    expected=read(C/'oracle/expected_cases.json')
    cases={x['case_id']:x for x in expected['cases']}
    assert len(cases)==len(expected['cases'])
    entries=manifest['contracts']
    assert len(entries)==8
    assert manifest['initial_contract_ids']==['C01','C02','C03','C04','C05','C06','C07']
    assert manifest['held_back_contract_ids']==['C08']
    assert {p.name for p in (C/'inputs/contracts').glob('*.pdf')}=={f'C{i:02}.pdf' for i in range(1,9)}
    index={}
    page_count=0
    for entry in entries:
        path=allowed_file(entry['file'])
        assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256']
        source=next(x for x in CONTRACTS if x['id']==entry['contract_id'])
        reader=PdfReader(path)
        page_count+=len(reader.pages)
        pages=[p.extract_text() for p in reader.pages]
        reader.close()
        text='\n'.join(pages)
        assert text.startswith('CONTRACT TITLE: ')
        cover=dict(line.split(': ',1) for line in pages[0].splitlines()[:7])
        assert list(cover)==['CONTRACT TITLE','CONTRACT ID','CONTRACT TYPE','EFFECTIVE DATE','PARTY A','PARTY B','GOVERNING LAW']
        assert cover['CONTRACT ID']==source['id']
        assert not re.search(r'\bversion\b',text,re.I)
        assert cover['CONTRACT TYPE'] in ['vendor','lease','employment','saas','partnership','nda','supply','other']
        assert re.fullmatch(r'\d{4}-\d{2}-\d{2}',cover['EFFECTIVE DATE'])
        assert not re.search(r'fictional|synthetic|demonstration|simulation|fixture',text,re.I)
        assert not re.search(r'C\d{2}\.\d',text),'Old citation format remains'
        records=clause_records(source)
        expected_numbers=[r['clause_id'] for r in records]+list(dict.fromkeys(r['section'] for r in records))
        actual_numbers=re.findall(r'^(\d+(?:\.\d+){0,3})\s+',text,re.M)
        assert Counter(actual_numbers)==Counter(expected_numbers),(source['id'],actual_numbers)
        assert all(t.isupper() for n,t in re.findall(r'^(\d+)\s+(.+)',text,re.M))
        for record in records:
            cid=source['id']+':'+record['clause_id']
            matches=[i for i,p in enumerate(pages,1) if norm(record['clause_id']+' '+record['text']) in norm(p)]
            assert len(matches)==1,cid
            index[cid]=dict(contract_id=source['id'],clause_id=record['clause_id'],file=entry['file'],page=matches[0],quote=norm(record['text']))
        if source['id']=='C01':
            assert re.search(r'^(SCHEDULE|ANNEX|EXHIBIT)\s+[A-Z]',text,re.M)
            for row,quote in [(1,'Row 1 | SVC-ATLAS hosting | INR 200,000 per month | Due on day 5 at 17:00 UTC'),(2,'Row 2 | Qualifying incident credit | INR 10,000 | Monthly cap INR 20,000')]:
                matched=[n for n,p in enumerate(pages,1) if quote in norm(p)]
                assert len(matched)==1
                label=f'Sch A, row {row}'
                index['C01:'+label]=dict(contract_id='C01',clause_id=label,file=entry['file'],page=matched[0],quote=quote)
    # Evidence index stays evaluator-only. Its quotes were checked against final PDF pages.
    (C/'oracle/evidence_index.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
    allowed_file(manifest['context'])
    context_lines=dict(line.split(': ',1) for line in allowed_file(manifest['context']).read_text().splitlines())
    assert set(context_lines)=={'COMPANY NAME','INDUSTRY','HQ / JURISDICTIONS','FISCAL YEAR START','BASE CURRENCY','RISK APPETITE','APPROVAL THRESHOLD','KEY CONTACTS','STRATEGIC PRIORITIES','CRITICAL DEPENDENCIES'}
    assert context_lines['APPROVAL THRESHOLD']=='INR 10,00,000'
    assert read(allowed_file(manifest['structured_context']))['approval_threshold_inr']=='1000000'
    all_ids={e['contract_id'] for e in entries}
    for item in read(allowed_file(manifest['scenario_index'])):
        scenario=read(allowed_file(item['file']))
        cid=scenario['scenario_id']; case=cases[cid]
        assert set(scenario['initial_contract_ids'])<=all_ids
        assert instant(scenario['baseline_clock'])<=instant(case['assert_at'])
        events=read(allowed_file(scenario['events_file']))
        assert len({e['event_id'] for e in events})==len(events),cid
        assert events==sorted(events,key=lambda e:(e['received_at'],e['event_id']))
        ids={e['event_id'] for e in events}
        for e in events:
            assert instant(e['occurred_at'])<=instant(e['received_at']),e
            assert set(e)==({'event_id','event_type','occurred_at','received_at','source_ref','payload'} | ({'supersedes_event_id'} if 'supersedes_event_id' in e else set()))
            if 'supersedes_event_id' in e:
                assert e['supersedes_event_id'] in ids
            assert not any(x in json.dumps(e).lower() for x in ['expected_','severity','clause_id','business_status','oracle/']),cid
            if e['event_type']=='contract_received':
                allowed_file(e['payload']['file'])
        for clause in case['evidence']:
            assert clause in index,(cid,clause)
        for eid, clauses in case['event_mapping'].items():
            assert eid in ids,(cid,eid)
            assert set(clauses)<=set(index),(cid,clauses)
        assert set(case['event_mapping'])==ids,cid
        assert case['business_status'] in ['compliant','at_risk','breached','unresolved']
        assert case['required_findings'] and case['forbidden_findings']
        assert instant(case['assert_at']) in [instant(x) for x in scenario['clock_checkpoints']]
    assert {x['scenario_id'] for x in read(allowed_file(manifest['scenario_index']))}==set(cases)
    assert {c['family'] for c in cases.values()}=={'renewal','payments','dependencies','outages','regulatory','jurisdiction','cure','amendments','ambiguity','arrival','adversarial'}
    terms=read(C/'oracle/expected_terms.json')['contracts']
    assert {t['contract_id'] for t in terms}==all_ids
    field_count=0
    for term in terms:
        entry=next(x for x in entries if x['contract_id']==term['contract_id'])
        assert term['party_ids']==entry['party_ids']
        for field in term['fields']:
            field_count+=1
            assert field['evidence']
            assert all(x in index and x.startswith(term['contract_id']+':') for x in field['evidence'])
    email_index=read(allowed_file(manifest['email_fixture_index']))
    parser_cases={c['file']:c for c in read(C/'oracle/email_parser_expectations.json')['cases']}
    assert {e['template_type'] for e in email_index if 'template_type' in e}==set(TYPES)
    email_ids=set()
    for item in email_index:
        message=BytesParser(policy=policy.default).parsebytes(allowed_file(item['file']).read_bytes())
        body=message.get_content().replace('\r\n','\n')
        expected_result=parser_cases.get(item['file'],{}).get('strict_result','parsed')
        try:
            fields=strict_fields(str(message['Subject']),body)
            actual='parsed'
        except ValueError:
            actual='needs_llm_fallback';fields={}
        assert actual==expected_result,item['file']
        if fields.get('EVENT_ID'):
            assert fields['EVENT_ID'] not in email_ids,fields['EVENT_ID']
            email_ids.add(fields['EVENT_ID'])
        assert not re.search(r'fictional|synthetic|demonstration',body,re.I)
        assert 'oracle/' not in body and 'expected_' not in body
        allowed_file(item['copy_text'])
    with (C/'oracle/source_requirement_coverage.csv').open(encoding='utf-8',newline='') as f:
        coverage=list(csv.DictReader(f))
    requirements={f'FR{group}.{sub}' for group,count in enumerate([4,4,3,4,3,3,2,2,5],1) for sub in range(1,count+1)} | {f'NFR{n}' for n in range(1,8)}
    assert {row['requirement'] for row in coverage}==requirements
    assert all(None not in row and all(row.values()) for row in coverage)
    faults=read(C/'runtime_specs/fault_scenarios.json')['cases']
    assert len({x['id'] for x in faults})==len(faults)==13
    assert all(set(x['requirements'])<=requirements and x['expect'] for x in faults)
    traps=read(C/'oracle/seeded_traps.json')['traps']
    assert len(traps)==9
    assert all(set(t['evidence'])<=set(index) and set(t['case_ids'])<=set(cases) for t in traps)
    # Independent calendar and financial checks against authored expected constants.
    assert str(date(2027,6,30)-timedelta(days=30))=='2027-05-31'
    for key,days in [('AMD-01',60),('AMD-02',30)]:
        assert cases[key]['exact']['applicable_cutoff']==str(date(2027,12,31)-timedelta(days=days))+'T17:00:00Z'
    assert cases['REN-02']['exact']['renewal_committed_inr']==str(6*100000)
    for key in ['PAY-03','PAY-05']:
        assert Decimal(cases[key]['exact']['late_charge_inr'])==Decimal(100000-60000)*Decimal('0.001')*3
    days=(date(2027,3,20)-date(2027,1,26)).days+1
    assert days==54
    assert Decimal(cases['PAY-06']['exact']['late_charge_inr'])==min(Decimal(100000)*Decimal('.001')*days,Decimal(5000))
    assert cases['DEP-03']['exact']['upstream_delay_recoverable_inr']==str(min(5*2000,20000))
    assert cases['DEP-03']['exact']['downstream_delay_payable_inr']==str(min(7*5000,50000))
    assert cases['OUT-08']['exact']['recoverable_credit_inr']==str(min(3*10000,20000))
    assert cases['OUT-08']['exact']['gross_payable_credit_inr']==str(min(3*15000,45000))
    assert str(date(2027,2,11)+timedelta(days=10))=='2027-02-21'
    assert str(date(2027,4,2)+timedelta(days=10))=='2027-04-12'
    assert cases['TRAP-02']['exact']['payment_due']==str(date(2027,2,7)+timedelta(days=30))+'T17:00:00Z'
    for key in ['OUT-01','OUT-02','OUT-03','OUT-04']:
        e=read(C/f'inputs/events/{key}.json')[0]['payload']
        minutes=(instant(e['end'])-instant(e['start'])).total_seconds()/60
        assert cases[key]['exact']['recoverable_credit_inr']==('10000' if minutes>60 else '0')
        assert cases[key]['exact']['gross_payable_credit_inr']==('15000' if minutes>30 else '0')
    # Rebuild hashes must be stable; invariant PDF metadata and frozen data prevent drift.
    before={x['file']:x['sha256'] for x in entries}
    # Rebuild in scratch: validation must not overwrite a PDF open in a user viewer.
    for contract in CONTRACTS:
        rebuilt=render(contract,ROOT/'work/rebuild-v2')
        assert hashlib.sha256(rebuilt.read_bytes()).hexdigest()==before['inputs/contracts/'+rebuilt.name]
    report=dict(status='PASS',contracts=8,pages=page_count,verified_citation_units=len(index),scenarios=len(cases),email_fixtures=len(email_index),email_event_types=len(TYPES),extraction_field_assertions=field_count,source_requirements_mapped=len(requirements),runtime_specifications=len(faults),
        checks=['exact cover keys and absence of document versions','user clause and schedule regex without spurious starts','PDF source text and page citations','removed document labels','company context keys and approval amount','email syntax and all event enums','input path allowlist','event identities, times and oracle isolation','scenario and evidence references','independent date and decimal arithmetic','deterministic PDF rebuild'],
        limitations=['No Odin agents, UI, actual event replay or API fault recovery executed.','No independent human evaluator review.','Visual inspection recorded separately after rendering.'])
    (ROOT/'work').mkdir(exist_ok=True)
    (ROOT/'work/validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    validate()
