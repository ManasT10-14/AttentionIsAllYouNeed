"""Authored observations and independent expected constants for C09-C15."""

def author_extra_cases(add,event):
    def ev(cid,eid,kind,when,**payload):
        return event(eid,kind,when,dict(agreement_ref=cid,**payload))
    for suffix,when,fee in [('A','2027-06-30T17:00:00Z','0'),('B','2027-07-03T12:00:00Z','6000')]:
        e=ev('C09','RETURN1','equipment_return_received',when,asset_ids=['EQ-DR01','EQ-DR02'],destination='DEPOT-F',receipt_ref='EQ-RETURN-001',recipient_party_id='P02')
        add('HIRE-'+suffix,'payments',['C09'],when,[e],'compliant' if suffix=='A' else 'breached',
            dict(handback_due='2027-06-30T17:00:00Z',handback_payable_inr=fee),['C09:3.1','C09:3.2'],
            ['Hand-back requires both nodes; started-date charges are one combined amount, not per asset.'],['Double the charge for two nodes','Charge before the return cutoff'],mappings={'RETURN1':['C09:3.1','C09:3.2']})
    for suffix,minutes,credit in [('A','120','0'),('B','240','3000')]:
        e=ev('C10','REPORT1','monthly_service_report','2027-03-01T09:00:00Z',application_id='APP-HABITAT',period_start='2027-02-01T00:00:00Z',period_end='2027-03-01T00:00:00Z',calendar_minutes='40320',unavailable_minutes=minutes,report_ref='PORTAL-FEB-2027')
        add('PORTAL-'+suffix,'outages',['C10'],'2027-03-01T09:00:00Z',[e],'compliant' if suffix=='A' else 'breached',
            dict(month='2027-02',eligible_credit_payable_inr=credit,availability_below_target=suffix=='B'),['C10:2.1','C10:3.1','C10:3.2','C10:4.1','C10:4.2'],
            ['February contains 40320 minutes; compare the unrounded availability with 99.5 percent. A qualifying credit is 5 percent of INR 60000 and remains subject to timely claim.'],['Use the C02 per-incident credit','Treat a monthly report as two separate credits'],mappings={'REPORT1':['C10:3.1','C10:4.1','C10:4.2']})
    for suffix,signed in [('A',True),('B',False)]:
        a=ev('C11','ACCEPT1','milestone_acceptance_recorded','2027-01-31T12:00:00Z',project_id='INT-AX7',milestone_id='M1',demonstration_delivered_at='2027-01-31T11:00:00Z',signature_ref='M1-ANIL-001' if signed else None,signed_by='Anil Das' if signed else None)
        inv=ev('C11','INVOICE1','invoice_received','2027-01-31T12:30:00Z',project_id='INT-AX7',milestone_id='M1',invoice_id='INT-M1-2027',amount='600000',currency='INR',recipient_id='P02')
        add('PROJECT-'+suffix,'payments',['C11'],'2027-02-16T09:00:00Z',[a,inv],'breached' if signed else 'unresolved',
            dict(payment_due='2027-02-15T17:00:00Z' if signed else None,matured_receivable_inr='600000' if signed else '0',demonstration_delay_payable_inr='0'),['C11:2.1','C11:3.1','C11:3.2','C11:4.2'],
            ['An invoice and signed acceptance are separate gates. The timely demonstration avoids the demonstration-delay charge even if acceptance evidence is missing.'],['Mature a fee from the invoice alone','Charge for late demonstration solely because acceptance is unsigned'],clarification=None if signed else 'Obtain the signed Forge milestone acceptance.',mappings={'ACCEPT1':['C11:3.1','C11:4.2'],'INVOICE1':['C11:3.2']})
    late=ev('C11','STATUS1','milestone_status_recorded','2027-02-03T09:00:00Z',project_id='INT-AX7',milestone_id='M1',demonstration_received=False,recorded_by='Anil Das')
    add('PROJECT-C','payments',['C11'],'2027-02-03T09:00:00Z',[late],'breached',
        dict(demonstration_due='2027-01-31T17:00:00Z',demonstration_delay_payable_inr='4500'),['C11:2.1','C11:4.2'],
        ['Three started dates, February 1-3, each incur INR 1500; the total remains below the INR 30000 cap.'],['Apply a fee per hour','Confuse demonstration with signed acceptance'],mappings={'STATUS1':['C11:2.1','C11:4.2']})
    for suffix,ack,cost in [('A','2027-02-01T12:00:00Z','0'),('B','2027-02-01T12:00:01Z','12000')]:
        ticket=ev('C12','TICKET1','helpdesk_ticket_received','2027-02-01T08:00:00Z',ticket_id='T-UNIT5-001',location_id='UNIT-5',priority='urgent',provider_received_at='2027-02-01T08:00:00Z',recipient_party_id='P03')
        ack_event=ev('C12','ACK1','ticket_acknowledged',ack,ticket_id='T-UNIT5-001',dispatch_contact='Willow facilities desk')
        events=[ticket,ack_event];mapping={'TICKET1':['C12:1.1','C12:2.1'],'ACK1':['C12:2.1']}
        if suffix=='B':
            events.append(ev('C12','COST1','emergency_cost_recorded','2027-02-01T13:00:00Z',ticket_id='T-UNIT5-001',amount='12000',currency='INR',receipt_ref='REPAIR-001',approved_by='Kavya Paul',approved_at='2027-02-01T12:15:00Z',incurred_by='P01'))
            mapping['COST1']=['C12:3.1']
        add('MAINT-'+suffix,'cure',['C12'],'2027-02-01T13:00:00Z',events,'compliant' if suffix=='A' else 'breached',
            dict(acknowledgement_due='2027-02-01T12:00:00Z',approved_cost_recoverable_inr=cost),['C12:2.1','C12:3.1','C12:3.2'],
            ['Exact-deadline acknowledgement is timely. Late acknowledgement supports only incurred, approved and receipted repair cost up to the ticket cap.'],['Automatically award INR 25000','Add the monthly fee as a penalty'],mappings=mapping)
    for suffix,timely in [('A',True),('B',False)]:
        request=ev('C13','REQ1','material_return_requested','2027-05-01T09:00:00Z',request_id='RETURN-ENG-001',sender_party_id='P02',recipient_party_id='P01',material_refs=['AX-7 interface drawings','Connector source specification'],receipt_ref='NDA-REQUEST-001')
        events=[request];mapping={'REQ1':['C13:5.1']}
        if timely:
            events.append(ev('C13','ATTEST1','return_attestation_received','2027-05-11T17:00:00Z',request_id='RETURN-ENG-001',material_refs=['AX-7 interface drawings','Connector source specification'],signed_by='Mira Sen',signature_ref='RETURN-ATTEST-001',method='destroyed',retained_copies=[]))
            mapping['ATTEST1']=['C13:5.1','C13:5.2']
        add('NDA-'+suffix,'cure',['C13'],'2027-05-11T17:00:01Z',events,'compliant' if timely else 'breached',
            dict(return_attestation_due='2027-05-11T17:00:00Z',fixed_return_delay_fee_inr='0',disclosure_proven=False),['C13:5.1','C13:5.2','C13:6.1','C13:6.2'],
            ['Return and signed attestation are due on the tenth following date. Missing attestation alone does not establish unauthorized disclosure or its damages.'],['Award disclosure damages without disclosure evidence','Assume no disclosure protection because exchanges ended'],mappings=mapping)
    disclosure=ev('C13','DISC1','disclosure_recorded','2027-05-03T10:00:00Z',material_ref='AX-7 interface drawings',disclosed_by='P01',recipient_party_id='P03',authorisation_status='not_granted',material_public=False,verified_by='Mira Sen',record_ref='DISC-001')
    add('NDA-C','adversarial',['C13'],'2027-05-03T10:00:00Z',[disclosure],'breached',
        dict(distinct_unauthorised_recipients=1,disclosure_payable_inr='100000'),['C13:2.1','C13:3.1','C13:6.2'],
        ['The protected drawing was disclosed to Willow without authorization; one distinct recipient triggers INR 100000, subject to the overall cap.'],['Charge the INR 300000 cap immediately','Treat each repeated copy to the same recipient as another recipient'],mappings={'DISC1':['C13:2.1','C13:3.1','C13:6.2']})
    for suffix,finish,credit in [('A','2027-03-02T12:00:00Z','0'),('B','2027-03-02T13:00:00Z','8000')]:
        a=ev('C14','ACT1','recovery_activated','2027-03-02T08:00:00Z',service_id='DR-RESIDENT',activation_id='REC-001',requested_by='Kavya Paul',accepted_by='Mira Sen')
        r=ev('C14','RESTORE1','recovery_completed',finish,service_id='DR-RESIDENT',activation_id='REC-001',complete=True,record_ref='RECOVERY-001')
        add('RECOVERY-'+suffix,'outages',['C07','C10','C14'],'2027-03-02T13:30:00Z',[a,r],'compliant' if suffix=='A' else 'breached',
            dict(restoration_due='2027-03-02T12:00:00Z',recovery_credit_payable_inr=credit),['C14:2.1','C14:2.2','C14:3.1','C14:3.2','C14:3.3','C10:3.2'],
            ['Four elapsed hours is timely; five hours earns 20 percent of the INR 40000 fee. The exercise alone is not a complete monthly availability report or a data disclosure.'],['Automatically add a C10 monthly credit','Infer unauthorized disclosure under C07'],mappings={'ACT1':['C14:2.1'],'RESTORE1':['C14:2.1','C14:2.2','C14:3.2']})
    for suffix,timely in [('A',True),('B',False)]:
        claim=ev('C15','CLAIM1','warranty_claim_received','2027-05-01T09:00:00Z',claim_id='RMA-001',serial_number='AX7-SN001',order_id='PO-AX7',original_acceptance_at='2027-02-07T12:00:00Z',defect='manufacturing solder failure',normal_use=True,unauthorised_modification=False,recipient_party_id='P02',receipt_ref='RMA-RECEIPT-001')
        events=[claim];mapping={'CLAIM1':['C15:1.1','C15:2.1','C15:3.1','C15:3.2']}
        if timely:
            events.append(ev('C15','REPLACE1','replacement_received','2027-05-11T17:00:00Z',claim_id='RMA-001',conforming=True,recipient_party_id='P01',receipt_ref='REPLACEMENT-001'))
            mapping['REPLACE1']=['C15:3.2','C15:3.3']
        else:
            events.append(ev('C15','STATUS1','replacement_status_recorded','2027-05-14T09:00:00Z',claim_id='RMA-001',replacement_received=False,recorded_by='Mira Sen'))
            mapping['STATUS1']=['C15:3.2','C15:3.3']
        add('WARRANTY-'+suffix,'payments',['C03','C15'],'2027-05-14T09:00:00Z',events,'compliant' if timely else 'breached',
            dict(replacement_due='2027-05-11T17:00:00Z',replacement_delay_recoverable_inr='0' if timely else '3000',separate_warranty_fee_inr='0'),['C15:2.1','C15:3.2','C15:3.3','C15:5.1'],
            ['Covered replacement is due May 11. If still missing, May 12-14 are three started charge dates. Warranty is already included in C03 purchase price.'],['Add another INR 500000 warranty fee','Infer an automatic full purchase-price refund'],mappings=mapping)
    add('LINK-01','dependencies',['C09','C14'],'2027-06-25T09:00:00Z',[],'at_risk',
        dict(equipment_hire_end='2027-06-30',recovery_service_end='2027-12-15'),['C09:2.1','C09:3.1','C09:3.2','C14:1.2','C14:5.1'],
        ['The backup-node hire ends before the dependent recovery service. Returning nodes avoids late charges but needs a continuity plan; keeping them can incur capped charges.'],['Assume a free hire extension','Assert that future recovery service has already failed'],action='Draft a hire extension or substitute-equipment proposal for human approval.')
    add('LINK-02','dependencies',['C01','C02'],'2027-12-01T09:00:00Z',[],'at_risk',
        dict(hosting_end='2027-12-14',application_service_end='2027-12-31',uncovered_calendar_dates=17),['C01:2.1','C02:1.1','C02:3.1'],
        ['Hosting expires without renewal before the dependent application service ends; December 15-31 are 17 uncovered calendar dates if no replacement or extension is agreed.'],['Assume automatic hosting renewal','Declare a future service breach as already observed'],action='Draft a hosting extension or migration plan for human approval.')
    outage=ev('C01','OUT1','service_restored','2027-01-16T11:30:00Z',provider_id='P02',service_id='SVC-ATLAS',application_id='APP-ATLAS',incident_id='INC-PORTFOLIO-01',start='2027-01-16T10:00:00Z',end='2027-01-16T11:30:00Z',scheduled_maintenance=False)
    claim=ev('C01','CLAIM1','service_credit_claim_received','2027-01-20T10:00:00Z',incident_id='INC-PORTFOLIO-01',sender_party_id='P01',recipient_party_id='P02',recipient_address='claims@forge.example',receipt_ref='CLAIM-PORTFOLIO-01')
    pay=ev('C05','PAY1','payment_cleared','2027-01-24T12:00:00Z',payer_id='P01',payee_id='P03',invoice_id='RENT-2027-01',amount='60000',currency='INR',bank_transaction_id='BANK-PORTFOLIO-01')
    arrival=ev('C08','UPLOAD1','contract_received','2027-01-25T09:00:00Z',document_id='C08',file='inputs/contracts/C08.pdf',uploader_party_id='P01')
    add('DEMO-PORTFOLIO','demo',[f'C{i:02}' for i in range(1,16) if i!=8],'2027-02-01T09:00:00Z',[outage,claim,pay,arrival],'breached',
        dict(initial_document_count=14,known_document_count=15,january_rent_principal_inr='40000',january_late_charge_inr='280',hosting_claim_recoverable_inr='10000',application_credit_payable_inr='15000',exclusive_procurement_conflict=True),
        ['C01:3.1','C01:5.1','C02:5.1','C03:17.1','C05:4.1','C05:5.1','C05:6.1','C08:1.1','C08:3.1'],
        ['Load all fourteen baseline PDFs, release C08 only at receipt, and retain all fifteen afterward. Separate the timely hosting claim from the downstream credit. Seven started rent-charge dates accrue January 26 through February 1. Preserve the new procurement conflict and do not treat the selected assertions as the entire company balance.'],
        ['Expose C08 before receipt','Net the hosting receivable into gross payable exposure without qualification','Claim the scoped amounts are the complete company balance'],
        checkpoints=[dict(clock='2027-01-24T09:00:00Z',known_document_count=14),dict(clock='2027-01-25T09:00:00Z',known_document_count=15,c08_effective=False),dict(clock='2027-01-28T12:00:00Z',january_rent_principal_inr='40000',january_late_charge_inr='120')],
        mappings={'OUT1':['C01:3.1','C02:5.1'],'CLAIM1':['C01:5.1'],'PAY1':['C05:4.1','C05:5.1','C05:6.1'],'UPLOAD1':['C08:1.1','C08:3.1']})
