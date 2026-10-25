"""Author copy-ready email fixtures and evaluator-only parser expectations."""
import json
from email.message import EmailMessage
from email.policy import SMTP
from pathlib import Path
from datetime import datetime
import re

ROOT=Path(__file__).resolve().parents[2]/'corpus'
TYPES=['PAYMENT_MADE','PAYMENT_LATE','PAYMENT_MISSED','INVOICE_RECEIVED','SERVICE_OUTAGE','SLA_BREACH',
       'DELIVERY_LATE','DELIVERY_RECEIVED','REGULATORY_CHANGE','PRICE_CHANGE','TERMINATION_NOTICE_RECEIVED',
       'RENEWAL_NOTICE_RECEIVED','PARTY_CHANGE','FORCE_MAJEURE','DISPUTE_RAISED','CUSTOM']
TYPE_MAP=dict(payment_cleared='PAYMENT_MADE',service_restored='SERVICE_OUTAGE',
              delivery_accepted='DELIVERY_RECEIVED',rule_change_published='REGULATORY_CHANGE',
              dispute_request_received='DISPUTE_RAISED',invoice_received='INVOICE_RECEIVED')


def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def indian_amount(value):
    whole,dot,fraction=str(value).partition('.')
    tail=whole[-3:];head=whole[:-3];groups=[]
    while head:
        groups.insert(0,head[-2:]);head=head[:-2]
    return 'INR '+','.join(groups+[tail])+(dot+fraction if dot else '')


def strict_fields(subject,body):
    """Fixture lint only. LLM fallback, ingestion and Gmail are not implemented here."""
    if not re.fullmatch(r'\[ODIN-EVENT\] [A-Z_]+ (?:ALL|UNKNOWN|[A-Za-z0-9_-]+(?:,[A-Za-z0-9_-]+)*)',subject):
        raise ValueError('invalid subject')
    head,sep,description=body.partition('DESCRIPTION:\n')
    if not sep:
        raise ValueError('missing DESCRIPTION')
    fields={}
    for line in head.splitlines():
        key,separator,value=line.partition(':')
        if not separator or key in fields:
            raise ValueError('malformed or duplicated header')
        fields[key]=value.strip()
    if not fields.get('EVENT_TYPE') or not fields.get('OCCURRED_AT'):
        raise ValueError('missing required key; request LLM fallback')
    if fields['EVENT_TYPE'] not in TYPES:
        raise ValueError('invalid event type')
    when=datetime.fromisoformat(fields['OCCURRED_AT'].replace('Z','+00:00'))
    if when.tzinfo is None:
        raise ValueError('timestamp must include timezone')
    if fields['EVENT_TYPE']!=subject.split()[1]:
        raise ValueError('subject/body type mismatch')
    if 'CONTRACT_ID' in fields and fields['CONTRACT_ID']!=subject.split()[2]:
        raise ValueError('subject/body contract mismatch')
    return dict(fields,DESCRIPTION=description)


def save_email(relative,subject,body):
    destination=ROOT/'inputs/emails'/relative
    destination.parent.mkdir(parents=True,exist_ok=True)
    message=EmailMessage(policy=SMTP)
    message['From']='operations@aurora.example';message['To']='odin-inbox@aurora.example'
    message['Subject']=subject
    message.set_content(body)
    destination.with_suffix('.eml').write_bytes(message.as_bytes())
    destination.with_suffix('.txt').write_text('Subject: '+subject+'\n\n'+body,encoding='utf-8')
    return destination.relative_to(ROOT).with_suffix('.eml').as_posix()


def route(event,default):
    p=event['payload'];kind=event['event_type']
    if p.get('agreement_ref'):
        return p['agreement_ref']
    if kind=='contract_received': return 'C08'
    if kind=='payment_cleared' or 'UNIT-5' in p.get('subject',''): return 'C05'
    if p.get('subscription_id')=='TOOL-CIRCUIT': return 'C06'
    if p.get('order_id')=='PO-AX7': return 'C03'
    if kind in ['service_restored','maintenance_approval_recorded']: return 'C01,C02'
    if kind in ['rule_change_published','safeguard_attested']: return 'C07'
    if kind in ['delivery_accepted','invoice_received']:
        return 'C04' if p.get('order_id')=='SO-AX7' else 'C03'
    return ','.join(default)


