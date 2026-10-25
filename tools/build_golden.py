"""Build evaluator-only agent goldens from authored keys and verified PDF evidence.

No agent is executed. Never give these files to an end-to-end agent run.
"""
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'corpus'
OUT=ROOT/'oracle/golden'
AGENTS=['odin','thor','norns','loki','heimdall','tyr']
ROLES={
 'odin':dict(input=['company context','selected contract inventory','clock and released arrivals','actual agent outputs and workstream statuses','iteration/call/token limits'],output=['one workstream per known contract plus a cross-contract workstream','delegation and status tracking','clarification/debate coordination','cited per-contract and company reports','prioritized actions and honest stopping/completion status'],forbidden=['Claim a whole-company total from a scoped subtotal','Mark failed/pending workstreams complete','Automatically replace an agreement because parties match']),
 'thor':dict(input=['raw selected PDF bytes','company identity and canonical party IDs','optional targeted clause re-extraction request'],output=['parties, scope, dates, payments, obligations and remedies','field values with exact source quotes and page/clause IDs','model-produced confidence','missing or ambiguous terms and targeted questions'],forbidden=['Read evaluator answer keys','Invent an absent Schedule B or blank percentage','Treat event observations as contractual text']),
 'norns':dict(input=['actual Thor structured facts and evidence','simulated clock','visible payment/event history or verified ledger updates','prior obligation state and calendar rules'],output=['past/current/future obligations','notice, grace, cure and payment dates','contract-supported monetary calculations with direction and conditions','inaction projections with explicit assumptions','history/replay state'],forbidden=['Compound simple late interest','Add a credit receivable to gross payable exposure','Treat future obligations as current fines','Retain future facts after reset']),
 'loki':dict(input=['actual Thor extraction and uncertainty','actual Norns timeline/projection','relevant cross-contract clauses','company risk appetite and priorities'],output=['evidence-backed risk hypotheses and attack paths','cross-contract contradictions and dependencies','reasoned severity and likelihood','targeted clarification where evidence is insufficient'],forbidden=['Treat different jurisdictions alone as invalidity','Invent liabilities to make a case risky','Force a disagreement when agents agree','Repeat whole-document extraction for an already resolved question']),
 'heimdall':dict(input=['only released emails/observations','actual Thor evidence and entity/service references','actual Norns ledger/timeline','actual Loki hypotheses','clock and event identity history'],output=['event-to-contract/clause mappings','verification or challenge with event and clause evidence','deduplication/correction treatment','supported exposure/state changes','prioritized alerts and filtered noise'],forbidden=['Read future received_at records early','Trust sender SEVERITY_HINT as a finding','Duplicate a payment or outage from repeated records','Map an event solely because a vendor name matches']),
 'tyr':dict(input=['actual disputed Loki/Heimdall findings, if any','verified source and event evidence','actual current timeline and money state','company contacts, approval policy and unresolved questions'],output=['reasoned rulings when a dispute exists','cited drafts or escalation/clarification proposals','explicit human-approval and confidence markings','unresolved issues where evidence cannot decide'],forbidden=['Fabricate a dispute or compulsory ruling','Guess a missing fee to force resolution','Send or execute a drafted action','Silently choose between contradictory notice periods'])}


