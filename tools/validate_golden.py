"""Validate authored golden references and visibility; never runs an agent."""
import hashlib
import json
from pathlib import Path
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]/'corpus'
G=ROOT/'oracle/golden'
AGENTS=['odin','thor','norns','loki','heimdall','tyr']


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def t(value):
    return datetime.fromisoformat(value.replace('Z','+00:00'))


def run():
    manifest=read(G/'manifest.json');corpus=read(ROOT/'manifest.json')
    cases={c['case_id']:c for c in read(ROOT/'oracle/expected_cases.json')['cases']}
    evidence=read(ROOT/'oracle/evidence_index.json');citations=read(G/'citation_goldens.json')
    documents={c['contract_id']:c['file'] for c in corpus['contracts']}
    assert manifest['agents']==AGENTS
    assert manifest['scenario_count']==len(cases)==64
    assert manifest['agent_scenario_vectors']==6*len(cases)==384
    for relative,digest in manifest['source_hashes'].items():
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==digest,relative
    assert set(citations)==set(evidence)
    for key,value in citations.items():
        assert value=={k:evidence[key][k] for k in ['contract_id','clause_id','page','quote']}
    extraction=read(G/'thor_contract_goldens.json')['contracts']
    assert set(extraction)==set(documents)
    field_count=0
    for cid,record in extraction.items():
        assert record['input']['contract_file']==documents[cid]
        for field in record['expected']['field_assertions']:
            field_count+=1
            assert field['evidence_refs'] and set(field['evidence_refs'])<=set(citations)
        assert all(unit['contract_id']==cid for unit in record['expected']['clause_inventory'])
    assert field_count==manifest['typed_extraction_assertions']==114
    total=0
    for agent in AGENTS:
        records=[json.loads(line) for line in (G/(agent+'.jsonl')).read_text(encoding='utf-8').splitlines()]
        assert len(records)==len(cases)
        assert {r['case_id'] for r in records}==set(cases)
        for r in records:
            total+=1;cid=r['case_id'];inp=r['input_spec'];expect=r['expected_output']
            assert r['agent']==agent and r['golden_id']==cid+'::'+agent
            assert 'oracle/' not in json.dumps(inp) and 'expected_output' not in inp
            scenario=read(ROOT/r['harness_source_refs']['scenario']);events=read(ROOT/scenario['events_file'])
            visible=[e for e in events if t(e['received_at'])<=t(inp['clock'])]
            known=set(scenario['initial_contract_ids'])
            known.update(e['payload']['document_id'] for e in visible if e['event_type']=='contract_received')
            assert set(inp['contract_files'])=={documents[k] for k in known}
            assert all((ROOT/path).is_file() and path.startswith('inputs/') for path in inp['contract_files'])
            if agent=='thor':assert inp['visible_event_ids']==[] and inp['released_observations']==[]
            else:assert inp['visible_event_ids']==[e['event_id'] for e in visible]
            assert all(t(e['received_at'])<=t(inp['clock']) for e in inp['released_observations'])
            assert set(expect.get('evidence_refs',[]))<=set(citations)
            if agent=='odin':
                assert set(expect['exact']['known_contract_ids'])==known
                assert expect['exact']['case_assertions']==cases[cid]['exact']
            if agent=='heimdall':
                assert set(expect['exact']['event_to_clause_mapping'])<=set(inp['visible_event_ids'])
            for point in r['evaluator_checkpoint_visibility']:
                actual=[e for e in events if t(e['received_at'])<=t(point['clock'])]
                docs=set(scenario['initial_contract_ids'])|{e['payload']['document_id'] for e in actual if e['event_type']=='contract_received'}
                assert point['visible_event_ids']==[e['event_id'] for e in actual]
                assert set(point['known_contract_ids'])==docs
            assert 'checkpoint_visibility' not in inp and 'evaluator_checkpoint_visibility' not in inp
    assert total==384
    examples=read(G/'worked_examples.json')['examples']
    assert len(examples)==6*len(manifest['worked_scenarios'])==36
    assert all(not e['unit_upstream_fixture']['state'] for e in examples if e['agent']=='thor')
    payment=read(G/'payment_pipeline_example.json')
    assert {p['agent'] for p in payment['pipeline']}==set(AGENTS)
    assert next(p for p in payment['pipeline'] if p['agent']=='norns')['expected_minimum']['late_charge_inr']=='120'
    def jsonl(name):
        return [json.loads(line) for line in (G/name).read_text(encoding='utf-8').splitlines()]
    assert jsonl('agent_goldens.jsonl')==[record for agent in AGENTS for record in jsonl(agent+'.jsonl')]
    assert len(jsonl('agent_goldens.jsonl'))==384
    assert {r['contract_id']:r for r in jsonl('thor_contract_goldens.jsonl')}==extraction
    assert {r['evidence_ref']:{k:v for k,v in r.items() if k!='evidence_ref'} for r in jsonl('citation_goldens.jsonl')}==citations
    assert jsonl('worked_examples.jsonl')==examples
    assert jsonl('payment_pipeline_example.jsonl')==[dict(case_id='PAY-03',**step) for step in payment['pipeline']]
    assert len(jsonl('agent_contracts.jsonl'))==6
    print(json.dumps(dict(status='PASS',agent_vectors=total,thor_contracts=len(extraction),typed_facts=field_count,citation_units=len(citations),worked_agent_examples=len(examples),agents_executed=0),indent=2))


if __name__=='__main__':
    run()
