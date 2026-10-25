"""Seven different manuscripts with grouped and nested clauses."""

ADDITIONAL_CONTRACTS = [{'id': 'C09',
  'title': 'Equipment Hire Deed',
  'type': 'lease',
  'parties': ['P01', 'P02'],
  'effective_date': '2027-01-04',
  'governing_law': 'India',
  'form': 'Equipment hire deed',
  'preamble': ('WITNESSETH',
               'Forge makes the equipment described below available on hire. Aurora accepts possession for its '
               'own operations, without acquiring title. The rent, custody and hand-back promises form the '
               'consideration for this deed.'),
  'articles': [('1',
                'PROPERTY ON HIRE',
                [('1.1',
                  'Forge Electronics Private Limited (P02, Owner) hires backup nodes EQ-DR01 and EQ-DR02 to '
                  'Aurora Software Private Limited (P01, Hirer). The nodes are reserved for the resident-data '
                  'recovery service under C14.'),
                 ('1.2',
                  'Aurora shall keep the nodes at UNIT-5, exercise reasonable care and neither sell nor pledge '
                  'them. Forge retains ownership. Consent to this hire is not a waiver of AX-7 procurement '
                  'restrictions under C03.')]),
               ('2',
                'HIRE ACCOUNT',
                [('2.1',
                  'Possession begins on 2027-01-04 and ends on 2027-06-30. There is no automatic extension. '
                  'Rent is INR 30,000 monthly, due on day 10 at 17:00 UTC against HIRE-YYYY-MM. No deposit or '
                  'payment interest is stipulated.'),
                 ('2.2',
                  'The monthly sum includes ordinary maintenance of both nodes. An additional equipment charge '
                  'cannot be inferred from the C14 service fee, which belongs to a separate agreement.')]),
               ('3',
                'HAND-BACK PROCEDURE',
                [('3.1',
                  'Both nodes must be physically received at Forge depot DEPOT-F by 2027-06-30 at 17:00 UTC. '
                  'Dispatch does not constitute return. The receipt must identify both asset IDs.'),
                 ('3.2',
                  'For every started UTC calendar date from 2027-07-01 when either node remains unreturned at '
                  '00:00 UTC, Aurora owes INR 2,000 in total, not per node. The hand-back charge is capped at '
                  'INR 20,000. A later return on that date does not reverse its charge.')]),
               ('4',
                'CUSTODY AND RESPONSIBILITY',
                [('4.1',
                  'Aurora is responsible for loss caused by its negligent custody, limited to INR 400,000 in '
                  'aggregate for both nodes. Ordinary wear is excluded. Each party indemnifies the other for '
                  'third-party intellectual-property claims caused by its own materials; fraud and those '
                  'indemnities are outside the custody cap.'),
                 ('4.2',
                  'Configuration information is confidential for 2 years after return. Personal data on a node '
                  'must be protected under applicable data-protection law and erased before hand-back; a blank '
                  'node alone is not proof of return.')]),
               ('5',
                'EARLY ENDING AND EXCEPTIONAL EVENTS',
                [('5.1',
                  'A material breach may be ended after a written notice and 7 calendar days to cure. Aurora '
                  'may end the hire for convenience on 30 calendar days notice, but rent through actual return '
                  'remains due.'),
                 ('5.2',
                  'Neither party may assign the deed without written consent. Force majeure requires prompt '
                  'written evidence and mitigation; it does not erase accrued rent or automatically postpone '
                  'hand-back. Indian law applies and Bengaluru courts have exclusive jurisdiction. Calendar '
                  'days and UTC govern all deadlines.')]),
               ('6',
                'DELIVERY OF THIS DEED',
                [('6.1',
                  'Mira Sen for Aurora and Anil Das for Forge record execution on 2026-12-22. Notices go to '
                  'aurora-legal@aurora.example and notices@forge.example respectively.')])],
  'schedules': [{'letter': 'A',
                 'title': 'EQUIPMENT REGISTER',
                 'columns': ['Entry', 'Asset', 'Quantity'],
                 'rows': [['Row 1', 'EQ-DR01 backup node', 'One'], ['Row 2', 'EQ-DR02 backup node', 'One']]}],
  'tables_position': 'front'},
 {'id': 'C10',
  'title': 'Resident Portal Service Order',
  'type': 'saas',
  'parties': ['P01', 'P03'],
  'effective_date': '2027-01-07',
  'governing_law': 'India',
  'form': 'SaaS commercial order',
  'preamble': ('ORDER ACCEPTANCE',
               'Willow orders the resident portal identified in this order. Aurora will operate the portal and '
               'Willow will pay the recurring price. This order is limited to APP-HABITAT and does not '
               'consolidate the companies other accounts.'),
  'articles': [('1',
                'ORDERED SERVICE',
                [('1.1',
                  'Aurora Software Private Limited (P01) shall operate APP-HABITAT for Willow Housing Private '
                  'Limited (P03), covering resident requests and housing-maintenance tickets. APP-HABITAT is '
                  'distinct from APP-ATLAS under C02.')]),
               ('2',
                'PRICE AND COLLECTION',
                [('2.1',
                  'Willow shall pay INR 60,000 per billing month by day 5 of the following month at 17:00 UTC, '
                  'using invoice PORTAL-YYYY-MM. The first period 2027-01-07 through 2027-01-31 is billed at '
                  'the full monthly fee and due on 2027-02-05. No late-payment interest is specified; taxes '
                  'are excluded.')]),
               ('3',
                'MONTHLY MEASUREMENT',
                [('3.1',
                  'The target availability is 99.5 percent per UTC calendar month. Calculate availability as '
                  '100 multiplied by (calendar minutes minus unavailable minutes) divided by calendar minutes. '
                  'Include every minute of the month and all observed unavailability; no maintenance exclusion '
                  'applies. The first scored month is February 2027; the initial partial billing month is not '
                  'measured for availability.'),
                 ('3.2',
                  'Only a complete monthly report identifying APP-HABITAT, the month and its unavailable '
                  'minutes supports the monthly measurement. A recovery exercise or an outage on another '
                  'application is not such a report.')]),
               ('4',
                'CREDIT NOTE',
                [('4.1',
                  'When monthly availability is below 99.5 percent, Willow may claim a credit of 5 percent of '
                  'that month fee. At exactly 99.5 percent no credit is due. Only one percentage credit '
                  'applies for the month, capped at INR 15,000.'),
                 ('4.2',
                  'A claim must be received at aurora-legal@aurora.example by 17:00 UTC on the tenth calendar '
                  'date following the month final date. Show an eligible credit separately until a claim is '
                  'established. The credit is the sole monetary remedy for the measured availability '
                  'shortfall.')]),
               ('5',
                'RESIDENT INFORMATION',
                [('5.1',
                  'Willow remains Controller and Aurora Processor for DS-HOUSING under C07. This service order '
                  'does not change those roles or treat every service interruption as an unauthorized '
                  'disclosure. Each party shall restrict access to resident information and comply with '
                  'applicable privacy law.')]),
               ('6',
                'ORDER DURATION',
                [('6.1',
                  'The service runs from 2027-01-07 through 2027-12-31 and renews for 12 months unless notice '
                  'is received 45 calendar days before expiry, at 17:00 UTC on that date. Either party may '
                  'terminate for material breach after written notice and a 10-day cure opportunity; '
                  'convenience termination requires 60 days notice.')]),
               ('7',
                'RISK AND GENERAL CONDITIONS',
                [('7.1',
                  'Other contractual damages are limited to INR 720,000, excluding fraud and each party '
                  'indemnity for its own third-party intellectual-property infringement. Assignment requires '
                  'written consent. Proven force majeure may excuse affected future performance after notice '
                  'and mitigation but not accrued payments. Indian law and Pune courts govern.')]),
               ('8',
                'ORDER SIGN-OFF',
                [('8.1',
                  'Mira Sen for Aurora and Kavya Paul for Willow record acceptance on 2026-12-22. Willow '
                  'notices are received at legal@willow.example. Days are calendar days and all times UTC.')])],
  'schedules': [{'letter': 'A',
                 'title': 'SUBSCRIPTION ORDER',
                 'columns': ['Entry', 'Service', 'Monthly fee'],
                 'rows': [['Row 1', 'APP-HABITAT resident portal', 'INR 60,000']]}],
  'tables_position': 'front'},
 {'id': 'C11',
  'title': 'Controller Integration Statement of Work',
  'type': 'other',
  'parties': ['P01', 'P02'],
  'effective_date': '2027-01-09',
  'governing_law': 'India',
  'form': 'Milestone statement of work',
  'preamble': ('PROJECT MANDATE',
               'Forge commissions a defined integration project rather than purchasing a continuing support '
               'service. The parties record deliverables, acceptance gates and earned milestones below. '
               'Completion of a demonstration and acceptance of a milestone are separate acts.'),
  'articles': [('1',
                'PROJECT BOUNDARY',
                [('1.1',
                  'Aurora Software Private Limited (P01, Integrator) shall integrate the AX-7 controller '
                  'interface for Forge Electronics Private Limited (P02, Client) as project INT-AX7. Hardware '
                  'procurement under C03 and the firmware tool license C06 retain their separate scope. This '
                  'statement of work takes effect on 2027-01-09 and continues until both milestones are '
                  'accepted and completed, unless ended earlier under its exit provisions; it does not '
                  'automatically renew.')]),
               ('2',
                'DELIVERABLE REGISTER',
                [('2.1',
                  'Milestone M1 is the controller-interface prototype, scheduled for demonstration by '
                  '2027-01-31.'),
                 ('2.1.1',
                  'M1 evidence comprises source code, interface test results and the demonstration record.'),
                 ('2.2',
                  'Milestone M2 is the production connector and deployment handbook, scheduled for '
                  'demonstration by 2027-02-28. Total project consideration is INR 1,200,000, allocated '
                  'equally between M1 and M2.')]),
               ('3',
                'ACCEPTANCE GATE',
                [('3.1',
                  'A milestone is accepted only when Anil Das for Forge signs a record identifying INT-AX7 and '
                  'that milestone. An unsigned record, a demonstration alone or silence does not establish '
                  'acceptance.'),
                 ('3.2',
                  'For each accepted milestone Forge owes INR 600,000 by 17:00 UTC on the fifteenth calendar '
                  'date after both signed acceptance and receipt of its invoice. No payment becomes due from '
                  'an invoice alone and no late-payment interest is specified.')]),
               ('4',
                'CHANGE CONTROL AND DELAY',
                [('4.1',
                  'A change to deliverables, dates or price requires a written change order signed by both '
                  'parties. A request to change scope is not an agreed amendment. Aurora shall identify '
                  'effects on other obligations rather than assuming they are waived.'),
                 ('4.2',
                  'If the M1 demonstration has not been delivered by 2027-01-31 at 17:00 UTC, Aurora owes '
                  'Forge INR 1,500 for each started UTC calendar date from 2027-02-01 on which the '
                  'demonstration remains undelivered at 00:00 UTC, capped at INR 30,000. Missing acceptance '
                  'alone does not prove the demonstration was late.')]),
               ('5',
                'RIGHTS IN THE WORK',
                [('5.1',
                  'Forge receives the completed project deliverables after payment of the relevant milestone. '
                  'Each party retains its pre-existing tools and indemnifies the other against third-party '
                  'infringement caused by materials it supplies. TOOL-CIRCUIT is not transferred merely '
                  'because it was used to develop a deliverable.')]),
               ('6',
                'PROJECT SAFEGUARDS',
                [('6.1',
                  'Designs, code and test data shall remain confidential for 3 years. Personnel must follow '
                  'applicable security and privacy requirements. Ordinary project damages are limited to INR '
                  '1,200,000, except fraud, wilful misconduct and the infringement indemnities.')]),
               ('7',
                'EXIT AND DISPUTE HANDLING',
                [('7.1',
                  'Either party may terminate an uncured material breach after written notice and 15 calendar '
                  'days to cure. Convenience termination needs 30 days notice; only accepted milestones and '
                  'separately agreed cancellation costs are payable. No unspecified cancellation fee is '
                  'implied.'),
                 ('7.2',
                  'Assignment needs consent. Force majeure requires notice, evidence and mitigation and does '
                  'not excuse accrued sums. The parties shall first seek executive resolution for 15 days; '
                  'Bengaluru courts then have exclusive jurisdiction under Indian law.')]),
               ('8',
                'AUTHORISATION',
                [('8.1',
                  'Mira Sen for Aurora and Anil Das for Forge record execution on 2026-12-23. Notices use '
                  'aurora-legal@aurora.example and notices@forge.example. UTC and calendar days apply.')])],
  'schedules': [{'letter': 'A',
                 'title': 'MILESTONE BILLING',
                 'columns': ['Entry', 'Milestone', 'Consideration'],
                 'rows': [['Row 1', 'M1 prototype', 'INR 600,000'],
                          ['Row 2', 'M2 production connector', 'INR 600,000']]}],
  'tables_position': 'front'},
 {'id': 'C12',
  'title': 'UNIT-5 Emergency Maintenance Work Order',
  'type': 'vendor',
  'parties': ['P01', 'P03'],
  'effective_date': '2027-01-11',
  'governing_law': 'India',
  'form': 'Facilities work order',
  'preamble': ('WORK AUTHORISATION',
               'This work order authorizes a defined urgent-maintenance response for UNIT-5. It is separately '
               'priced from the lease. It neither renews the premises nor grants a different occupancy right.'),
  'articles': [('1',
                'SERVICE LOCATION',
                [('1.1',
                  'Willow Housing Private Limited (P03, Maintenance Provider) shall support urgent electrical '
                  'and access-control faults at Aurora Software Private Limited (P01, Occupier) office UNIT-5. '
                  'The underlying occupancy remains governed by C05.')]),
               ('2',
                'DISPATCH INSTRUCTION',
                [('2.1',
                  'For an urgent ticket received by Willow, an acknowledgement identifying the ticket and '
                  'dispatch contact must be sent within 4 elapsed hours of that receipt. An acknowledgement at '
                  'the exact deadline is timely.'),
                 ('2.2',
                  'Measure from the evidenced provider_received_at time, not from a later monitoring-system '
                  'receipt. A ticket for another location does not trigger this work order.')]),
               ('3',
                'EMERGENCY COST ACCOUNT',
                [('3.1',
                  'If Willow misses the acknowledgement deadline, it shall reimburse Aurora actual emergency '
                  'repair costs approved by Kavya Paul and evidenced by a receipt, up to INR 25,000 per '
                  'ticket. No cost is payable from the missed deadline alone.'),
                 ('3.2',
                  'Do not charge the monthly fee again as an emergency penalty. Insurance or a hypothetical '
                  'contractor quotation does not establish an incurred approved cost.')]),
               ('4',
                'WORK-ORDER PRICE',
                [('4.1',
                  'The term is 2027-01-11 through 2027-12-31 without auto-renewal. Aurora pays Willow INR '
                  '15,000 per billing month by day 10 of the following month at 17:00 UTC against '
                  'MAINT-YYYY-MM. The first partial month is charged at the full fee and due on 2027-02-10. No '
                  'late interest is agreed; the fee is distinct from rent.')]),
               ('5',
                'CORRECTION AND CANCELLATION',
                [('5.1',
                  'A recurring service failure requires written notice and 7 calendar days for corrective '
                  'measures before termination for cause. Either party may cancel for convenience on 30 '
                  'calendar days notice, without cancelling the separate lease.')]),
               ('6',
                'RESPONSIBILITY FOR WORK',
                [('6.1',
                  'Willow is responsible for negligent maintenance and indemnifies Aurora for third-party '
                  'injury claims caused by that negligence. Other ordinary damages are capped at INR 180,000; '
                  'fraud and that injury indemnity are excluded from the cap.')]),
               ('7',
                'SITE INFORMATION',
                [('7.1',
                  'Access credentials and office plans are confidential. Each party shall comply with '
                  'applicable safety and data-protection requirements. No right to use resident data is '
                  'granted by access to this office.')]),
               ('8',
                'ADMINISTRATION',
                [('8.1',
                  'Indian law and Bengaluru courts apply. Assignment requires written consent. Force majeure '
                  'relief needs causal evidence, notice and mitigation; it does not excuse accrued fees. All '
                  'times are UTC. Notices go to aurora-legal@aurora.example and legal@willow.example.')]),
               ('9',
                'PURCHASER AND PROVIDER',
                [('9.1',
                  'Mira Sen for Aurora and Kavya Paul for Willow approve this work order on 2026-12-23.')])],
  'schedules': [{'letter': 'A',
                 'title': 'DISPATCH CARD',
                 'columns': ['Reference', 'Item', 'Agreed particulars'],
                 'rows': [['Row 1',
                           'Urgent UNIT-5 acknowledgement',
                           'Within 4 elapsed hours of provider receipt'],
                          ['Row 2',
                           'Approved repair reimbursement',
                           'Actual evidenced cost; cap INR 25,000 per ticket'],
                          ['Row 3', 'Separate maintenance fee', 'INR 15,000 per billing month']]}],
  'tables_position': 'front'},
 {'id': 'C13',
  'title': 'Mutual Engineering Confidentiality Undertaking',
  'type': 'nda',
  'parties': ['P01', 'P02'],
  'effective_date': '2026-12-20',
  'governing_law': 'India',
  'form': 'Mutual confidentiality undertaking',
  'preamble': ('THE UNDERTAKING',
               'In consideration of exchanging engineering information, each signatory gives the following '
               'promises to the other. The undertaking protects the exchange; it is not an order for hardware '
               'or an intellectual-property license.'),
  'articles': [('1',
                'PERSONS BOUND',
                [('1.1',
                  'Aurora Software Private Limited (P01) and Forge Electronics Private Limited (P02) are each '
                  'a Discloser when providing information and a Recipient when receiving it. No payment is due '
                  'merely for entering this undertaking.')]),
               ('2',
                'PROTECTED MATERIAL',
                [('2.1',
                  'Engineering drawings, source code, controller test reports and credentials disclosed in '
                  'confidence are Protected Material. Information already public without breach, independently '
                  'developed or lawfully obtained without restriction is excluded.')]),
               ('3',
                'RECIPIENT PROMISES',
                [('3.1',
                  'The Recipient shall use Protected Material solely for evaluating and implementing the '
                  'parties integration work, limit access to personnel with a need to know and equivalent '
                  'confidentiality duties, and apply reasonable access controls.'),
                 ('3.2',
                  'A mandatory legal disclosure requires prior notice where permitted and disclosure only to '
                  'the required extent. No ownership, sublicensing or general commercialization right is '
                  'granted.')]),
               ('4',
                'PERIOD OF PROTECTION',
                [('4.1',
                  'The exchange period is 2026-12-20 through 2027-12-19, without auto-renewal. Confidentiality '
                  'continues for 3 years after each disclosure. Either party may end future exchanges on 15 '
                  'days notice, without releasing accrued duties.')]),
               ('5',
                'RETURN OR DESTRUCTION',
                [('5.1',
                  'On an evidenced written request, the Recipient shall return or destroy the specified '
                  'material and supply a signed attestation by 17:00 UTC on the tenth calendar date following '
                  'receipt. Dispatch of a request alone is insufficient.'),
                 ('5.2',
                  'Copies legally required to be retained must be identified, segregated and remain protected. '
                  'No legally required retention is presumed without evidence. An attestation must identify '
                  'the request and material inventory.')]),
               ('6',
                'RELIEF AND LIMITS',
                [('6.1',
                  'A delayed return attestation permits a request for performance, injunctive relief and '
                  'supported damages but carries no fixed return-delay fee. Each party bears third-party '
                  'claims caused by its own unauthorized disclosure; an unknown damages amount is not zero.'),
                 ('6.2',
                  'For a proven unauthorized disclosure, the responsible Recipient owes INR 100,000 for each '
                  'distinct unauthorized recipient, capped at INR 300,000 in total under this undertaking. '
                  'Disclosure evidence must identify the protected material and recipient. A missing return '
                  'attestation does not itself prove a disclosure and must not trigger this sum.')]),
               ('7',
                'GENERAL PROMISES',
                [('7.1',
                  'Neither party may assign the undertaking without written consent. Applicable privacy law '
                  'governs personal data in the exchange. Force majeure does not make an intentional '
                  'disclosure permissible. The parties first seek resolution between legal contacts; Bengaluru '
                  'courts and Indian law govern remaining disputes.')]),
               ('8',
                'SIGNED UNDERTAKING',
                [('8.1',
                  'Mira Sen for Aurora and Anil Das for Forge record execution on 2026-12-19. Legal notices '
                  'use aurora-legal@aurora.example and notices@forge.example. UTC and calendar days apply.')])],
  'schedules': [{'kind': 'ANNEX',
                 'letter': 'A',
                 'title': 'INITIAL INFORMATION INVENTORY',
                 'columns': ['Entry', 'Material', 'Custodian'],
                 'rows': [['Row 1', 'AX-7 interface drawings', 'Aurora engineering'],
                          ['Row 2', 'Connector source specification', 'Forge engineering']]}]},
 {'id': 'C14',
  'title': 'Resident-Service Recovery Schedule',
  'type': 'other',
  'parties': ['P01', 'P03'],
  'effective_date': '2027-01-13',
  'governing_law': 'India',
  'form': 'Recovery service schedule',
  'preamble': ('SERVICE COMMITMENT',
               'The parties adopt this recovery schedule for resident-service continuity. It supplements their '
               'operating relationship without changing the monthly availability measurement or the '
               'data-processing allocation in the agreements identified below.'),
  'articles': [('1',
                'RECOVERY BOUNDARY',
                [('1.1',
                  'Aurora Software Private Limited (P01) shall provide recovery service DR-RESIDENT for Willow '
                  'Housing Private Limited (P03), covering DS-HOUSING and the APP-HABITAT recovery copy. '
                  'Controller and Processor roles remain as in C07.'),
                 ('1.2',
                  'The service uses the backup nodes hired under C09. Their hire ends on 2027-06-30, while '
                  'this schedule continues through 2027-12-15; no extension or substitute equipment is '
                  'attached.')]),
               ('2',
                'ACTIVATION AND RESTORATION',
                [('2.1',
                  'A recovery activation accepted from Kavya Paul starts a 4-elapsed-hour restoration window. '
                  'Aurora must restore the complete recovery copy within that window. An evidenced completion '
                  'at exactly 4 hours satisfies the target.'),
                 ('2.2',
                  'The activation and completion must identify DR-RESIDENT and the same activation ID. A '
                  'partial restore is not completion. A recovery exercise alone is not proof of production '
                  'unavailability or unauthorized disclosure.')]),
               ('3',
                'COMMERCIAL ADJUSTMENT',
                [('3.1',
                  'Willow pays Aurora INR 40,000 per billing month by day 5 of the following month at 17:00 '
                  'UTC against RECOVERY-YYYY-MM. The first partial month 2027-01-13 through 2027-01-31 is '
                  'billed at the full fee and due on 2027-02-05. No late-payment interest is specified.'),
                 ('3.2',
                  'A missed restoration window earns Willow a credit of 20 percent of the monthly recovery '
                  'fee, capped at INR 8,000 for the month. Only one such credit applies in a month and no '
                  'additional speculative loss is included.'),
                 ('3.3',
                  'Do not import the APP-ATLAS hosting thresholds from C01 or a monthly APP-HABITAT '
                  'availability result from C10 into this elapsed recovery test. Each remedy retains its own '
                  'evidence requirements.')]),
               ('4',
                'HANDLING OF RECOVERY COPIES',
                [('4.1',
                  'Recovered resident information remains confidential and subject to the processing '
                  'instructions and applicable privacy requirements under C07. Aurora shall control access and '
                  'maintain an audit of recovery operations. This schedule gives Willow no right to Aurora '
                  'development tools.')]),
               ('5',
                'SERVICE PERIOD AND EXIT',
                [('5.1',
                  'This schedule runs from 2027-01-13 through 2027-12-15 without automatic renewal. An uncured '
                  'material breach permits termination after notice and 10 calendar days to cure. Convenience '
                  'termination requires 45 days notice; accrued credits survive.')]),
               ('6',
                'REMAINING ALLOCATION',
                [('6.1',
                  'Recovery credits are the sole monetary remedy for the restoration-window miss. Other '
                  'ordinary damages are limited to INR 480,000, except fraud and third-party claims caused by '
                  'a party infringement or unauthorized disclosure, for which that party indemnifies the '
                  'other. Assignment needs consent; proven force majeure requires notice and mitigation. '
                  'Indian law and Pune courts govern.')]),
               ('7',
                'SERVICE ACCEPTANCE',
                [('7.1',
                  'Mira Sen for Aurora and Kavya Paul for Willow accept this schedule on 2026-12-24. Notices '
                  'use aurora-legal@aurora.example and legal@willow.example. UTC governs elapsed times and '
                  'calendar days govern date-based notices.')])],
  'schedules': [{'letter': 'A',
                 'title': 'RECOVERY PARAMETERS',
                 'columns': ['Reference', 'Item', 'Agreed particulars'],
                 'rows': [['Row 1', 'DR-RESIDENT restoration', 'Within 4 elapsed hours of accepted activation'],
                          ['Row 2', 'Monthly recovery fee', 'INR 40,000'],
                          ['Row 3', 'Missed-window credit', 'Credit: 20 percent of fee; monthly cap INR 8,000'],
                          ['Row 4', 'Backup equipment hire ends', '2027-06-30 under C09']]}]},
 {'id': 'C15',
  'title': 'AX-7 Product Warranty Undertaking',
  'type': 'supply',
  'parties': ['P01', 'P02'],
  'effective_date': '2027-01-14',
  'governing_law': 'India',
  'form': 'Product warranty undertaking',
  'preamble': ('WARRANTY GIVEN',
               'Forge warrants the covered controllers to Aurora on the conditions below. This undertaking '
               'addresses manufacturing defects after acceptance; it does not replace the delivery obligation '
               'or extend a customer deadline under another sale.'),
  'articles': [('1',
                'COVERED GOODS',
                [('1.1',
                  'Forge Electronics Private Limited (P02, Warrantor) gives Aurora Software Private Limited '
                  '(P01, Buyer) this undertaking for the AX-7 controllers supplied under PO-AX7 and C03. Each '
                  'claim must identify a covered serial number and its original conforming acceptance date.')]),
               ('2',
                'COVERAGE',
                [('2.1',
                  'Manufacturing defects arising in normal use are covered for 12 calendar months from the '
                  'original acceptance date. Physical misuse, unauthorized modification and ordinary wear are '
                  'excluded only when supported by evidence. A replacement does not reset the original '
                  'warranty period.')]),
               ('3',
                'CLAIM AND REPLACEMENT',
                [('3.1',
                  'A claim received at notices@forge.example must identify its claim ID, serial number, '
                  'acceptance record and defect evidence. A complete claim within coverage starts the '
                  'replacement process.'),
                 ('3.2',
                  'Forge shall deliver a conforming replacement by 17:00 UTC on the tenth calendar date '
                  'following receipt of a valid claim. Receipt at the exact deadline is timely; dispatch is '
                  'not delivery.'),
                 ('3.3',
                  'For each started UTC calendar date after the replacement due date when the replacement '
                  'remains undelivered at 00:00 UTC, Forge owes Aurora INR 1,000, capped at INR 10,000 per '
                  'claim. These charges do not extinguish the replacement duty. No full purchase-price refund '
                  'follows automatically from a delay.')]),
               ('4',
                'TRANSPORT AND INFORMATION',
                [('4.1',
                  'Forge bears reasonable return transport for an accepted covered claim. Aurora shall remove '
                  'data and protect credentials before return. Technical claim records are confidential for 2 '
                  'years, subject to mandatory legal disclosure and applicable privacy law.')]),
               ('5',
                'PRICE ALLOCATION',
                [('5.1',
                  'Warranty coverage is included in the price under C03. This undertaking creates no separate '
                  'warranty subscription fee and does not add another INR 500,000 to that purchase.')]),
               ('6',
                'REMEDIES AND FORUM',
                [('6.1',
                  'Ordinary warranty damages are capped at INR 250,000, excluding fraud and each party '
                  'indemnity for third-party claims caused by its own infringement. No damages amount follows '
                  'from that cap alone. Indian law and Bengaluru courts govern warranty disputes independently '
                  'of a downstream resale.')]),
               ('7',
                'CONTINUING RIGHTS',
                [('7.1',
                  'The undertaking operates from 2027-01-14 through 2027-12-20 without auto-renewal. Coverage '
                  'already earned by original acceptance survives until its own expiry. Material breach allows '
                  'termination of future obligations after 10 calendar days written cure notice, without '
                  'extinguishing earned coverage.'),
                 ('7.2',
                  'Neither party may assign this undertaking without consent. Force majeure relief requires '
                  'proof, notice and mitigation and does not automatically defeat a replacement claim. There '
                  'is no exclusivity beyond any separate express procurement promise.')]),
               ('8',
                'WARRANTOR AND BUYER',
                [('8.1',
                  'Mira Sen for Aurora and Anil Das for Forge record execution on 2026-12-24. Notices to '
                  'Aurora use aurora-legal@aurora.example. All dates use calendar days and UTC.')])],
  'schedules': [{'letter': 'A',
                 'title': 'WARRANTY HANDLING',
                 'columns': ['Reference', 'Item', 'Agreed particulars'],
                 'rows': [['Row 1', 'Covered goods', 'AX-7 controllers originally accepted under C03'],
                          ['Row 2',
                           'Coverage period',
                           'Coverage: 12 calendar months after original acceptance'],
                          ['Row 3', 'Replacement receipt', 'Tenth following calendar date at 17:00 UTC'],
                          ['Row 4',
                           'Replacement delay charge',
                           'INR 1,000 per started date after due date; cap INR 10,000']]}]}]