def read(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8'))


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')


def instant(value):
    return datetime.fromisoformat(value.replace('Z','+00:00'))


def snapshot(scenario,events,clock):
    visible=[e for e in events if instant(e['received_at'])<=instant(clock)]
    known=list(scenario['initial_contract_ids'])
    for e in visible:
        if e['event_type']=='contract_received' and e['payload']['document_id'] not in known:
            known.append(e['payload']['document_id'])
    return dict(clock=clock,known_contract_ids=sorted(known),visible_event_ids=[e['event_id'] for e in visible])


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    manifest=read('manifest.json');evidence=read('oracle/evidence_index.json')
    terms=read('oracle/expected_terms.json')['contracts']
    cases=read('oracle/expected_cases.json')['cases']
    entries={c['contract_id']:c for c in manifest['contracts']}
    citations={key:dict(contract_id=value['contract_id'],clause_id=value['clause_id'],page=value['page'],quote=value['quote']) for key,value in evidence.items()}
    write(OUT/'agent_contracts.json',dict(agents=ROLES,confidence_policy='Require a numeric agent-generated confidence in [0,1] with evidence/uncertainty rationale. Do not compare against a fixed golden score.',
        assessment_policy='Severity, likelihood and narrative wording are rubric-scored. Equivalent supported explanations pass.',
        approval_policy='Company threshold is INR 1000000; above-threshold actions require approval. All externally usable drafts in this corpus remain approval-marked and draft-only.',
        modes=dict(unit='Harness injects a controlled upstream state for the single agent under test. Clearly label it as a test fixture, not an execution trace.',end_to_end='Agents receive actual upstream outputs only. No golden file or expected answer is exposed to agents.'),
        recommended_loop=['Odin plan','Thor extraction','Norns baseline','Loki review','Heimdall released-event verification','Norns affected-state update','Tyr if dispute/action is needed','Odin synthesis'],
        feedback='Targeted Thor clarification and Loki/Heimdall/Tyr feedback are conditional. Use configured evidence, iteration and budget stopping rules; no exact call count or mandatory disagreement is imposed.'))

    extraction=[]
    for contract in terms:
        cid=contract['contract_id']
        extraction.append(dict(contract_id=cid,
            input=dict(contract_file=entries[cid]['file'],sha256=entries[cid]['sha256'],company_context=manifest['context'],target='full extraction, or a specifically requested clause'),
            expected=dict(party_ids=contract['party_ids'],field_assertions=[dict(name=f['field'],value=f['value'],evidence_refs=f['evidence']) for f in contract['fields']],
                clause_inventory=[dict(evidence_ref=key,**value) for key,value in citations.items() if value['contract_id']==cid],
                required_output_fields=['field name','normalized value or explicit unknown','supporting quote','contract/clause ID','one-based PDF page','model confidence','uncertainty explanation when needed'],
                coverage='Typed fields are minimum semantic assertions, not a claim of exhaustive normalized legal interpretation. The inventory exhaustively anchors authored clauses/table rows.')))
    write(OUT/'thor_contract_goldens.json',dict(contract_count=len(extraction),contracts={r['contract_id']:r for r in extraction}))
    write(OUT/'citation_goldens.json',citations)

    datasets={agent:[] for agent in AGENTS};worked=[]
    examples={'PAY-03','OUT-07','AMB-01','PROJECT-B','LINK-01','DEMO-PORTFOLIO'}
    financial_tokens=['due','deadline','cutoff','principal','charge','credit','inr','fee','cap','hours','days','committed','renewal','restoration','matured','calendar','end']
    for case in cases:
        cid=case['case_id'];scenario=read('inputs/scenarios/'+cid+'.json');events=read(scenario['events_file'])
        visible=snapshot(scenario,events,case['assert_at']);known=visible['known_contract_ids']
        released=[e for e in events if e['event_id'] in visible['visible_event_ids']]
        refs=[r for r in case['evidence'] if r.split(':')[0] in known]
        common_input=dict(company_context=manifest['context'],contract_files=[entries[c]['file'] for c in known],clock=case['assert_at'],
            release_filter='received_at <= clock; the harness releases only matching observations',visible_event_ids=visible['visible_event_ids'],
            state_scope=case['scope'])
        financial={k:v for k,v in case['exact'].items() if any(token in k for token in financial_tokens)}
        mappings={eid:cl for eid,cl in case['event_mapping'].items() if eid in visible['visible_event_ids']}
        duplicate_groups=[];identities={}
        for e in released:
            p=e['payload'];kind=e['event_type'];identity=p.get('bank_transaction_id') if kind=='payment_cleared' else p.get('incident_id') if kind=='service_restored' and not e.get('supersedes_event_id') else None
            if identity:identities.setdefault(kind+':'+identity,[]).append(e['event_id'])
        duplicate_groups=[dict(identity=k,event_ids=v) for k,v in identities.items() if len(v)>1]
        visibility_checks=[snapshot(scenario,events,t) for t in scenario['clock_checkpoints']]
        rubric=dict(required_findings=case['required_findings'],forbidden_findings=case['forbidden_findings'],evidence_refs=refs)
        values={
          'odin':dict(exact=dict(known_contract_ids=known,contract_workstream_count=len(known),cross_contract_workstream_count=1,case_business_status=case['business_status'],case_assertions=case['exact']),
            requirements=['Delegate separate responsibilities and retain per-contract/cross-contract state.','Synthesize actual agent outputs and preserve facts versus analysis.','Only mark the scoped analysis complete after mandatory workstreams succeed; unresolved terms may remain explicit.'],
            expected_normal_completion=case['completion_state'],scope_warning='These assertions are scoped. They are not an exhaustive company exposure total.',**rubric),
          'thor':dict(exact=dict(known_contract_ids=known),contract_goldens=[dict(contract_id=c,golden_record='thor_contract_goldens.json#/contracts/'+c) for c in known],
            requirements=['Extract from the PDFs, not from golden fields.','Every field needs clause quote/page and model confidence.','A missing attachment or blank rate remains unknown.','Do not include event-derived balances as contract text.'],evidence_refs=refs),
          'norns':dict(exact=dict(as_of=case['assert_at'],timeline_and_financial_assertions=financial),checkpoint_assertions=case['checkpoints'],
            requirements=['Use actual extracted terms and the visible/verified history.','Give formulas, charge dates and currency; distinguish payable, receivable, future commitment and unquantified items.','A late receipt can revise reconstructed history while retaining the earlier as-known view.'],**rubric),
          'loki':dict(exact={},scenario_context=case['business_status'],
            requirements=['Identify supported adverse interpretations or dependencies, including clean controls.','Each proposed attack needs an evidence-backed path, assumptions and model-assessed severity/likelihood.','If evidence is already clear, do not manufacture a clarification loop.'],
            clarification_topic=case['clarification'],clarification_gate='Request targeted evidence only where missing/uncertain and not already resolved; missing external documents may require an external clarification proposal.',**rubric),
          'heimdall':dict(exact=dict(processed_visible_event_ids=visible['visible_event_ids'],event_to_clause_mapping=mappings),semantic_duplicate_groups=duplicate_groups,
            corrections=[dict(event_id=e['event_id'],supersedes=e['supersedes_event_id']) for e in released if e.get('supersedes_event_id')],
            verified_state_assertions=case['exact'] if released else {},
            requirements=['Mapping can propagate to dependent contracts. Sender contract IDs and severity hints do not override actual scope.','Process repeated records idempotently.','Challenge or confirm actual Loki claims using visible observations and clauses; check clock deadlines even with no new event.'],**rubric),
          'tyr':dict(exact=dict(external_actions_executed=0,all_emitted_external_drafts_require_human_approval=True),
            recommended_action=case['recommended_action'],unresolved_question=case['clarification'],
            ruling_gate=dict(if_actual_dispute='Return a cited decision and rationale, preserving unresolved evidence where necessary.',if_no_dispute='No invented ruling is required; an empty rulings list or not_required is valid.'),
            draft_gate='Draft only an appropriate supported action. No-action/control cases may return no draft. Do not send or execute anything.',
            requirements=['Use actual verified money, dates, roles and recipient details.','Include exact clause citations and confidence on drafted actions.','Do not invent a missing term to close a dispute.'],**rubric)
        }
        upstream={
          'odin':['actual agent outputs and workstream states; company action policy'],
          'thor':['optional targeted extraction request only'],
          'norns':['actual Thor facts','actual visible history/Heimdall ledger updates'],
          'loki':['actual Thor facts and uncertainties','actual Norns timeline'],
          'heimdall':['actual Thor facts','actual Norns state','actual Loki hypotheses'],
          'tyr':['actual Loki/Heimdall disagreement if any','actual Norns verified state','company approval policy']}
        for agent in AGENTS:
            data=dict(golden_id=cid+'::'+agent,case_id=cid,agent=agent,
                harness_source_refs=dict(scenario='inputs/scenarios/'+cid+'.json',event_schedule=scenario['events_file']),
                evaluator_checkpoint_visibility=visibility_checks,
                input_spec=dict(common_input,upstream_state_requirements=upstream[agent],released_observations=released if agent in ['odin','norns','heimdall','tyr'] else []),
                expected_output=values[agent],comparison=dict(exact='Recursive partial equality; preserve exact dates, IDs, decimal strings, booleans and unknown nulls.',
                    narrative='Required/forbidden findings are role-scoped rubrics, not verbatim target text. Extra supported findings are allowed.',
                    model_assessments='Confidence, severity, likelihood and wording are not fixed expected constants. Require a defined scale and evidence-aware rationale.'))
            datasets[agent].append(data)
            if agent=='thor':data['input_spec']['visible_event_ids']=[]
            if cid in examples:
                expanded=dict(data)
                expanded['resolved_evidence']={r:citations[r] for r in refs}
                facts={r['contract_id']:r['expected']['field_assertions'] for r in extraction if r['contract_id'] in known}
                fixture={}
                if agent!='thor':fixture['thor_facts']=facts
                if agent in ['loki','heimdall','tyr','odin']:fixture['norns_state_assertions']=financial
                if agent in ['tyr','odin']:fixture['heimdall_event_mapping']=mappings
                if agent=='tyr':fixture['disputes']=[]
                expanded['unit_upstream_fixture']=dict(label='Controlled test input only, not actual execution results. Inject only the selected agent input; never the expected_output.',state=fixture)
                if agent=='tyr' and cid=='OUT-07':
                    fixture['disputes']=[dict(dispute_id='HOSTING-EXCLUSION-01',loki_hypothesis=dict(hosting_recoverable_inr='10000',assumption='Timely maintenance approval not established in the earlier view.'),heimdall_verification=dict(hosting_recoverable_inr='0',new_evidence='APPROVAL1',approval_lead_hours=48))]
                    expanded['expected_unit_ruling']=dict(dispute_id='HOSTING-EXCLUSION-01',decision='Apply the proved maintenance exclusion to hosting recovery only.',hosting_recoverable_inr='0',downstream_credit_payable_inr='15000',evidence_refs=['C01:4.1','C02:5.1','C02:6.1'])
                worked.append(expanded)
    for agent,records in datasets.items():
        (OUT/(agent+'.jsonl')).write_text(''.join(json.dumps(r,ensure_ascii=True)+'\n' for r in records),encoding='utf-8')
    write(OUT/'worked_examples.json',dict(examples=worked))
    payment_case=next(c for c in cases if c['case_id']=='PAY-03')
    payment_events=read('inputs/events/PAY-03.json')
    quote_refs=['C05:4.1','C05:5.1','C05:6.1']
    pipeline=[
        dict(agent='odin',phase='plan',input=dict(company_context=manifest['context'],contract_files=['inputs/contracts/C05.pdf'],clock=payment_case['assert_at']),
             expected_minimum=dict(contract_workstreams=[dict(contract_id='C05',status='pending')],cross_contract_workstreams=1,delegated_roles=['thor','norns','loki','heimdall','tyr'])),
        dict(agent='thor',input=dict(pdf='inputs/contracts/C05.pdf',company_id='P01'),
             expected_minimum=dict(contract_id='C05',party_ids=['P01','P03'],facts=[dict(name='monthly_rent_inr',value='100000',evidence_refs=['C05:4.1']),dict(name='daily_simple_rate',value='0.001',evidence_refs=['C05:6.1']),dict(name='charge_cap_per_invoice_inr',value='5000',evidence_refs=['C05:6.1'])])),
        dict(agent='norns',input=dict(upstream='actual Thor rent/allocation/grace facts',clock=payment_case['assert_at'],visible_observations=payment_events),
             expected_minimum=dict(invoice_id='RENT-2027-01',rent_due='2027-01-20T17:00:00Z',grace_end='2027-01-25T23:59:59Z',principal_inr='40000',charged_dates=['2027-01-26','2027-01-27','2027-01-28'],daily_charge_inr='40',late_charge_inr='120',invoice_total_inr='40120',formula='40000 * 0.001 * 3',evidence_refs=quote_refs)),
        dict(agent='loki',input=dict(upstream=['actual Thor facts','actual Norns timeline']),
             expected_minimum=dict(attacks=[dict(claim_id='RENT-OVERDUE-01',contract_id='C05',claim='Unpaid January rent supports a simple daily charge after grace.',supported_charge_inr='120',evidence_refs=quote_refs)],clarification_requests=[]),
             narrative_requirements=['Explain the path from unpaid principal and expired grace to the charge.','Do not charge on the INR 60000 already paid.','Severity, likelihood and confidence must be model-assessed, not copied from a fixed example.']),
        dict(agent='heimdall',input=dict(visible_observations=payment_events,upstream=['actual Thor clauses','actual Loki claim','actual Norns state']),
             expected_minimum=dict(event_to_clause_mapping={'PAY1':quote_refs},effective_payment_count=1,principal_inr='40000',late_charge_inr='120',verification=dict(claim_id='RENT-OVERDUE-01',decision='confirmed_for_supported_amount',charge_inr='120'))),
        dict(agent='tyr',input=dict(disputes=[],verified_invoice_balance_inr='40120',company_finance_contact='cfo@aurora.example',upstream='actual verified evidence and timeline'),
             expected_minimum=dict(rulings=[],external_actions_executed=0,drafts=[dict(draft_type='internal_payment_escalation',recipient='cfo@aurora.example',invoice_id='RENT-2027-01',principal_inr='40000',late_charge_inr='120',balance_inr='40120',human_approval_required=True,status='draft_only',evidence_refs=quote_refs)]),
             narrative_requirements=['Draft a reminder to Aurora finance about its own payable; do not impersonate Willow.','No dispute means no invented arbitration is needed.','Draft wording is semantic, not a verbatim golden string.']),
        dict(agent='odin',phase='synthesis',input=dict(upstream='actual completed agent states, findings and draft'),
             expected_minimum=dict(case_business_status='breached',analysis_scope='PAY-03 January rent obligation',case_assertions=payment_case['exact'],known_contract_ids=['C05'],cross_contract_workstream_count=1),
             narrative_requirements=['Report the INR 40120 as a scoped invoice subtotal, not the complete company exposure.','Retain cited facts, actions, confidence and completion/uncertainty state.'])]
    write(OUT/'payment_pipeline_example.json',dict(case_id='PAY-03',note='Author-created minimum expected outputs, not actual agent logs. Actual outputs must also include confidence and all role-required fields.',resolved_evidence={r:citations[r] for r in quote_refs},pipeline=pipeline))
    jsonl_exports={
        'agent_goldens.jsonl':[record for agent in AGENTS for record in datasets[agent]],
        'thor_contract_goldens.jsonl':extraction,
        'citation_goldens.jsonl':[dict(evidence_ref=key,**value) for key,value in citations.items()],
        'worked_examples.jsonl':worked,
        'payment_pipeline_example.jsonl':[dict(case_id='PAY-03',**step) for step in pipeline],
        'agent_contracts.jsonl':[dict(agent=agent,**role) for agent,role in ROLES.items()],
    }
    for filename,records in jsonl_exports.items():
        (OUT/filename).write_text(''.join(json.dumps(record,ensure_ascii=True)+'\n' for record in records),encoding='utf-8')
    with (OUT/'agent_io_matrix.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['agent','inputs','expected_outputs','never_do'])
        for agent,role in ROLES.items():w.writerow([agent,'; '.join(role['input']),'; '.join(role['output']),'; '.join(role['forbidden'])])
    manifest_out=dict(dataset='odin-agent-goldens',evaluator_only=True,agents=AGENTS,scenario_count=len(cases),agent_scenario_vectors=sum(len(v) for v in datasets.values()),
        thor_contract_goldens=len(extraction),typed_extraction_assertions=sum(len(c['fields']) for c in terms),verified_citation_units=len(evidence),worked_scenarios=sorted(examples),
        status='Authored expected outputs and rubrics; no agent execution or independent human review claimed.',
        source_hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['manifest.json','oracle/expected_cases.json','oracle/expected_terms.json','oracle/evidence_index.json']})
    write(OUT/'manifest.json',manifest_out)
    (OUT/'README.md').write_text(README,encoding='utf-8')
    print(json.dumps(manifest_out,indent=2))


README='''# Golden dataset: agent inputs and expected outputs

This evaluator-only dataset covers six agents, 64 scenarios and 15 contracts: **384 agent/scenario vectors**, **15 Thor contract goldens**, **114 typed extraction assertions** and **276 verified citation units**. It specifies expected behavior; no actual Odin agent run or independent human review is claimed.

| Agent | Receives | Expected result |
| --- | --- | --- |
| Odin | Company context, selected documents, clock, actual agent states/results and limits | One workstream per known contract plus cross-contract work; coordination; cited scoped synthesis and actions; honest completion/stopping state |
| Thor | Raw selected PDFs, company identities, optional targeted extraction request | Normalized contractual facts, parties, dates, payments, obligations and remedies with exact quote/page/clause evidence, confidence and explicit missing/ambiguous terms |
| Norns | Actual Thor facts, clock and visible/verified history | Due/grace/cure/notice dates, past/current/future obligations, directional money and supported inaction projections |
| Loki | Actual extraction, uncertainty, timeline and related clauses | Supported attack paths, conflicts and hidden liabilities; reasoned severity/likelihood; targeted clarification when useful |
| Heimdall | Released observations, actual facts/timeline and Loki hypotheses | Event mappings, verification/challenge, idempotent state updates, corrections, noise filtering and evidence-backed alerts |
| Tyr | Actual disputes if any, verified evidence/state, contacts and approval policy | Cited rulings when needed; supported drafts/escalations with approval and confidence; unresolved issues preserved; no action execution |

## Files

- agent_goldens.jsonl: combined 384-record dataset, one agent/scenario per line, with agent, input_spec, expected_output and comparison fields. The six per-agent JSONL files contain the same records split by agent.
- JSONL companion files: thor_contract_goldens.jsonl (15 records), citation_goldens.jsonl (276), worked_examples.jsonl (36), payment_pipeline_example.jsonl (7 stages), agent_contracts.jsonl (6 roles). Original JSON files remain available for existing lookup references.
- agent_contracts.json: responsibility boundaries, input/output contracts, forbidden behavior, feedback and scoring policies.
- agent_io_matrix.csv: compact teammate handoff table.
- thor_contract_goldens.json: records keyed C01-C15, typed facts and full clause/table-row citation inventories.
- odin.jsonl, thor.jsonl, norns.jsonl, loki.jsonl, heimdall.jsonl, tyr.jsonl: 64 vectors per agent.
- citation_goldens.json: verified quote/page lookup for every citation unit.
- worked_examples.json: six scenarios expanded across all agents (36 examples), with resolved evidence and role-specific controlled upstream inputs.
- payment_pipeline_example.json: concrete input/minimum-output records through planning, all five specialist agents and final synthesis for PAY-03.
- manifest.json: counts and source hashes to detect stale answer keys.

Each vector has input_spec, expected_output and comparison. The expected exact fields are a **minimum normalized assertion subset**, not a complete backend response schema. Evidence references identify relevant grounding, not an instruction to reproduce every quote verbatim. Additional supported facts/actions are allowed within the case scope. If an agent backend uses another schema, the evaluator maps its output to the logical assertion fields first. Normalize monetary values as decimal strings without float rounding; preserve unknown null rather than converting it to zero.

## What is fixed and what is judged

Compare IDs, dates, money, party scope, event visibility and cited source identity exactly after agreed normalization. Required/forbidden findings, attack paths, reasoning, prioritization and draft wording are rubric-scored. Confidence must be agent-produced on a defined scale; it is not a hardcoded golden value. Severity and likelihood need supported rationale, not a predetermined label. A breach correctly found or an uncertainty correctly retained can pass.

Thor field assertions are deliberately minimum typed checks. The 276-unit inventory exhaustively anchors the authored numbered clauses and table rows, but it does not pretend to be an independently reviewed full legal interpretation of every sentence. A scenario-level Thor vector checks the combined stage results; use the 15 contract records for per-contract Thor calls rather than assuming a single all-document prompt. Runtime fault, budget and retry tests remain separate acceptance specifications.

## Worked payment example: PAY-03

At 2027-01-28T12:00:00Z, C05 rent is INR 100000 and the visible January 24 cleared payment is INR 60000. Thor extracts the rent, allocation and simple daily rate from C05 clauses 4.1, 5.1 and 6.1. Norns retains INR 40000 principal and computes INR 40 for each of January 26, 27 and 28: INR 120 late charge, invoice subtotal INR 40120. Loki must support its overdue-payment claim and cannot charge on the already-paid INR 60000. Heimdall maps PAY1 and applies it once. Tyr may draft an internal payment reminder/escalation with citations and human review; it must not send a notice or act as the landlord. Odin reports these as scoped invoice figures, not the complete company balance.

OUT-07 demonstrates later approval evidence: hosting recovery becomes INR 0 while the downstream credit remains INR 15000. AMB-01 preserves the unknown Schedule B fee. PROJECT-B must not mature INR 600000 from an invoice without signed acceptance. LINK-01 anticipates an equipment/service term gap without declaring a future failure already observed. DEMO-PORTFOLIO contains the 14-to-15 document transition plus scoped rent and service-credit assertions.

## Unit versus end-to-end use

For a unit test, the harness may supply the selected agent with the controlled upstream fixture from worked_examples.json. These are deliberately authored test inputs, not real agent messages. Thor gets no downstream-answer fixture. Tyr OUT-07 has an explicit injected test dispute to exercise arbitration. That does not mean the real Loki and Heimdall must disagree; no-dispute runs accept no ruling.

For an end-to-end run, supply only selected PDFs, company context, clock/configuration and observations released by received_at. Each agent receives the actual outputs of upstream agents. Never inject golden upstream state into an end-to-end demonstration or present it as live computation. The harness/evaluator may read oracle/golden; the agents must not. Do not pass an entire vector containing expected_output into an agent prompt.

C08 is unavailable before its receipt. evaluator_checkpoint_visibility records expected known IDs and released event IDs at each clock position. These records and harness_source_refs are evaluator/harness-only and must not be included in agent input. Only input_spec is the proposed agent input, populated with actual upstream results for an end-to-end run. The harness reads schedules and releases observations; agents do not get raw future event files. Checkpoints do not invent financial answers where no assertion was authored. Preserve occurrence, receipt, effective time, correction and as-known history separately.

An exact-field pass alone is not an overall pass: narrative, evidence, role boundaries and honest completion must also pass. Budget/parse failures must be reported incomplete rather than relabeled successful. Golden normal-completion expectations assume mandatory processing succeeded. No fixed agent-call count, mandatory argument or automatic external action is required.
'''


if __name__=='__main__':
    build()
