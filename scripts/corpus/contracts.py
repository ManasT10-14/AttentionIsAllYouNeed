"""Individually drafted agreements. Never ingest generator source."""

CONTRACTS = [{'id': 'C01',
  'title': 'Cloud Hosting Agreement',
  'parties': ['P01', 'P02'],
  'clauses': [('HOSTING SCOPE AND CAPACITIES',
               'Aurora Software Private Limited (P01, Customer) and Forge Electronics Private Limited (P02, '
               'Provider) agree to hosting service SVC-ATLAS for Aurora application APP-ATLAS. The same '
               'parties also contract in different capacities under C02; this hosting agreement retains its '
               'own obligations and remedies. Company legal notice address: aurora-legal@aurora.example. '
               'Counterparty legal notice address: legal@forge.example.'),
              ('TERM AND FEES',
               'This agreement is signed on 2026-12-15 and runs from 2026-12-15 through 2027-12-14 '
               'inclusive. It expires without automatic renewal. The fixed hosting fee is INR 200,000 per '
               'calendar month, due on the fifth day of that month at 17:00 UTC. No late-payment charge is '
               'agreed. The initial 2026-12-15 through 2026-12-31 period is charged at the full monthly fee '
               'and is first due on 2026-12-20 at 17:00 UTC; the regular fifth-day rule applies thereafter.'),
              ('SERVICE CREDIT',
               'For each distinct incident of more than 60 consecutive minutes of complete unavailability of '
               'SVC-ATLAS, Provider owes Customer a credit of INR 10,000. An incident of exactly 60 minutes '
               'does not qualify. Distinct incidents must have separate restoration and outage records. '
               'Total credits are capped at INR 20,000 per UTC calendar month of outage start. Credits are '
               'recoverable by Customer and are not Customer liabilities.'),
              ('MAINTENANCE EXCLUSION',
               'An incident is excluded from clause 3.1 of C01 only if Customer approved that specific '
               'maintenance window at least 48 hours before its start and the outage was wholly inside that '
               'window. Provider scheduling alone is not approval. If approval evidence is missing, '
               'applicability is unresolved pending evidence; do not presume approval or its absence.'),
              ('CREDIT PROCEDURE AND REMEDY',
               'Customer must email a claim identifying the incident within 10 calendar days after '
               'restoration to claims@forge.example. A valid claim is due by 17:00 UTC on the tenth '
               'following calendar date. Credits are the sole monetary remedy for service unavailability '
               'under this agreement; no downstream damages are reimbursed.'),
              ('INCIDENT EVIDENCE',
               'Provider restoration logs identify incident ID, service ID, start, end and any scheduled '
               'window. A later signed approval record may supply earlier approval evidence. A repeated log '
               'for the same incident is not a second outage. Corrected records supersede the identified '
               'prior record without creating another incident.'),
              ('NOTICE AND CURE',
               'For a material breach other than service unavailability, written notice must be received at '
               'legal@forge.example. Provider has 10 calendar days after receipt to cure, ending at 17:00 '
               'UTC on the tenth following date. Customer may serve a separate termination notice only after '
               'that deadline if the breach remains uncured.'),
              ('DISPUTES AND SCOPE',
               'Indian law governs this agreement. Courts in Bengaluru have exclusive jurisdiction over '
               'disputes under this agreement. This provision neither chooses the forum for other contracts '
               'nor promises consolidated proceedings.'),
              ('CLOCK AND INTERPRETATION',
               'All times are UTC and all days are calendar days. There is no weekend or holiday adjustment. '
               'A deadline stated as a date ends at 17:00 UTC unless another time is explicit. Financial '
               'amounts exclude taxes, which are outside this agreement. No terms from an absent document '
               'may be assumed.'),
              ('HOSTING ACCEPTANCE',
               'Mira Sen for Aurora and Anil Das for Forge record execution on 2026-12-15.'),
              ('LIMITATION OF LIABILITY',
               'The monthly service-credit cap in clause 3.1 is INR 20,000. For other claims, each party '
               'aggregate liability is capped at INR 1,000,000, except fraud, wilful misconduct and '
               'indemnity obligations. Downstream service liabilities are not reimbursed under this '
               'agreement.'),
              ('HOSTING CLAIM DEFENCE',
               'A party whose supplied hosting materials infringe third-party intellectual property, or '
               'whose unauthorized disclosure produces a third-party claim, shall indemnify the other for '
               'that claim and reasonable defense costs. The protected party must give prompt notice and '
               'cooperate in the defense.'),
              ('HOSTING INFORMATION',
               'Hosting configurations, access keys and the other party commercial information shall be '
               'disclosed only to personnel who need them for this hosting service and owe confidentiality '
               'duties. Use for another purpose is prohibited. Protection continues for 3 years after '
               'termination, except for information public without breach.'),
              ('OPERATING REQUIREMENTS',
               'Each party must comply with laws applicable to its role in hosting facilities. This includes '
               'the Digital Personal Data Protection Act, 2023 where applicable and GDPR where its '
               'processing scope applies. Personal-data processing requires access controls and a documented '
               'incident-response procedure. No ISO certification is promised.'),
              ('HOSTING TRANSFER',
               'Transfer of the hosting agreement needs the other party written consent. An affiliate '
               'transfer is permitted on 30 calendar days written notice only if the original party remains '
               'liable. A change of control does not substitute a new party or waive required consent.'),
              ('EXCEPTIONAL HOSTING DISRUPTION',
               'Relief for an event beyond reasonable control is confined to the affected obligations in '
               'hosting facilities. The affected party must give written notice within 5 calendar days after '
               'discovery, explain causation and provide mitigation evidence. Accrued payments remain '
               'payable. Neither an outage nor supplier delay qualifies automatically.'),
              ('ALTERNATIVE HOSTS',
               'The parties remain free to enter other arrangements outside the scope of hosting facilities. '
               'This agreement grants no exclusivity or non-compete except any restriction expressly stated '
               'in this clause.'),
              ('ORDINARY HOSTING EXIT',
               'Either party may end future hosting facilities for convenience by written notice received at '
               'the other party legal notice address at least 30 calendar days before termination. Accrued '
               'payment obligations, express survival provisions and the stated conditions of any early-exit '
               'fee continue to apply.')],
  'type': 'vendor',
  'effective_date': '2026-12-15',
  'governing_law': 'India',
  'form': 'Hosting services undertaking',
  'preamble': ('SERVICE UNDERTAKING',
               'Forge agrees to make the hosting service available to Aurora on the operational and '
               'commercial conditions below. These hosting promises stand independently of the parties '
               'application-service relationship.'),
  'schedules': [{'letter': 'A',
                 'title': 'FEES',
                 'columns': ['Reference', 'Service / remedy', 'Amount', 'Payment / limit'],
                 'rows': [['Row 1',
                           'SVC-ATLAS hosting',
                           'INR 200,000 per month',
                           'Due on day 5 at 17:00 UTC'],
                          ['Row 2', 'Qualifying incident credit', 'INR 10,000', 'Monthly cap INR 20,000']]}]},
 {'id': 'C02',
  'title': 'Customer Application Service Agreement',
  'parties': ['P01', 'P02'],
  'clauses': [('APPLICATION COMMISSION',
               'Aurora Software Private Limited (P01, Service Supplier) supplies APP-ATLAS to Forge '
               'Electronics Private Limited (P02, Customer). APP-ATLAS depends entirely on Forge service '
               'SVC-ATLAS identified in Aurora hosting agreement C01. Forge is the hosting provider under '
               'C01 and the application customer under C02; these capacities and payment flows remain '
               'separate. Company legal notice address: aurora-legal@aurora.example. Counterparty legal '
               'notice address: legal@forge.example.'),
              ('LIABILITY BOUNDARY',
               'The service credits in clause 5.1 of C02 are the sole monetary remedy for unavailability. Do '
               'not add speculative lost profits. Recoverable hosting credits under C01 do not reduce the '
               'gross amount owed to Forge; show any net illustration separately and label it contingent on '
               'recovery.'),
              ('TERM AND FEES',
               'Signed on 2026-12-16; effective 2027-01-01 through 2027-12-31 inclusive, with no automatic '
               'renewal. Forge pays Aurora INR 300,000 monthly by the fifth day at 17:00 UTC. No late charge '
               'is specified.'),
              ('TIME AND EVIDENCE',
               'All dates and times use UTC, with calendar days and no holiday adjustments. Date-only '
               'deadlines end at 17:00 UTC. Logs linking SVC-ATLAS to APP-ATLAS are sufficient incident '
               'observations for this service chain. Financial amounts exclude taxes.'),
              ('CUSTOMER SERVICE REMEDY',
               'For each distinct incident of more than 30 consecutive minutes of complete APP-ATLAS '
               'unavailability, Aurora owes Forge a service credit of INR 15,000, capped at INR 45,000 per '
               'UTC month of outage start. Exactly 30 minutes does not qualify. This credit accrues '
               'automatically on restoration; Forge need not file a claim. It is Aurora payable exposure.'),
              ('EXCLUSIONS AND DEPENDENCE',
               'No maintenance exclusion applies to the service credits in this agreement, even for '
               'maintenance approved under C01. Forge failure does not excuse Aurora performance. Separate '
               'restoration and outage records distinguish incidents. Duplicates and corrections for one '
               'incident do not create additional credits.'),
              ('OFFICE-DEPENDENT SUPPORT',
               'Throughout the term ending 2027-12-31, Aurora shall maintain the staffed APP-ATLAS support '
               'operation at office UNIT-5 covered by lease C05. Relocation requires Forge prior written '
               'approval. No relocation approval is attached. The initial C05 lease term ends on 2027-06-30 '
               'and has its own renewal and notice provisions.'),
              ('NOTICE AND TERMINATION',
               'Material breaches other than unavailability require written notice received at '
               'aurora-legal@aurora.example and a 10-calendar-day cure period ending at 17:00 UTC on the '
               'tenth following date. An uncured breach permits a separate termination notice after the cure '
               'deadline.'),
              ('LIMITATION OF LIABILITY',
               'Service-credit liability is limited to INR 45,000 per UTC calendar month under clause 5.1. '
               'Other aggregate liability is capped at INR 1,000,000, except fraud, wilful misconduct and '
               'indemnity obligations.'),
              ('MUTUAL THIRD-PARTY PROTECTION',
               'Each party protects the other against third-party claims and reasonable defense expense '
               'caused by its own infringement or unauthorized disclosure. Notice must be prompt and the '
               'party seeking protection must cooperate reasonably with the defense.'),
              ('CUSTOMER MATERIAL',
               'Customer files and application specifications are received in confidence. Each party must '
               'limit their use to providing or receiving the application service and bind its permitted '
               'staff accordingly. Public information is excluded; the undertaking continues for 3 years '
               'after this agreement ends.'),
              ('SERVICE COMPLIANCE',
               'Each party must comply with laws applicable to its role in application performance. This '
               'includes the Digital Personal Data Protection Act, 2023 where applicable and GDPR where its '
               'processing scope applies. Personal-data processing requires access controls and a documented '
               'incident-response procedure. No ISO certification is promised.'),
              ('SUBSTITUTION OF ENTITY',
               'Neither party may substitute a new contracting entity without written consent. An affiliate '
               'may take an assignment on 30 calendar days written notice, provided the original party '
               'continues to answer for performance. A corporate acquisition does not itself amend these '
               'terms.'),
              ('EVENTS OUTSIDE CONTROL',
               'Relief for an event beyond reasonable control is confined to the affected obligations in '
               'application performance. The affected party must give written notice within 5 calendar days '
               'after discovery, explain causation and provide mitigation evidence. Accrued payments remain '
               'payable. Neither an outage nor supplier delay qualifies automatically.'),
              ('OTHER CUSTOMER RELATIONSHIPS',
               'The parties remain free to enter other arrangements outside the scope of application '
               'performance. This agreement grants no exclusivity or non-compete except any restriction '
               'expressly stated in this clause.'),
              ('DISCONTINUANCE WITHOUT CAUSE',
               'Either party may end future application performance for convenience by written notice '
               'received at the other party legal notice address at least 30 calendar days before '
               'termination. Accrued payment obligations, express survival provisions and the stated '
               'conditions of any early-exit fee continue to apply.'),
              ('DISPUTES',
               'Indian law governs. Pune courts have exclusive jurisdiction for disputes arising solely '
               'under C02. A joint proceeding including claims under any other agreement requires a '
               'separately signed forum agreement by all relevant parties; no such agreement is attached.'),
              ('OTHER AGREEMENTS',
               'C02 governs APP-ATLAS subscription services only. A separate agreement between the same '
               'parties does not amend, replace, or consolidate C02 unless it expressly identifies the '
               'changed provisions. Rights already accrued survive expiry.'),
              ('ACCEPTED ON BEHALF OF THE PARTIES',
               'Mira Sen for Aurora and Anil Das for Forge record execution on 2026-12-16.')],
  'type': 'saas',
  'effective_date': '2027-01-01',
  'governing_law': 'India',
  'form': 'Customer letter agreement',
  'preamble': ('AGREED COMMERCIAL LETTER',
               'Forge has requested an application service from Aurora. By the acceptance recorded at the '
               'end of this letter, the parties adopt the following scope, commitments and allocation of '
               'risk.'),
  'schedules': [{'letter': 'A',
                 'title': 'SERVICE COMMITMENTS',
                 'columns': ['Reference', 'Item', 'Agreed particulars'],
                 'rows': [['Row 1',
                           'APP-ATLAS incident',
                           'Over 30 minutes: INR 15,000; monthly cap INR 45,000'],
                          ['Row 2', 'Support location', 'UNIT-5 through 2027-12-31']]}]},
 {'id': 'C03',
  'title': 'Component Supplier Agreement',
  'parties': ['P01', 'P02'],
  'clauses': [('PURCHASE PARTICULARS',
               'Aurora Software Private Limited (P01, Buyer) purchases 100 AX-7 controllers from Forge '
               'Electronics Private Limited (P02, Supplier) under purchase order PO-AX7. This is a single '
               'delivery lot, LOT-AX7. Company legal notice address: aurora-legal@aurora.example. '
               'Counterparty legal notice address: notices@forge.example.'),
              ('TERM AND DELIVERY',
               'Signed on 2026-12-17 and effective from 2027-01-05 until 2027-03-31. Supplier must deliver '
               'the entire conforming lot to Aurora depot DEPOT-A by 2027-02-10 at 17:00 UTC. Early delivery '
               'is permitted. The upstream date is not accelerated by any Aurora resale commitment.'),
              ('PRICE AND PAYMENT',
               'The total price is INR 500,000, payable 30 calendar days after Aurora receives a '
               'conforming-delivery acceptance record and invoice INV-AX7, by 17:00 UTC on that following '
               'date. No delivery acceptance or invoice is assumed merely from the passage of time. No '
               'late-payment fee is agreed.'),
              ('DELAY REMEDY',
               'For each calendar date beginning on 2027-02-11 while the conforming lot remains undelivered '
               'at 00:00 UTC, Supplier owes Buyer INR 2,000, capped at INR 20,000 for this lot. Delivery '
               'after 00:00 on a date does not remove that date charge. No delay damages beyond this cap are '
               'agreed. These sums are Buyer recoverables, not Buyer payables.'),
              ('ACCEPTANCE EVIDENCE',
               'A delivery record must identify PO-AX7, LOT-AX7, 100 conforming units, destination DEPOT-A '
               'and acceptance time. Partial shipment is not full performance. An unrelated purchase order '
               'does not satisfy this obligation.'),
              ('CURE AND TERMINATION',
               'For a delivery breach, Buyer may send written notice to notices@forge.example. Cure ends at '
               '17:00 UTC on the tenth calendar date after Supplier receives the notice. If full conforming '
               'delivery is absent after that deadline, Buyer may serve a separate termination notice; the '
               'agreement does not terminate automatically. Curing the breach preserves accrued clause 4.1 '
               'of C03 charges.'),
              ('DEPENDENCY BOUNDARY',
               'Supplier knows Aurora resells LOT-AX7 under customer agreement C04. Supplier makes no '
               'promise to meet the C04 resale deadline and owes no C04 penalties. Aurora retains '
               'responsibility for its downstream promises.'),
              ('DISPUTES',
               'Indian law and exclusive Bengaluru court jurisdiction apply to this purchase only. No joint '
               'forum with C04 is agreed.'),
              ('TIME AND NOTICES',
               'All days are calendar days and all times UTC, without holiday adjustments. Written notice is '
               'effective on proven receipt, not dispatch. A notice has no effect on a different purchase '
               'order. All figures exclude taxes.'),
              ('PURCHASE AUTHORISATION',
               'Mira Sen for Aurora and Anil Das for Forge record execution on 2026-12-17.'),
              ('REMEDY BOUNDARIES',
               'The lot-delay remedy is subject to its INR 20,000 cap in clause 4.1. For other ordinary '
               'claims the aggregate limit is INR 1,000,000. Fraud, wilful misconduct and indemnity '
               'obligations are outside that aggregate limit; downstream penalties do not become supplier '
               'liabilities by implication.'),
              ('RESPONSIBILITY FOR THIRD-PARTY CLAIMS',
               'The party supplying infringing intellectual property or making an unauthorized confidential '
               'disclosure must meet the other party third-party claim and reasonable defense costs arising '
               'from it. Prompt notification and reasonable defense cooperation are conditions of this '
               'mutual protection.'),
              ('ORDER CONFIDENCE',
               'Bills of materials, testing records and order pricing supplied in confidence shall stay '
               'within the purchasing and fulfilment teams on equivalent confidentiality terms. The '
               'restriction survives this order for 3 years and does not cover material already public '
               'without breach.'),
              ('MANUFACTURING STANDARDS',
               'Each party must comply with laws applicable to its role in controller manufacture and '
               'delivery. This includes the Digital Personal Data Protection Act, 2023 where applicable and '
               'GDPR where its processing scope applies. Personal-data processing requires access controls '
               'and a documented incident-response procedure. No ISO certification is promised.'),
              ('ORDER ASSIGNMENT',
               'This order may not be assigned without the other party written approval. Assignment to an '
               'affiliate is an exception only after 30 calendar days written notice and with the assignor '
               'remaining liable. Ownership changes alone do not transfer the order.'),
              ('UNAVOIDABLE SUPPLY INTERRUPTION',
               'Relief for an event beyond reasonable control is confined to the affected obligations in '
               'controller manufacture and delivery. The affected party must give written notice within 5 '
               'calendar days after discovery, explain causation and provide mitigation evidence. Accrued '
               'payments remain payable. Neither an outage nor supplier delay qualifies automatically.'),
              ('EXCLUSIVE PROCUREMENT',
               'From 2027-01-05 through 2027-03-31, Aurora shall source all AX-7 controllers exclusively '
               'from Forge. Aurora shall not commit to purchase AX-7 controllers from another supplier '
               'during that period without Forge prior written waiver. No waiver is attached.'),
              ('CANCELLATION OF FUTURE SUPPLY',
               'Either party may end future controller manufacture and delivery for convenience by written '
               'notice received at the other party legal notice address at least 30 calendar days before '
               'termination. Accrued payment obligations, express survival provisions and the stated '
               'conditions of any early-exit fee continue to apply.'),
              ('CHANGE REQUEST RESPONSE',
               'Supplier shall respond to an Aurora delivery-change request within a reasonable time. The '
               'parties have not specified a numeric response deadline or a monetary remedy for this '
               'response obligation.')],
  'type': 'supply',
  'effective_date': '2027-01-05',
  'governing_law': 'India',
  'form': 'Purchase order conditions',
  'preamble': ('ORDER CONFIRMATION',
               'Aurora confirms its purchase of the identified controller lot. Forge accepts the order '
               'subject to the delivery, inspection and sourcing conditions set out here; a resale promise '
               'does not accelerate Forge own delivery date.'),
  'schedules': [{'letter': 'A',
                 'title': 'PURCHASE ORDER',
                 'columns': ['Reference', 'Item', 'Agreed particulars'],
                 'rows': [['Row 1', 'PO-AX7 / LOT-AX7', 'Quantity: 100 conforming AX-7 units'],
                          ['Row 2', 'Purchase price', 'INR 500,000'],
                          ['Row 3', 'Latest depot receipt', '2027-02-10 at 17:00 UTC'],
                          ['Row 4', 'Delay remedy', 'INR 2,000 per started date; cap INR 20,000']]}],
  'tables_position': 'front'},
 {'id': 'C04',
  'title': 'Customer Controller Supply Agreement',
  'parties': ['P01', 'P03'],
  'clauses': [('CUSTOMER ORDER',
               'Aurora Software Private Limited (P01, Seller) supplies 100 AX-7 controllers from LOT-AX7 to '
               'Willow Housing Private Limited (P03, Customer) under order SO-AX7. Company legal notice '
               'address: aurora-legal@aurora.example. Counterparty legal notice address: '
               'legal@willow.example. The controllers support Willow residential building automation '
               'installations.'),
              ('DELIVERY AND DEPENDENCY',
               'Signed on 2026-12-18 and effective 2027-01-08 through 2027-03-31. Aurora must deliver the '
               'entire conforming lot to Willow by 2027-02-08 at 17:00 UTC. Aurora sources that same lot '
               'under C03, whose latest promised depot delivery is 2027-02-10 at 17:00 UTC. Transfer '
               'requires no minimum additional transit time under this agreement. Supplier failure does not '
               'excuse Aurora delay.'),
              ('PRICE',
               'Willow owes INR 650,000 within 30 calendar days after full conforming delivery acceptance '
               'and receipt of invoice INV-SOAX7, by 17:00 UTC on the thirtieth following date. No '
               'acceptance or invoice is presumed. Late-payment interest is addressed in clause 19.1.'),
              ('DELAY CHARGES',
               'For each calendar date beginning on 2027-02-09 when the complete conforming lot remains '
               'undelivered to Willow at 00:00 UTC, Aurora owes Willow INR 5,000, capped at INR 50,000 per '
               'lot. Delivery later that date preserves that date charge. This is Aurora payable exposure. '
               'These charges are the sole monetary remedy for delay.'),
              ('EVIDENCE',
               'A receipt for SO-AX7 must identify all 100 conforming units and Willow destination SITE-W. '
               'Arrival at Aurora DEPOT-A under C03 alone is not downstream delivery. An early downstream '
               'acceptance may prevent actual late-delivery charges without changing either contractual '
               'deadline.'),
              ('CURE AND TERMINATION',
               'A material breach notice must be received at aurora-legal@aurora.example. Aurora has 10 '
               'calendar days after receipt, until 17:00 UTC on the tenth following date, to cure. After '
               'that time an uncured breach permits a separate termination notice. Accrued delay charges '
               'survive cure or termination.'),
              ('OTHER RECOVERY',
               'Any credit recoverable from Forge under C03 must be reported separately from C04 '
               'liabilities. This agreement promises no reimbursement of Aurora downstream charges by '
               'Forge.'),
              ('DISPUTES',
               'Indian law and exclusive Pune court jurisdiction govern C04. The differing forum in C03 does '
               'not itself invalidate either agreement. Any combined proceeding with claims under C08 '
               'requires a separately signed forum agreement by all relevant parties. No such agreement is '
               'attached.'),
              ('CLOCK',
               'All times are UTC and days calendar days, without holiday adjustments. Date-only deadlines '
               'end at 17:00 UTC. Prices and charges exclude taxes.'),
              ('ORDER EXECUTION',
               'Mira Sen for Aurora and Kavya Paul for Willow record execution on 2026-12-18.'),
              ('DAMAGES AND EXCEPTIONS',
               'The delay remedy is limited to INR 50,000 under clause 4.1. Other ordinary aggregate damages '
               'are capped at INR 1,000,000. Fraud, wilful misconduct and indemnity obligations, including '
               'the seller indemnity in clause 12.1, are excluded from that cap.'),
              ('SELLER INDEMNITY WITHOUT RECIPROCITY',
               'Aurora shall indemnify Willow against all third-party claims and defense costs arising from '
               'the controllers or their use, including claims caused by Willow own negligence. Willow has '
               'no reciprocal indemnity obligation. This indemnity is excluded from the aggregate liability '
               'cap in clause 11.1.'),
              ('DRAWINGS AND REQUIREMENTS',
               'The controller drawings and Willow commercial requirements may be used only to fulfil this '
               'sale. Both parties shall secure them against unauthorized disclosure and require equivalent '
               'undertakings from personnel with access. Public material is excluded; protection lasts 3 '
               'years beyond termination.'),
              ('SALE COMPLIANCE',
               'Each party must comply with laws applicable to its role in fulfilment of this sale. This '
               'includes the Digital Personal Data Protection Act, 2023 where applicable and GDPR where its '
               'processing scope applies. Personal-data processing requires access controls and a documented '
               'incident-response procedure. No ISO certification is promised.'),
              ('TRANSFER OF THE SALE',
               'Consent in writing is required to assign the sale. On 30 calendar days written notice, an '
               'affiliate may receive it if the existing seller or buyer remains liable. A merger '
               'announcement does not silently alter the named buyer or seller.'),
              ('EXCUSED NON-PERFORMANCE',
               'Relief for an event beyond reasonable control is confined to the affected obligations in '
               'fulfilment of this sale. The affected party must give written notice within 5 calendar days '
               'after discovery, explain causation and provide mitigation evidence. Accrued payments remain '
               'payable. Neither an outage nor supplier delay qualifies automatically.'),
              ('OTHER SALES',
               'The parties remain free to enter other arrangements outside the scope of fulfilment of this '
               'sale. This agreement grants no exclusivity or non-compete except any restriction expressly '
               'stated in this clause.'),
              ('ENDING THE SALE BY NOTICE',
               'Either party may end future fulfilment of this sale for convenience by written notice '
               'received at the other party legal notice address at least 30 calendar days before '
               'termination. Accrued payment obligations, express survival provisions and the stated '
               'conditions of any early-exit fee continue to apply.'),
              ('LATE-PAYMENT INTEREST',
               'Late-payment interest rate: ____ % per month on overdue invoiced principal. The percentage '
               'has not been completed. No numeric late-payment interest amount can be determined from this '
               'execution copy.')],
  'type': 'supply',
  'effective_date': '2027-01-08',
  'governing_law': 'India',
  'form': 'Sales order acceptance',
  'preamble': ('SALE ACCEPTED',
               'Aurora accepts Willow order for controllers to be installed in residential buildings. The '
               'delivery commitment in this sale is Aurora own promise, even though the goods are sourced '
               'under a separate purchase.'),
  'schedules': [{'letter': 'A',
                 'title': 'CUSTOMER ORDER',
                 'columns': ['Reference', 'Item', 'Agreed particulars'],
                 'rows': [['Row 1', 'SO-AX7 / LOT-AX7', 'Quantity: 100 conforming AX-7 units'],
                          ['Row 2', 'Sale price', 'INR 650,000'],
                          ['Row 3', 'Customer receipt', '2027-02-08 at 17:00 UTC'],
                          ['Row 4', 'Delay charge', 'INR 5,000 per started date; cap INR 50,000']]}],
  'tables_position': 'front'},
 {'id': 'C05',
  'title': 'Office Lease',
  'parties': ['P01', 'P03'],
  'clauses': [('DEMISE OF THE PREMISES',
               'Aurora Software Private Limited (P01, Tenant) leases office UNIT-5 at 5 Example Quay from '
               'Willow Housing Private Limited (P03, Landlord). Company legal notice address: '
               'aurora-legal@aurora.example. Counterparty legal notice address: notices@willow.example.'),
              ('TERM AND RENEWAL',
               'Signed on 2026-12-19. The initial term is 2027-01-03 through 2027-06-30 inclusive. It renews '
               'automatically for 6 months on the same rent unless Tenant gives valid non-renewal notice at '
               'least 30 calendar days before the current term end date. The notice cutoff is at 17:00 UTC '
               'on the calculated cutoff date.'),
              ('VALID NOTICE',
               'Non-renewal notice must be received by notices@willow.example with subject UNIT-5 '
               'NON-RENEWAL and authorized Tenant sender Mira Sen. Dispatch alone, an incorrect address, or '
               'receipt after the cutoff is insufficient. No acknowledgment from Landlord is required if '
               'receipt is evidenced.'),
              ('RENT',
               'Rent is INR 100,000 per calendar month, due on the twentieth day of that month at 17:00 UTC, '
               'with invoice reference RENT-YYYY-MM. The first invoice is RENT-2027-01. No deposit or taxes '
               'are included under this agreement. The January rent is the stated full monthly amount '
               'notwithstanding the 2027-01-03 commencement.'),
              ('PAYMENT ALLOCATION',
               'Only cleared payments identifying the invoice and currency INR reduce its rent principal, '
               'from their occurred_at time. Apply principal before charges. A repeated bank transaction ID '
               'is not another payment; a reversal expressly identifying that transaction removes the '
               'payment from its reversal time. Unrelated invoices do not reduce this rent.'),
              ('GRACE AND LATE CHARGE',
               'Unpaid rent has a grace period through 23:59:59 UTC on the twenty-fifth day of the due '
               'month. Starting at 00:00 UTC on the twenty-sixth, a simple charge of 0.1 percent of unpaid '
               'rent principal at that instant accrues for each started UTC calendar date until full '
               'payment. There is no compounding and no charge on earlier charges. Total late charges per '
               'invoice are capped at INR 5,000. A payment later on a date does not reverse that date '
               'charge.'),
              ('RENEWAL CONSEQUENCE',
               'A missed or invalid non-renewal notice commits the next 6-month term at INR 100,000 monthly. '
               'Report INR 600,000 as a future committed rent obligation, not a present fine. Do not add it '
               'again to the same months of scheduled rent. The current term remains in effect when a timely '
               'notice prevents renewal.'),
              ('TERMINATION FOR CONVENIENCE',
               'No unilateral early termination for convenience is granted during a committed lease term. '
               'Non-renewal at term end requires compliance with clauses 2.1 and 3.1. Earlier release '
               'requires a signed agreement between Landlord and Tenant.'),
              ('DEFAULT AND TERMINATION',
               'Landlord must give Tenant written material-breach notice at aurora-legal@aurora.example and '
               'allow 10 calendar days after receipt, through 17:00 UTC on the tenth following date, to '
               'cure. An uncured breach permits a separate termination notice; mere late rent does not '
               'automatically terminate this lease.'),
              ('TIME AND FORUM',
               'All times are UTC and all days calendar days. No business-day or holiday adjustment applies. '
               'Indian law and exclusive Bengaluru court jurisdiction govern. No unspecified damages or fees '
               'are inferred.'),
              ('LIMITATION OF LIABILITY',
               'Late charges are capped at INR 5,000 per rent invoice under clause 6.1. Accrued rent and '
               'committed renewal rent are payment obligations, not damages. Other aggregate damages are '
               'capped at INR 1,000,000, excluding fraud and indemnity obligations.'),
              ('LANDLORD AND TENANT INDEMNITIES',
               'Landlord and Tenant each indemnify the other for third-party claims caused by their own '
               'intellectual-property infringement or unauthorized disclosure, including reasonable defense '
               'costs. A claim must be notified promptly and the defense assisted reasonably.'),
              ('PRIVATE OCCUPANCY INFORMATION',
               'Office plans, entry credentials and non-public lease information shall be kept private and '
               'used only in administering the letting. Staff access must be limited and subject to '
               'confidentiality duties. Information public without breach is excluded. This covenant '
               'survives the letting for 3 years.'),
              ('LAWFUL USE OF PREMISES',
               'Each party must comply with laws applicable to its role in occupation and maintenance of the '
               'premises. This includes the Digital Personal Data Protection Act, 2023 where applicable and '
               'GDPR where its processing scope applies. Personal-data processing requires access controls '
               'and a documented incident-response procedure. No ISO certification is promised.'),
              ('DEALINGS WITH THE LEASE',
               'Assignment of this lease requires written consent from the other party. An affiliate '
               'assignment is allowed only with 30 calendar days written notice and continuing liability of '
               'the original tenant or landlord. A change of control is not a consent waiver.'),
              ('EXCEPTIONAL EVENTS AT THE PREMISES',
               'Relief for an event beyond reasonable control is confined to the affected obligations in '
               'occupation and maintenance of the premises. The affected party must give written notice '
               'within 5 calendar days after discovery, explain causation and provide mitigation evidence. '
               'Accrued payments remain payable. Neither an outage nor supplier delay qualifies '
               'automatically.'),
              ('OTHER LETTINGS',
               'The parties remain free to enter other arrangements outside the scope of occupation and '
               'maintenance of the premises. This agreement grants no exclusivity or non-compete except any '
               'restriction expressly stated in this clause.'),
              ('EXECUTION AS A DEED',
               'Mira Sen for Aurora and Kavya Paul for Willow record execution on 2026-12-19.')],
  'type': 'lease',
  'effective_date': '2027-01-03',
  'governing_law': 'India',
  'form': 'Lease deed',
  'preamble': ('RECITALS',
               'Willow controls the premises described below and agrees to let them to Aurora. Aurora '
               'accepts the letting for office use. The parties distinguish expiry, non-renewal and early '
               'release in the operative covenants.'),
  'schedules': [{'letter': 'A',
                 'title': 'RENT AND NOTICE CALENDAR',
                 'columns': ['Reference', 'Item', 'Agreed particulars'],
                 'rows': [['Row 1', 'Monthly rent', 'INR 100,000; due on day 20 at 17:00 UTC'],
                          ['Row 2',
                           'Late-charge start',
                           'Day 26 at 00:00 UTC; 0.1 percent daily on unpaid principal'],
                          ['Row 3', 'Per-invoice charge cap', 'INR 5,000'],
                          ['Row 4', 'Initial non-renewal cutoff', '2027-05-31 at 17:00 UTC']]}]},
 {'id': 'C06',
  'title': 'Firmware Development Software Subscription',
  'parties': ['P01', 'P02'],
  'clauses': [('LICENSED ACCESS',
               'Aurora Software Private Limited (P01, Subscriber) licenses TOOL-CIRCUIT from Forge '
               'Electronics Private Limited (P02, Vendor). This document includes the original agreement and '
               'an executed amendment. Company legal notice address: aurora-legal@aurora.example. '
               'Counterparty legal notice address: legal@forge.example.'),
              ('TERM',
               'The original agreement is signed on 2026-12-20. Subscription runs from 2027-01-10 through '
               '2027-12-31 inclusive and automatically renews for one year unless valid non-renewal notice '
               'is given under clause 3.1 of C06 as amended when applicable.'),
              ('ORIGINAL NOTICE WINDOW',
               'In the original agreement, Subscriber must give notice at least 60 calendar days before the '
               'current term end date. Notice must be received at notices@forge.example by 17:00 UTC on the '
               'calculated cutoff date and identify TOOL-CIRCUIT. See the embedded amendment clause 19.1 of '
               'C06-clause 19.3 of C06 for its limited change and effective date.'),
              ('SUBSCRIPTION PRICE',
               'The license fee is INR 120,000 for the initial year, due on 2027-01-31 at 17:00 UTC under '
               'invoice CIRCUIT-2027. Renewal price remains INR 120,000 per year. There is no agreed late '
               'charge.'),
              ('SERVICE SCOPE',
               'Subscriber may use TOOL-CIRCUIT for internal firmware development and controller '
               'configuration only. This subscription neither changes APP-ATLAS obligations nor incorporates '
               'any Forge marketing statements.'),
              ('TERMINATION',
               'A material-breach notice received at the other party legal email gives a 10-calendar-day '
               'cure period, ending at 17:00 UTC on the tenth following date. After an uncured breach a '
               'separate termination notice may be served. Vendor legal email is legal@forge.example; '
               'Subscriber email is aurora-legal@aurora.example.'),
              ('MISSING EXIT FEE SCHEDULE',
               'On early termination, Subscriber shall pay the migration fee stated in Schedule B. Schedule '
               'B is not attached to this execution copy. No numeric migration fee, formula or waiver '
               'appears elsewhere in this agreement. Non-renewal at term end is not early termination. '
               'Obtain Schedule B before quantifying an early-termination migration fee.'),
              ('PRECEDENCE AND SURVIVAL',
               'Only an expressly executed amendment may change this agreement. The embedded amendment '
               'changes only the identified notice period from its effective date; other obligations, '
               'accrued charges, and missing Schedule B remain unchanged. No general replacement is '
               'intended.'),
              ('TIME AND DISPUTES',
               'Calendar days and UTC apply, without holiday adjustments. Date-only deadlines end at 17:00 '
               'UTC. Indian law and exclusive Bengaluru courts apply. Financial figures exclude taxes.'),
              ('SUBSCRIPTION ACCEPTANCE',
               'Mira Sen for Aurora and Anil Das for Forge record execution on 2026-12-20.'),
              ('SUBSCRIPTION LIABILITY',
               'Ordinary aggregate claims concerning this subscription are limited to INR 1,000,000, '
               'excluding fraud, wilful misconduct and indemnity obligations. The limit is not a price for '
               'the absent migration-fee schedule and supplies no missing fee or formula.'),
              ('LICENSE CLAIM ALLOCATION',
               'Third-party intellectual-property or confidentiality claims caused by a party infringement '
               'or unauthorized disclosure are that party responsibility by indemnity, including reasonable '
               'defense costs. The other party shall promptly notify the claim and reasonably cooperate.'),
              ('KEYS AND DOCUMENTATION',
               'License keys, non-public tool documentation and each party commercial information are '
               'confidential. Their use is limited to performance of the subscription; access is restricted '
               'to bound personnel. Confidentiality survives expiry for 3 years, with an exception for '
               'information public without breach.'),
              ('LICENSE COMPLIANCE',
               'Each party must comply with laws applicable to its role in operation of the development '
               'tool. This includes the Digital Personal Data Protection Act, 2023 where applicable and GDPR '
               'where its processing scope applies. Personal-data processing requires access controls and a '
               'documented incident-response procedure. No ISO certification is promised.'),
              ('SUBSCRIPTION ASSIGNMENT',
               'A subscription assignment needs the other party written consent, except an affiliate '
               'assignment notified 30 calendar days in advance with the original subscriber or vendor '
               'remaining liable. A sale of a business does not automatically transfer the license.'),
              ('EXCEPTIONAL LICENSE DISRUPTION',
               'Relief for an event beyond reasonable control is confined to the affected obligations in '
               'operation of the development tool. The affected party must give written notice within 5 '
               'calendar days after discovery, explain causation and provide mitigation evidence. Accrued '
               'payments remain payable. Neither an outage nor supplier delay qualifies automatically.'),
              ('OTHER SOFTWARE TOOLS',
               'The parties remain free to enter other arrangements outside the scope of operation of the '
               'development tool. This agreement grants no exclusivity or non-compete except any restriction '
               'expressly stated in this clause.'),
              ('CONVENIENCE EXIT',
               'Either party may end future operation of the development tool for convenience by written '
               'notice received at the other party legal notice address at least 30 calendar days before '
               'termination. Accrued payment obligations, express survival provisions and the stated '
               'conditions of any early-exit fee continue to apply.')],
  'amendment': [('A1',
                 'LIMITED CHANGE',
                 'Aurora and Forge, as the same parties to C06, execute this amendment on 2027-01-10. '
                 'Effective 2027-03-01 at 00:00 UTC, replace only the words "60 calendar days" in clause 3.1 '
                 'of C06 with "30 calendar days". The amendment is prospective from that effective instant.'),
                ('A2',
                 'PRESERVED PROVISIONS',
                 'All other C06 terms remain unchanged, including its year-end term, notice receipt address '
                 'and time, annual price, and the absent Schedule B. Before 2027-03-01 at 00:00 UTC, the '
                 'original 60-day provision is applicable. The amendment does not replace the original '
                 'agreement or waive accrued rights.'),
                ('A3',
                 'AMENDMENT EXECUTION',
                 'Mira Sen for Aurora and Anil Das for Forge record amendment execution on 2027-01-10. All '
                 'provisions not expressly changed remain in force.')],
  'type': 'saas',
  'effective_date': '2027-01-10',
  'governing_law': 'India',
  'form': 'Software subscription order',
  'preamble': ('LICENSE ELECTION',
               'Aurora selects the controller-development subscription offered by Forge. Access to the tool '
               'is licensed for the stated purpose; neither purchase of controllers nor delivery of software '
               'to a customer transfers the tool itself.'),
  'schedules': [{'letter': 'A',
                 'title': 'LICENSE ORDER',
                 'columns': ['Reference', 'Item', 'Agreed particulars'],
                 'rows': [['Row 1', 'TOOL-CIRCUIT annual price', 'INR 120,000'],
                          ['Row 2', 'Initial invoice due', '2027-01-31 at 17:00 UTC'],
                          ['Row 3', 'Original renewal notice', 'Notice: 60 calendar days'],
                          ['Row 4',
                           'Notice from 2027-03-01',
                           'Notice: 30 calendar days; other terms unchanged']]}]},
 {'id': 'C07',
  'title': 'Resident Data Processing and Confidentiality Agreement',
  'parties': ['P01', 'P03'],
  'clauses': [('CONTROLLER INSTRUCTIONS',
               'Willow Housing Private Limited (P03, Controller) appoints Aurora Software Private Limited '
               '(P01, Processor) to process resident-service dataset DS-HOUSING for Willow residential '
               'properties in REGION-NORTH. Company legal notice address: aurora-legal@aurora.example. '
               'Controller legal notice address: legal@willow.example.'),
              ('CONFIDENTIALITY',
               'Processor must use DS-HOUSING solely to provide this service, restrict access to authorized '
               'staff, and report an observed unauthorized disclosure to Controller within 24 hours of '
               'Processor discovery. No disclosure is assumed without supporting observations.'),
              ('CONFIDENTIAL PROCESSING INFORMATION',
               'Processing instructions and non-public operational information remain confidential during '
               'the appointment and for 3 years afterwards. Access is limited to people with a performance '
               'need and matching duties. Public information is excluded, without relaxing the separate '
               'protections for resident data.'),
              ('EVIDENCE',
               'A notice records issuer, dataset, region, rule ID, effective time, safeguards and Processor '
               'receipt time. A correction identifies the superseded notice. The contractual receipt time '
               'and the monitoring system received_at time are distinct. System knowledge must be limited to '
               'records received by the simulated clock.'),
              ('APPLICABLE RULE',
               'For this agreement, an applicable rule-change notice is a supplied record issued by Data '
               'Standards Board, naming DS-HOUSING, REGION-NORTH and its rule ID, effective date and '
               'required safeguards. The notice must identify the applicable contractual safeguard '
               'requirements. A different dataset, region or issuer does not trigger clause 6.1 of C07.'),
              ('SAFEGUARD RESPONSE',
               'For an applicable notice, Processor must deliver the specified safeguard attestation to '
               'Controller by the later of the rule effective instant and 17:00 UTC on the tenth calendar '
               'date following receipt by Processor. A safeguard attestation matching rule ID, dataset and '
               'region by that deadline satisfies this obligation.'),
              ('REMEDIES AND UNCERTAINTY',
               'If the attestation is missing after the clause 6.1 of C07 deadline, the obligation is '
               'breached and Controller may request immediate remediation and legal review. No regulatory '
               'fine, automatic damages, per-day fee or monetary cap for this event is supplied. Do not '
               'quantify an unspecified fine as zero or as a guessed number.'),
              ('DATA-PROTECTION OBLIGATIONS',
               'Each party must comply with laws applicable to its role in resident-data processing. This '
               'includes the Digital Personal Data Protection Act, 2023 where applicable and GDPR where its '
               'processing scope applies. Personal-data processing requires access controls and a documented '
               'incident-response procedure. No ISO certification is promised.'),
              ('CLAIMS ARISING FROM PROCESSING',
               'For third-party claims resulting from its own infringement or unauthorized disclosure, each '
               'party indemnifies the other and pays reasonable defense costs. The claimant must give prompt '
               'notice and reasonable assistance in the defense.'),
              ('LIMITATION OF LIABILITY',
               'Ordinary contractual damages are capped at INR 1,000,000, excluding fraud, wilful misconduct '
               'and indemnity obligations. This cap is not a regulatory fine, does not set a fine amount, '
               'and does not itself quantify any regulatory liability.'),
              ('TERMINATION',
               'An uncured material breach may support termination only after written notice received at '
               'aurora-legal@aurora.example and a 10-calendar-day cure period through 17:00 UTC on the tenth '
               'following date. A separate termination notice is then required. Missing attestation alone '
               'does not prove unauthorized disclosure.'),
              ('TRANSFER OF APPOINTMENT',
               'The appointment cannot be assigned without the other party written agreement. An affiliate '
               'assignment requires 30 calendar days notice and continuing liability of the original party. '
               'A change of ownership does not rewrite the processing roles.'),
              ('PROCESSING CONTINGENCIES',
               'Relief for an event beyond reasonable control is confined to the affected obligations in '
               'resident-data processing. The affected party must give written notice within 5 calendar days '
               'after discovery, explain causation and provide mitigation evidence. Accrued payments remain '
               'payable. Neither an outage nor supplier delay qualifies automatically.'),
              ('OTHER PROCESSING APPOINTMENTS',
               'The parties remain free to enter other arrangements outside the scope of resident-data '
               'processing. This agreement grants no exclusivity or non-compete except any restriction '
               'expressly stated in this clause.'),
              ('ENDING THE APPOINTMENT WITHOUT CAUSE',
               'Either party may end future resident-data processing for convenience by written notice '
               'received at the other party legal notice address at least 30 calendar days before '
               'termination. Accrued payment obligations, express survival provisions and the stated '
               'conditions of any early-exit fee continue to apply.'),
              ('CLOCK AND FORUM',
               'All times UTC, days calendar days, no holiday adjustments. Indian law and exclusive '
               'Bengaluru courts apply to the agreement. Fees exclude taxes.'),
              ('APPOINTMENT PERIOD AND REMUNERATION',
               'The appointment takes effect on 2027-01-12 and ends on 2027-12-31 without automatic renewal. '
               'Willow owes Aurora INR 50,000 per billing month, payable by 17:00 UTC on day 5 of the '
               'following month. The initial 2027-01-12 through 2027-01-31 period is billed at the full '
               'monthly fee and is first due on 2027-02-05. No late fee is agreed.'),
              ('PROCESSING AUTHORISATION',
               'Mira Sen for Aurora and Kavya Paul for Willow record execution on 2026-12-21.')],
  'type': 'nda',
  'effective_date': '2027-01-12',
  'governing_law': 'India',
  'form': 'Processing instruction agreement',
  'preamble': ('APPOINTMENT',
               'Willow appoints Aurora to process resident-service information on its instructions. The '
               'processing restrictions are stated first; administration and remuneration follow them. The '
               'appointment does not transfer control of the resident information.'),
  'schedules': [{'letter': 'A',
                 'title': 'PROCESSING INSTRUCTION REGISTER',
                 'columns': ['Reference', 'Item', 'Agreed particulars'],
                 'rows': [['Row 1', 'Dataset / region', 'DS-HOUSING / REGION-NORTH'],
                          ['Row 2', 'Controller', 'Willow Housing Private Limited (P03)'],
                          ['Row 3', 'Processor', 'Aurora Software Private Limited (P01)'],
                          ['Row 4', 'Monthly processing fee', 'INR 50,000 payable by Willow to Aurora']]}]},
 {'id': 'C08',
  'title': 'Smart Building Supply and Partnership Agreement',
  'parties': ['P01', 'P03'],
  'clauses': [('PILOT PARTICIPANTS',
               'Aurora Software Private Limited (P01) and Willow Housing Private Limited (P03), also parties '
               'to customer supply agreement C04 and lease C05, enter PROJECT-HABITAT for a smart-building '
               'deployment pilot. This agreement concerns deployment coordination and the separate '
               'surplus-controller procurement in clause 3.1. It does not replace C04, C05 or any APP-ATLAS '
               'obligation under C02. Company legal notice address: aurora-legal@aurora.example. '
               'Counterparty legal notice address: legal@willow.example.'),
              ('DATES AND EFFECT',
               'Signed on 2027-01-20; effective from 2027-02-01 at 00:00 UTC through 2027-05-31 inclusive, '
               'with no automatic renewal. No obligations under this agreement accrue before its effective '
               'date. Ingestion or upload does not change that date.'),
              ('ADDITIONAL CONTROLLER PROCUREMENT',
               'Willow has surplus unopened AX-7 controllers from a completed housing installation. Aurora '
               'commits to purchase 100 AX-7 controllers from Willow for delivery on 2027-02-20 at 17:00 UTC '
               'for INR 600,000, payable on 2027-02-28 at 17:00 UTC against invoice WILLOW-AX7-2027. This is '
               'a separate procurement from order SO-AX7 and does not amend or waive any restriction in C03. '
               'No Forge waiver or Willow release is attached.'),
              ('PILOT FUNDING',
               'Aurora shall pay Willow INR 80,000 for PROJECT-HABITAT by 2027-02-05 at 17:00 UTC against '
               'invoice HABITAT-2027. No late charge or unspecified pilot-project damages are agreed.'),
              ('WILLOW DEPLOYMENT PLAN',
               'Willow shall deliver an approved deployment plan for PROJECT-HABITAT by 2027-02-03 at 17:00 '
               'UTC. Approval requires an Aurora signed approval record identifying the plan. A submitted '
               'but unapproved draft is insufficient. No plan is assumed from the passage of time.'),
              ('NO AMENDMENT OR REPLACEMENT',
               'C08 neither amends nor replaces any part of C04, C05 or C02 and does not offset service '
               'credits or combine invoices. APP-ATLAS maintenance and service-credit obligations remain '
               'exactly as stated in C02. This agreement contains no commitment to change C01.'),
              ('DISPUTES AND JOINT CLAIMS',
               'Indian law governs. Mumbai courts have exclusive jurisdiction over claims solely under C08. '
               'Any combined proceeding involving C04 also requires a separately signed forum agreement '
               'under clause 8.1 of C04 and this clause. The parties have not supplied that agreement. Do '
               'not assume one forum automatically controls all claims.'),
              ('TERMINATION AND SURVIVAL',
               'Written breach notice to the other party legal email gives 10 calendar days after receipt to '
               'cure, through 17:00 UTC on the tenth following date. Thereafter an uncured breach permits a '
               'separate termination notice. Accrued payment obligations survive termination.'),
              ('NOTICES',
               'Aurora legal email is aurora-legal@aurora.example and Willow legal email is '
               'legal@willow.example. A notice takes effect on proven receipt. A C08 notice does not by '
               'itself terminate C02.'),
              ('TIME AND ACCOUNTING',
               'All times UTC and days calendar days, without holiday adjustments. Date-only deadlines end '
               'at 17:00 UTC. All amounts exclude taxes. Independent scope does not imply the absence of all '
               'business risk; assess each agreement on its evidence.'),
              ('FRAMEWORK RISK ALLOCATION',
               'Ordinary aggregate damages under this framework are capped at INR 1,000,000, except fraud, '
               'wilful misconduct and indemnity obligations. The controller purchase price in clause 3.1 is '
               'a payment commitment, not an additional fixed damages charge. No limit from another '
               'agreement is imported.'),
              ('PARTICIPANT INDEMNITIES',
               'A participant shall hold the other protected against third-party claims and reasonable '
               'defense costs arising from its own infringement or unauthorized disclosure. The benefiting '
               'participant shall notify promptly and cooperate reasonably in the defense.'),
              ('PROJECT CONFIDENCE',
               'Pilot plans, property drawings and non-public procurement terms shall remain within the '
               'authorized project teams. Each party must prevent unrelated use and bind recipients to '
               'confidentiality. Apart from material public without breach, these protections last 3 years '
               'after the framework ends.'),
              ('PROJECT COMPLIANCE',
               'Each party must comply with laws applicable to its role in pilot and controller procurement. '
               'This includes the Digital Personal Data Protection Act, 2023 where applicable and GDPR where '
               'its processing scope applies. Personal-data processing requires access controls and a '
               'documented incident-response procedure. No ISO certification is promised.'),
              ('CHANGE OF PARTICIPANT',
               'A participant may assign the framework only with written consent. An affiliate assignment is '
               'permissible on 30 calendar days written notice if the original participant remains liable. '
               'Corporate restructuring alone neither replaces a party nor waives consent.'),
              ('PROJECT IMPEDIMENTS',
               'Relief for an event beyond reasonable control is confined to the affected obligations in '
               'pilot and controller procurement. The affected party must give written notice within 5 '
               'calendar days after discovery, explain causation and provide mitigation evidence. Accrued '
               'payments remain payable. Neither an outage nor supplier delay qualifies automatically.'),
              ('OTHER PARTNERSHIPS',
               'The parties remain free to enter other arrangements outside the scope of pilot and '
               'controller procurement. This agreement grants no exclusivity or non-compete except any '
               'restriction expressly stated in this clause.'),
              ('ORDINARY PROJECT WITHDRAWAL',
               'Either party may end future pilot and controller procurement for convenience by written '
               'notice received at the other party legal notice address at least 30 calendar days before '
               'termination. Accrued payment obligations, express survival provisions and the stated '
               'conditions of any early-exit fee continue to apply.'),
              ('CONVENIENCE NOTICE PERIOD',
               'For termination for convenience under clause 18.1, either party must give 60 calendar days '
               'prior written notice. Clause 18.1 states 30 calendar days for the same notice. Both '
               'provisions form part of this agreement and no order of precedence between them is stated.'),
              ('FRAMEWORK EXECUTION',
               'Mira Sen for Aurora and Kavya Paul for Willow record execution on 2027-01-20.')],
  'type': 'supply',
  'effective_date': '2027-02-01',
  'governing_law': 'India',
  'form': 'Deployment framework',
  'preamble': ('PROJECT CHARTER',
               'The parties wish to coordinate a housing-technology pilot and a separate purchase of surplus '
               'controllers. They record those commercial commitments before the administrative provisions. '
               'Existing leases and sale orders continue on their own terms.'),
  'schedules': [{'letter': 'A',
                 'title': 'PROJECT COMMITMENTS',
                 'columns': ['Reference', 'Item', 'Agreed particulars'],
                 'rows': [['Row 1', 'PROJECT-HABITAT plan', '2027-02-03 at 17:00 UTC'],
                          ['Row 2', 'Pilot funding', 'INR 80,000 due 2027-02-05 at 17:00 UTC'],
                          ['Row 3', 'Surplus AX-7 receipt', 'Quantity: 100 units on 2027-02-20 at 17:00 UTC'],
                          ['Row 4', 'Surplus purchase price', 'INR 600,000 due 2027-02-28 at 17:00 UTC']]}]}]

from extra_contracts import ADDITIONAL_CONTRACTS
CONTRACTS += ADDITIONAL_CONTRACTS