def build():
    index=[];parser_expectations=[]
    scenarios=json.loads((ROOT/'inputs/scenarios/index.json').read_text())
    for item in scenarios:
        scenario=json.loads((ROOT/item['file']).read_text());case=scenario['scenario_id']
        events=json.loads((ROOT/scenario['events_file']).read_text())
        for event in events:
            kind=TYPE_MAP.get(event['event_type'],'CUSTOM')
            if event['event_type']=='notice_received':
                kind='RENEWAL_NOTICE_RECEIVED' if 'renewal' in event['payload'].get('subject','').lower() else 'CUSTOM'
            contract_id=route(event,scenario['initial_contract_ids'])
            eid='EVT-'+case+'-'+event['event_id']
            subject=f'[ODIN-EVENT] {kind} {contract_id}'
            fields=[('EVENT_ID',eid),('EVENT_TYPE',kind),('OCCURRED_AT',event['occurred_at']),('CONTRACT_ID',contract_id)]
            p=event['payload']
            if 'amount' in p: fields.append(('AMOUNT',indian_amount(p['amount'])))
            reference=p.get('invoice_id') or p.get('incident_id') or p.get('order_id') or event['source_ref']
            fields.append(('REFERENCE',reference))
            observation=dict(observation_type=event['event_type'],source_ref=event['source_ref'],**p)
            if 'supersedes_event_id' in event:
                observation['supersedes_event_id']='EVT-'+case+'-'+event['supersedes_event_id']
            body=''.join(k+': '+v+'\n' for k,v in fields)+'DESCRIPTION:\n'+json.dumps(observation,indent=2)+'\n'
            strict_fields(subject,body)
            file=save_email(f'{case}/{event["event_id"]}',subject,body)
            index.append(dict(scenario_id=case,source_event_id=event['event_id'],email_event_id=eid,
                received_at=event['received_at'],file=file,copy_text=file.removesuffix('.eml')+'.txt'))
        # The adapter reads the schedule; only released email bytes reach the poller/agent.
        scenario['email_files']=[x['file'] for x in index if x['scenario_id']==case]
        dump(ROOT/item['file'],scenario)

    observations={
        'PAYMENT_MADE':('C05','AMOUNT: INR 60,000\nREFERENCE: RENT-2027-01\n','Bank transaction BANK-DEMO-01 cleared for the January rent invoice.'),
        'PAYMENT_LATE':('C05','AMOUNT: INR 1,00,000\nREFERENCE: RENT-2027-01\n','The January rent balance remains unpaid at the recorded time.'),
        'PAYMENT_MISSED':('C06','AMOUNT: INR 1,20,000\nREFERENCE: CIRCUIT-2027\n','No cleared payment is recorded for the annual invoice.'),
        'INVOICE_RECEIVED':('C03','AMOUNT: INR 5,00,000\nREFERENCE: INV-AX7\n','Invoice received for PO-AX7. Delivery acceptance evidence is not included.'),
        'SERVICE_OUTAGE':('C01,C02','COUNTERPARTY: Forge Electronics Private Limited\nREFERENCE: INC-DEMO-01\n','SVC-ATLAS and APP-ATLAS were unavailable from 2027-01-16T10:00:00Z through 2027-01-16T11:30:00Z. This incident was unscheduled.'),
        'SLA_BREACH':('C01,C02','REFERENCE: INC-DEMO-02\nSEVERITY_HINT: high\n','Sender alleges an SLA breach after 45 minutes of APP-ATLAS unavailability; verify the allegation against the agreements.'),
        'DELIVERY_LATE':('C03','REFERENCE: PO-AX7\n','LOT-AX7 has not arrived at DEPOT-A as of 2027-02-11T09:00:00Z.'),
        'DELIVERY_RECEIVED':('C04','REFERENCE: SO-AX7\n','Willow accepted all 100 conforming units of LOT-AX7 at SITE-W at the recorded time.'),
        'REGULATORY_CHANGE':('C07','REFERENCE: DSB-27-A\n','Data Standards Board notice applies to DS-HOUSING in REGION-NORTH. Required safeguard: access-review attestation. Effective 2027-04-01T00:00:00Z; Processor received on 2027-03-20T09:00:00Z.'),
        'PRICE_CHANGE':('C06','AMOUNT: INR 1,50,000\n','Vendor proposes an annual renewal price of INR 1,50,000. No signed price amendment is attached.'),
        'TERMINATION_NOTICE_RECEIVED':('C03','COUNTERPARTY: Forge Electronics Private Limited\n','Supplier received a notice asserting termination for delivery breach. Check prior breach notice, cure evidence and authority before accepting its effect.'),
        'RENEWAL_NOTICE_RECEIVED':('C05','REFERENCE: UNIT-5 NON-RENEWAL\n','Receipt addressed to notices@willow.example from authorized sender Mira Sen with subject UNIT-5 NON-RENEWAL.'),
        'PARTY_CHANGE':('ALL','COUNTERPARTY: Forge Electronics Private Limited\n','Forge reports a proposed acquisition and asks to assign its agreement. No signed consent is attached.'),
        'FORCE_MAJEURE':('ALL','COUNTERPARTY: Forge Electronics Private Limited\n','Supplier reports a flood affecting its depot and asks for relief. Causation and mitigation evidence have not been supplied.'),
        'DISPUTE_RAISED':('C04,C08','COUNTERPARTY: Willow Housing Private Limited\n','Willow requests one Mumbai proceeding for SO-AX7 and PROJECT-HABITAT claims. No joint forum agreement is attached.'),
        'CUSTOM':('UNKNOWN','','A document mentioning an AX-7 procurement commitment has arrived; identify the relevant agreements from the observation.'),
    }
    for n,kind in enumerate(TYPES,1):
        cid,extra,description=observations[kind]
        subject=f'[ODIN-EVENT] {kind} {cid}'
        occurred='2027-01-16T10:30:00+05:30' if kind=='CUSTOM' else '2027-02-11T09:00:00Z'
        body=f'EVENT_ID: EVT-TEMPLATE-{n:02}\nEVENT_TYPE: {kind}\nOCCURRED_AT: {occurred}\nCONTRACT_ID: {cid}\n'+extra+'DESCRIPTION:\n'+description+'\n'
        strict_fields(subject,body)
        file=save_email(f'templates/{kind}',subject,body)
        index.append(dict(template_type=kind,file=file,copy_text=file.removesuffix('.eml')+'.txt'))
        parser_expectations.append(dict(file=file,strict_result='parsed',event_type=kind,contract_id=cid))
    special=[
        ('NO_EVENT_ID','[ODIN-EVENT] CUSTOM UNKNOWN','EVENT_TYPE: CUSTOM\nOCCURRED_AT: 2027-01-16T10:30:00+05:30\nCONTRACT_ID: UNKNOWN\nDESCRIPTION:\nPlease identify the affected contract.\n','parsed'),
        ('MISSING_KEYS','[ODIN-EVENT] CUSTOM UNKNOWN','DESCRIPTION:\nSVC-ATLAS outage began on 2027-01-16 at 10:00 UTC and ended at 11:30 UTC.\n','needs_llm_fallback'),
        ('INVALID_DATE','[ODIN-EVENT] PAYMENT_MADE C05','EVENT_TYPE: PAYMENT_MADE\nOCCURRED_AT: not-a-date\nCONTRACT_ID: C05\nDESCRIPTION:\nRent payment record.\n','needs_llm_fallback'),
        ('INVALID_TYPE','[ODIN-EVENT] UNKNOWN_TYPE C05','EVENT_TYPE: UNKNOWN_TYPE\nOCCURRED_AT: 2027-01-16T10:00:00Z\nCONTRACT_ID: C05\nDESCRIPTION:\nUnrecognized event type.\n','needs_llm_fallback'),
    ]
    for label,subject,body,result in special:
        file=save_email('parser/'+label,subject,body)
        index.append(dict(parser_fixture_id=label,file=file,copy_text=file.removesuffix('.eml')+'.txt'))
        try:
            strict_fields(subject,body);actual='parsed'
        except ValueError:
            actual='needs_llm_fallback'
        assert actual==result
        parser_expectations.append(dict(file=file,strict_result=result))
    dump(ROOT/'inputs/emails/index.json',index)
    dump(ROOT/'oracle/email_parser_expectations.json',dict(scope='Strict fixture validation only; actual LLM fallback, parse_confidence, Gmail dedupe and rejection auto-reply must be tested in the real application.',
        event_type_enum=TYPES,cases=parser_expectations))
    print(f'Built {len(index)} email fixtures (.eml plus copy-ready .txt), covering {len(TYPES)} event types.')


if __name__=='__main__':
    build()
