"""Independently authored observations and expected outcomes; never imports contracts.

Build separate input and evaluator artifacts. This is a fixture packager, not Odin.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from extra_cases import author_extra_cases
import csv
import json

ROOT = Path(__file__).resolve().parents[1] / 'corpus'
CASES = []


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True)+'\n', encoding='utf-8')


def event(eid, kind, occurred, payload, received=None):
    return dict(event_id=eid, event_type=kind, occurred_at=occurred,
                received_at=received or occurred, source_ref='record:'+eid, payload=payload)


def payment(amount, when='2027-01-24T12:00:00Z', eid='PAY1', received=None, invoice='RENT-2027-01', transaction='BANK-001'):
    return event(eid, 'payment_cleared', when, dict(payer_id='P01',payee_id='P03',invoice_id=invoice,
        amount=str(amount),currency='INR',bank_transaction_id=transaction), received)


def notice(when, address='notices@willow.example', sender='Mira Sen'):
    return event('NOTICE1','notice_received',when,dict(sender_party_id='P01',recipient_party_id='P03',
        recipient_address=address,subject='UNIT-5 NON-RENEWAL',authorized_sender=sender,delivery_receipt='receipt-001'))


def outage(minutes, eid='OUT1', start='2027-01-16T10:00:00Z', scheduled=False, service='SVC-ATLAS', received=None):
    end=(datetime.fromisoformat(start.replace('Z','+00:00'))+timedelta(minutes=minutes)).isoformat().replace('+00:00','Z')
    return event(eid,'service_restored',end,dict(provider_id='P02',service_id=service,
        application_id='APP-ATLAS' if service=='SVC-ATLAS' else 'APP-OTHER',incident_id='INC-'+eid,
        start=start,end=end,scheduled_maintenance=scheduled),received)


def approval(received='2027-01-16T09:00:00Z', approved='2027-01-14T10:00:00Z'):
    return event('APPROVAL1','maintenance_approval_recorded',approved,dict(approver_party_id='P01',
        service_id='SVC-ATLAS',incident_id='INC-OUT1',window_start='2027-01-16T10:00:00Z',
        window_end='2027-01-16T12:00:00Z',approved_at=approved,signature_ref='record-approval-001'),received)


def delivery(eid, when, downstream=False):
    return event(eid,'delivery_accepted',when,dict(order_id='SO-AX7' if downstream else 'PO-AX7',
        lot_id='LOT-AX7',quantity=100,conforming=True,destination='SITE-W' if downstream else 'DEPOT-A',
        acceptance_ref='record-receipt-'+eid))


def rule(dataset='DS-HOUSING',received='2027-03-20T09:00:00Z', processor_received='2027-03-20T09:00:00Z'):
    return event('RULE1','rule_change_published','2027-03-19T09:00:00Z',dict(issuer='Data Standards Board',
        rule_id='FDB-27-A',dataset_id=dataset,region_id='REGION-NORTH',
        effective_at='2027-04-01T00:00:00Z',processor_received_at=processor_received,
        required_safeguards=['access-review-attestation']),received)


def add(cid, family, docs, clock, events, status, exact, evidence, required, forbidden,
        action='No external action; record the supported result.', clarification=None,
        checkpoints=None, mappings=None):
    CASES.append(dict(case_id=cid, family=family, docs=docs,clock=clock,events=events,
        expected=dict(business_status=status,scope='Only the obligations named in this case are scored; unrelated portfolio obligations remain independently assessable.',
            exact=exact,evidence=evidence,required_findings=required,forbidden_findings=forbidden,
            recommended_action=action,clarification=clarification,
            human_approval_required_for_external_action=True,
            completion_state='complete_with_unresolved_terms' if status=='unresolved' else 'complete_for_case_scope',
            checkpoints=checkpoints or [],event_mapping=mappings or {})))


def author_cases():
    add('REN-01','renewal',['C05'],'2027-05-31T17:00:00Z',[notice('2027-05-31T17:00:00Z')], 'compliant',
        dict(notice_cutoff='2027-05-31T17:00:00Z',renewal_committed_inr='0'),['C05:2.1','C05:3.1','C05:7.1'],
        ['Receipt exactly at cutoff is valid; current term continues through June 30.'],['Renewal fine','Early lease termination'],
        mappings={'NOTICE1':['C05:3.1']})
    add('REN-02','renewal',['C05'],'2027-05-31T17:00:01Z',[notice('2027-05-31T17:00:01Z')], 'at_risk',
        dict(notice_cutoff='2027-05-31T17:00:00Z',renewal_committed_inr='600000'),['C05:2.1','C05:3.1','C05:7.1'],
        ['Missed window commits July-December rent; distinguish future obligation from present penalty.'],['INR 600000 fine','Count July-December rent twice'],
        action='Draft an escalation memo and request negotiated release; human approval before sending.')
    add('REN-03','renewal',['C05'],'2027-05-31T17:00:01Z',[notice('2027-05-30T12:00:00Z',address='wrong@willow.example')], 'at_risk',
        dict(renewal_committed_inr='600000',notice_valid=False),['C05:2.1','C05:3.1','C05:7.1'],
        ['Wrong recipient makes the otherwise timely notice invalid.'],['Notice is valid solely because sent early'])
    add('REN-04','renewal',['C05'],'2027-05-31T16:59:59Z',[], 'at_risk',
        dict(notice_cutoff='2027-05-31T17:00:00Z',renewal_already_committed=False),['C05:2.1','C05:3.1'],
        ['Window remains open; warn before cutoff and recompute even without incoming events.'],['Renewal already unavoidable'],
        action='Draft non-renewal notice for immediate human review; do not send automatically.')
    for cid,clock,charge in [('PAY-01','2027-01-25T23:59:59Z','0'),('PAY-02','2027-01-26T00:00:00Z','100')]:
        add(cid,'payments',['C05'],clock,[],'breached',
            dict(invoice_id='RENT-2027-01',principal_inr='100000',late_charge_inr=charge),['C05:4.1','C05:6.1'],
            ['Rent is overdue; distinguish grace from payment due date and the fee trigger.'],['Compounded charge','Fee before grace ends'])
    add('PAY-03','payments',['C05'],'2027-01-28T12:00:00Z',[payment(60000)],'breached',
        dict(principal_inr='40000',late_charge_inr='120',invoice_total_inr='40120'),['C05:4.1','C05:6.1','C05:5.1'],
        ['Three started charge dates, Jan 26-28, each 40000 x 0.001 = INR 40.'],['Charge on original 100000 after partial payment'],
        action='Draft payment reminder with principal and accrued fee separated.',mappings={'PAY1':['C05:4.1','C05:6.1','C05:5.1']})
    add('PAY-04','payments',['C05'],'2027-01-28T12:00:00Z',[payment(100000)],'compliant',
        dict(principal_inr='0',late_charge_inr='0'),['C05:4.1','C05:6.1','C05:5.1'],
        ['Full cleared payment during grace prevents late charges.'],['Late charge despite cleared full payment'])
    add('PAY-05','payments',['C05'],'2027-01-28T12:00:00Z',[payment(60000),payment(60000,eid='PAY2')],'breached',
        dict(principal_inr='40000',late_charge_inr='120',distinct_payments=1),['C05:6.1','C05:5.1'],
        ['Two event IDs carrying the same bank transaction must be counted once.'],['Double subtraction of 60000'])
    add('PAY-06','payments',['C05'],'2027-03-20T12:00:00Z',[],'breached',
        dict(invoice_id='RENT-2027-01',principal_inr='100000',late_charge_inr='5000'),['C05:4.1','C05:6.1'],
        ['Only January invoice is scored; its 54 started late dates reach the INR 5000 cap.'],['Uncapped January late fee','Claim this is total portfolio rent'])
    add('PAY-07','payments',['C05'],'2027-01-28T12:00:00Z',[payment(100000,received='2027-01-29T09:00:00Z')],'breached',
        dict(principal_known_inr='100000',late_charge_known_inr='300',visible_event_count=0),['C05:4.1','C05:6.1','C05:5.1'],
        ['Before receipt the monitor has no payment evidence; label the knowledge limit.'],['Read the future payment early'],
        checkpoints=[dict(clock='2027-01-29T09:00:00Z',principal_inr='0',late_charge_inr='0',note='Replay from occurred_at: the newly received cleared payment actually preceded grace expiry; retain the earlier as-known view.')])
    add('DEP-01','dependencies',['C03','C04'],'2027-02-01T09:00:00Z',[],'at_risk',
        dict(upstream_deadline='2027-02-10T17:00:00Z',downstream_deadline='2027-02-08T17:00:00Z',gap_hours=48),
        ['C03:2.1','C03:7.1','C04:2.1','C04:4.1'],['Upstream latest promise is 48 hours after downstream deadline; evidence-backed planning gap.'],
        ['Supplier already breached on Feb 1','Downstream delay is excused automatically'],action='Draft amendment proposal aligning delivery commitments, for human approval.')
    add('DEP-02','dependencies',['C03','C04'],'2027-02-11T12:00:00Z',
        [delivery('DEL1','2027-02-07T08:00:00Z'),delivery('DEL2','2027-02-07T12:00:00Z',True)],'compliant',
        dict(upstream_delay_recoverable_inr='0',downstream_delay_payable_inr='0'),['C03:2.1','C03:5.1','C04:2.1','C04:5.1'],
        ['Actual deliveries are timely; original contractual planning gap still exists.'],['Actual breach inferred only from planned dates'])
    add('DEP-03','dependencies',['C03','C04'],'2027-02-15T12:00:00Z',[],'breached',
        dict(upstream_delay_recoverable_inr='10000',downstream_delay_payable_inr='35000',gross_payable_inr='35000',contingent_net_inr='25000'),
        ['C03:4.1','C04:4.1','C04:7.1'],['Five upstream charged dates and seven downstream charged dates; present both directions separately.'],
        ['Sum recoverable into payable exposure','Guaranteed collection from Forge'])
    for cid,minutes,credit,owed in [('OUT-01',30,'0','0'),('OUT-02',45,'0','15000'),('OUT-03',60,'0','15000'),('OUT-04',90,'10000','15000')]:
        add(cid,'outages',['C01','C02'],'2027-01-16T13:00:00Z',[outage(minutes)],'compliant' if owed=='0' else 'breached',
            dict(recoverable_credit_inr=credit,gross_payable_credit_inr=owed),['C01:3.1','C01:4.1','C01:5.1','C02:5.1','C02:6.1','C02:2.1'],
            ['Apply each threshold independently, with strict greater-than comparison.'],['Treat credit receivable as payable','Invent lost-profit damages'],
            action='Prepare timely hosting credit claim if eligible; track downstream credit separately; human approval before sending.',
            mappings={'OUT1':['C01:3.1','C01:4.1','C02:5.1','C02:6.1']})
    add('OUT-05','outages',['C01','C02'],'2027-01-16T13:00:00Z',[approval(),outage(90,scheduled=True)],'breached',
        dict(recoverable_credit_inr='0',gross_payable_credit_inr='15000',approval_lead_hours=48),['C01:4.1','C02:5.1','C02:6.1'],
        ['Exactly 48 hours approval qualifies; hosting exclusion does not propagate downstream.'],['Downstream credit excluded by upstream approval'])
    add('OUT-06','outages',['C01','C02'],'2027-01-16T13:00:00Z',[outage(90,scheduled=True)],'unresolved',
        dict(recoverable_credit_inr=None,recoverable_credit_upper_bound_inr='10000',gross_payable_credit_inr='15000'),['C01:3.1','C01:4.1','C02:6.1'],
        ['Request targeted approval evidence; preserve known downstream credit and uncertain hosting recovery.'],['Assume approval','Assume no approval'],
        clarification='Was this maintenance window approved by Aurora at least 48 hours before its start?')
    add('OUT-07','outages',['C01','C02'],'2027-01-17T09:00:00Z',[outage(90,scheduled=True),approval(received='2027-01-17T09:00:00Z')],'breached',
        dict(recoverable_credit_inr='0',gross_payable_credit_inr='15000'),['C01:4.1','C01:6.1','C02:6.1'],
        ['Later evidence proves earlier timely approval; revise hosting recovery with evidence lineage.'],['Erase prior uncertainty from audit history'],
        checkpoints=[dict(clock='2027-01-16T13:00:00Z',recoverable_credit_inr=None,completion_state='complete_with_unresolved_terms')])
    capped=[outage(90,'OUT1'),outage(90,'OUT2','2027-01-17T10:00:00Z'),outage(90,'OUT3','2027-01-18T10:00:00Z')]
    add('OUT-08','outages',['C01','C02'],'2027-01-18T13:00:00Z',capped,'breached',
        dict(recoverable_credit_inr='20000',gross_payable_credit_inr='45000'),['C01:3.1','C02:5.1'],
        ['Three distinct incidents reach separate monthly caps.'],['INR 30000 hosting recovery'])
    dup=outage(90); dup2=deepcopy(dup); dup2['event_id']='OUT-DUP'; dup2['source_ref']='record-record:repeat-log'
    add('OUT-09','outages',['C01','C02'],'2027-01-16T13:00:00Z',[dup,dup2],'breached',
        dict(distinct_incidents=1,recoverable_credit_inr='10000',gross_payable_credit_inr='15000'),['C01:6.1','C02:6.1'],
        ['Deduplicate incident identity even when event IDs differ.'],['Double credit for repeated log'])
    add('OUT-10','outages',['C01','C02'],'2027-01-16T13:00:00Z',[outage(90,service='SVC-OTHER')],'compliant',
        dict(recoverable_credit_inr='0',gross_payable_credit_inr='0'),['C01:1.1','C02:1.1'],
        ['Same provider with unrelated service is noise for these obligations.'],['Match solely on provider name'])
    for cid,events,clock,status in [
        ('REG-01',[rule()],'2027-04-01T00:00:01Z','breached'),
        ('REG-02',[rule(),event('ATT1','safeguard_attested','2027-03-31T12:00:00Z',dict(processor_id='P01',rule_id='FDB-27-A',dataset_id='DS-HOUSING',region_id='REGION-NORTH',safeguards=['access-review-attestation'],signature_ref='record-attestation-01'))],'2027-04-01T00:00:01Z','compliant')]:
        add(cid,'regulatory',['C07'],clock,events,status,
            dict(attestation_deadline='2027-04-01T00:00:00Z',monetary_fine_inr=None),['C07:5.1','C07:6.1','C07:7.1'],
            ['Apply supplied rule and later-of deadline; no supplied numeric fine.'],['Invent statutory fine','Describe rule as real law'],
            action='If missing, draft remediation request and escalation memo for human approval; otherwise record satisfaction.')
    add('REG-03','regulatory',['C07'],'2027-04-02T09:00:00Z',[rule(dataset='DS-OTHER')],'compliant',
        dict(applicable_rule=False,monetary_fine_inr=None),['C07:5.1'],['Unrelated dataset does not trigger the safeguard obligation.'],['Alert solely because any regulation arrived'])
    add('REG-04','regulatory',['C07'],'2027-04-12T17:00:01Z',
        [rule(received='2027-04-02T09:00:00Z',processor_received='2027-04-02T09:00:00Z')],'breached',
        dict(attestation_deadline='2027-04-12T17:00:00Z',monetary_fine_inr=None),['C07:6.1','C07:7.1'],
        ['Later receipt extends the contractual response deadline under the later-of rule.'],['Use publication date as processor receipt'])
    add('JUR-01','jurisdiction',['C04','C08'],'2027-02-02T09:00:00Z',
        [event('DISP1','dispute_request_received','2027-02-02T08:00:00Z',dict(requestor_id='P03',requested_forum='Mumbai',requested_scope=['SO-AX7','PROJECT-HABITAT'],request='Combine controller-supply and deployment-partnership claims in one proceeding.'))],
        'unresolved',dict(supply_forum='Pune',partnership_forum='Mumbai',joint_forum_agreement_present=False),['C04:8.1','C08:7.1'],
        ['A combined proceeding requires separate consent; route for legal clarification with both clauses.'],['Either contract is invalid','Mumbai automatically overrides Pune'],
        action='Draft forum-consent escalation memo for human review.',clarification='Will all relevant parties sign a joint forum agreement?')
    add('JUR-02','jurisdiction',['C04','C08'],'2027-02-02T09:00:00Z',[],'compliant',
        dict(supply_forum='Pune',partnership_forum='Mumbai'),['C04:8.1','C08:1.1','C08:7.1'],
        ['Independent claim scopes can retain different forums; no combined proceeding is requested.'],['Different courts alone prove a conflict'])
    breach=event('BREACH1','notice_received','2027-02-11T09:00:00Z',dict(sender_party_id='P01',recipient_party_id='P02',recipient_address='notices@forge.example',order_id='PO-AX7',subject='Delivery breach LOT-AX7',delivery_receipt='record-notice-receipt'))
    for cid,clock,events,eligible in [
        ('CUR-01','2027-02-21T17:00:00Z',[breach],False),
        ('CUR-02','2027-02-21T17:00:01Z',[breach],True),
        ('CUR-03','2027-02-21T17:00:01Z',[breach,delivery('DEL1','2027-02-21T16:00:00Z')],False)]:
        add(cid,'cure',['C03'],clock,events,'breached' if cid!='CUR-03' else 'compliant',
            dict(cure_deadline='2027-02-21T17:00:00Z',termination_eligible=eligible,automatically_terminated=False),['C03:2.1','C03:4.1','C03:5.1','C03:6.1','C03:9.1'],
            ['At the deadline cure is still allowed; only after the deadline can an uncured breach support a separate notice. Accrued delay recoverables survive cure.'],
            ['Automatic termination','Cure erases accrued delay charges'],action='If eligible, draft a separate termination notice for human approval; do not send.')
    for cid,clock,days,cutoff in [('AMD-01','2027-02-28T23:59:59Z',60,'2027-11-01T17:00:00Z'),('AMD-02','2027-03-01T00:00:00Z',30,'2027-12-01T17:00:00Z')]:
        add(cid,'amendments',['C06'],clock,[],'compliant',
            dict(applicable_notice_days=days,applicable_cutoff=cutoff,annual_price_inr='120000'),['C06:3.1','C06:4.1','C06:8.1','C06:19.1','C06:19.2'],
            ['Apply amendment prospectively; unchanged pricing and missing Schedule B survive. Show historical applicability separately from known future change.'],
            ['Amendment applies before effective time','Schedule B invented by amendment'])
    add('AMB-01','ambiguity',['C06'],'2027-02-01T09:00:00Z',
        [event('EXIT1','early_exit_requested','2027-02-01T08:00:00Z',dict(requestor_id='P01',subscription_id='TOOL-CIRCUIT',requested_exit_at='2027-02-15T17:00:00Z'))],
        'unresolved',dict(migration_fee_inr=None,schedule_b_present=False),['C06:6.1','C06:7.1','C06:8.1'],
        ['Request Schedule B and evaluate supported termination route; request alone is not termination.'],['Assume free exit','Invent fee from annual price'],
        clarification='Obtain executed Schedule B and identify the contractual early-termination basis. The requested February 15 exit also falls short of the 30-day convenience notice in C06 clause 18.1.',action='Draft targeted clarification and legal escalation for human review.')
    add('AMB-02','ambiguity',['C06'],'2027-12-01T17:00:00Z',
        [event('LNOTICE1','notice_received','2027-12-01T17:00:00Z',dict(sender_party_id='P01',recipient_party_id='P02',recipient_address='notices@forge.example',subject='TOOL-CIRCUIT non-renewal',subscription_id='TOOL-CIRCUIT',delivery_receipt='record-circuit-receipt'))],
        'compliant',dict(renewal_prevented=True,migration_fee_applicable=False),['C06:3.1','C06:7.1','C06:19.1'],
        ['Term-end non-renewal does not trigger early-termination migration fee; missing schedule remains noted.'],['Demand missing early-exit fee for normal non-renewal'])
    add('ARR-01','arrival',['C02','C03','C04','C05'],'2027-02-01T09:00:00Z',
        [event('UPLOAD1','contract_received','2027-01-25T09:00:00Z',dict(document_id='C08',file='inputs/contracts/C08.pdf',uploader_party_id='P01'))],
        'at_risk',dict(retained_contract_ids=['C02','C03','C04','C05','C08'],c08_effective_at='2027-02-01T00:00:00Z',c02_service_credit_inr='15000'),
        ['C02:5.1','C02:18.1','C03:17.1','C04:1.1','C05:1.1','C08:1.1','C08:2.1','C08:6.1','C08:3.1'],['Extract newcomer, link its Aurora/Willow parties to C04 and C05, preserve those agreements and unrelated C02, and detect the C03/C08 exclusive-procurement conflict; no pre-effective C08 accrual.'],
        ['Automatically replace C02','C08 silently changes service credits'],
        checkpoints=[dict(clock='2027-01-24T09:00:00Z',known_contract_ids=['C02','C03','C04','C05']),dict(clock='2027-01-25T09:00:00Z',known_contract_ids=['C02','C03','C04','C05','C08'],c08_effective=False)],
        mappings={'UPLOAD1':['C08:1.1','C08:2.1','C08:6.1']})
    corrected=outage(45,eid='CORR1'); corrected['payload']['incident_id']='INC-OUT1'; corrected['supersedes_event_id']='OUT1'; corrected['received_at']='2027-01-17T09:00:00Z'
    add('OUT-11','outages',['C01','C02'],'2027-01-17T09:00:00Z',[outage(90),corrected],'breached',
        dict(distinct_incidents=1,recoverable_credit_inr='0',gross_payable_credit_inr='15000'),['C01:3.1','C01:6.1','C02:5.1','C02:6.1'],
        ['Corrected 45-minute duration supersedes 90-minute observation; retain old version in audit.'],['Treat correction as new incident','Retain obsolete 90-minute hosting recovery'])
    add('TRAP-01','ambiguity',['C03'],'2027-01-20T09:00:00Z',
        [event('CHANGE1','change_request_received','2027-01-19T09:00:00Z',dict(requestor_id='P01',order_id='PO-AX7',request='Please propose an earlier delivery date.'))],
        'unresolved',dict(response_deadline=None),['C03:19.1'],
        ['The reasonable-time obligation has no numeric response deadline; request clarification.'],['Invent a 24-hour deadline','Declare response late after exactly one day'],
        clarification='Agree a measurable response time for delivery-change requests.',mappings={'CHANGE1':['C03:19.1']})
    add('TRAP-02','ambiguity',['C04'],'2027-03-10T09:00:00Z',
        [delivery('DEL1','2027-02-07T12:00:00Z',True),event('INV1','invoice_received','2027-02-07T12:00:00Z',dict(invoice_id='INV-SOAX7',order_id='SO-AX7',amount='650000',currency='INR',recipient_id='P03'))],
        'unresolved',dict(payment_due='2027-03-09T17:00:00Z',principal_receivable_inr='650000',late_interest_inr=None),['C04:3.1','C04:19.1'],
        ['Invoice and acceptance establish the due date; blank percentage prevents calculation of late interest.'],['Assume the blank rate is zero','Borrow the lease interest rate'],
        clarification='Obtain the agreed completed interest percentage.',mappings={'DEL1':['C04:3.1','C04:5.1'],'INV1':['C04:3.1','C04:19.1']})
    add('TRAP-03','ambiguity',['C08'],'2027-02-02T09:00:00Z',[],
        'unresolved',dict(convenience_notice_days=None,conflicting_notice_days=[30,60]),['C08:18.1','C08:19.1'],
        ['Two notice periods govern the same convenience termination without an agreed hierarchy.'],['Silently choose the shorter or longer notice period'],
        clarification='Obtain a signed clarification of the convenience-termination notice period.')
    add('TRAP-04','dependencies',['C03','C08'],'2027-02-01T09:00:00Z',[],
        'at_risk',dict(exclusive_supplier='P02',second_supplier='P03',conflicting_product='AX-7',second_purchase_inr='600000'),['C03:17.1','C08:2.1','C08:3.1'],
        ['C03 restricts procurement from another supplier during the C08 procurement commitment; request waiver or amendment.'],['Assume a Forge waiver exists','Assume delivery or payment already occurred'],
        action='Draft a waiver request or procurement amendment proposal for human review.')
    add('TRAP-05','dependencies',['C02','C05'],'2027-05-31T17:00:00Z',[notice('2027-05-31T17:00:00Z')],
        'at_risk',dict(office_term_end='2027-06-30',office_dependent_service_term_end='2027-12-31',lease_renewal_prevented=True),['C02:3.1','C02:7.1','C05:2.1','C05:3.1'],
        ['Valid non-renewal avoids future lease commitment but creates a continuity gap for required UNIT-5 support.'],['Assume relocation approval','Declare the service term ends with the lease'],
        action='Draft a relocation approval request or lease-extension proposal for human review.',mappings={'NOTICE1':['C05:2.1','C05:3.1','C02:7.1']})
    add('TRAP-06','adversarial',['C04'],'2027-01-15T09:00:00Z',[],
        'at_risk',dict(aurora_indemnifies_willow_negligence=True,willow_reciprocal_indemnity=False,indemnity_excluded_from_cap=True,quantified_indemnity_exposure_inr=None),['C04:11.1','C04:12.1'],
        ['One-sided indemnity includes Willow negligence and is excluded from the aggregate cap; exposure needs a supported claim, not a guessed amount.'],['Apply INR 1000000 cap to the excluded indemnity','Assume indemnity claim has already arisen'],
        action='Draft a mutual-indemnity and cap amendment proposal for human approval.')


def build():
    author_cases()
    author_extra_cases(add,event)
    index=[]
    expected=[]
    for case in CASES:
        cid=case['case_id']
        events=sorted(case['events'],key=lambda e:(e['received_at'],e['event_id']))
        dump(ROOT/f'inputs/events/{cid}.json',events)
        baseline='2027-01-25T09:00:00Z' if 'C08' in case['docs'] else '2027-01-15T09:00:00Z'
        clocks=sorted(set([baseline,case['clock']]+[x['clock'] for x in case['expected']['checkpoints']]))
        scenario=dict(schema_version='2.0',scenario_id=cid,baseline_clock=baseline,
            initial_contract_ids=case['docs'],events_file=f'inputs/events/{cid}.json',clock_checkpoints=clocks,
            reset_required=True,visibility_rule='received_at <= clock; apply visible observations using occurred_at and contractual effective dates; retain as-known history',
            ingestion_rule='Only initial PDFs are visible until a contract_received event releases its referenced PDF.')
        dump(ROOT/f'inputs/scenarios/{cid}.json',scenario)
        index.append(dict(scenario_id=cid,file=f'inputs/scenarios/{cid}.json'))
        if not case['expected']['event_mapping']:
            # This records expected clause routing, not additional data in the event feed.
            routes={
                'payment_cleared':['C05:4.1','C05:6.1','C05:5.1'],
                'service_restored':['C01:1.1','C01:3.1','C01:4.1','C01:6.1','C02:1.1','C02:5.1','C02:6.1'],
                'maintenance_approval_recorded':['C01:4.1','C01:6.1','C02:6.1'],
                'rule_change_published':['C07:5.1','C07:6.1','C07:7.1','C07:4.1'],
                'safeguard_attested':['C07:6.1'],
                'delivery_accepted':['C03:2.1','C03:4.1','C03:5.1','C03:6.1','C04:2.1','C04:4.1','C04:5.1'],
                'dispute_request_received':['C04:8.1','C08:7.1'],
                'early_exit_requested':['C06:6.1','C06:7.1'],
                'notice_received':['C05:3.1'] if 'C05' in case['docs'] else ['C06:3.1','C06:19.1'] if 'C06' in case['docs'] else ['C03:6.1','C03:9.1'],
            }
            for e in events:
                mapping=[r for r in routes.get(e['event_type'],[]) if r.split(':')[0] in case['docs']]
                if e['payload'].get('service_id')=='SVC-OTHER' or e['payload'].get('dataset_id')=='DS-OTHER':
                    mapping=[]
                case['expected']['event_mapping'][e['event_id']]=mapping
        expected.append(dict(case_id=cid,family=case['family'],assert_at=case['clock'],**case['expected']))
    dump(ROOT/'inputs/scenarios/index.json',index)
    dump(ROOT/'oracle/expected_cases.json',dict(schema_version='2.0',independence='Manually authored expected constants and rubrics; no contract generator imports or model predictions. Same-author arithmetic checks are not an independent human review.',
        test_status_definition='PASS means observed output satisfies exact fields and narrative/evidence rubrics. A detected breach or preserved uncertainty can pass.',
        scoring=dict(exact='IDs, booleans, dates and decimal strings must match; null means unknown, not zero.',
            narrative='Each required finding must be supported, no forbidden finding may appear, and the cited clauses must support the conclusion. Semantically equivalent explanations are accepted.',
            confidence='Require evidence-aware confidence and uncertainty explanation; do not require a fixed score.',
            actions='Any externally usable notice or amendment draft must include exact clauses and human-approval status. Never send it as part of evaluation.'),cases=expected))
    with (ROOT/'oracle/requirement_coverage.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['family','case_ids','corpus_evidence','runtime_proof'])
        for family in dict.fromkeys(c['family'] for c in CASES):
            group=[c for c in CASES if c['family']==family]
            w.writerow([family,';'.join(c['case_id'] for c in group),';'.join(sorted(set(x for c in group for x in c['expected']['evidence']))),'pending real Odin execution'])
    print(f'Built {len(CASES)} isolated scenarios and evaluator cases.')


if __name__=='__main__':
    build()
