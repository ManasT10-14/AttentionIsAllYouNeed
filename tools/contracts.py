"""Authored contract text. Never ingest generator source."""

CONTRACTS = [{'id': 'C01',
  'title': 'Cloud Hosting Agreement',
  'parties': ['P01', 'P02'],
  'clauses': [('PARTIES AND SERVICE',
               'Aurora Systems Private Limited (P01, Customer) and Nimbus Harbor Private Limited (P02, '
               'Provider) agree to hosting service SVC-ATLAS for Aurora application APP-ATLAS. Provider is '
               'not a party to Aurora customer contracts. Company legal notice address: '
               'aurora-legal@aurora.example. Counterparty legal notice address: legal@nimbus.example.'),
              ('TERM AND FEES',
               'This agreement is signed on 2026-12-15 and runs from 2027-01-01 through 2027-12-31 '
               'inclusive. It expires without automatic renewal. The fixed hosting fee is INR 200,000 per '
               'calendar month, due on the fifth day of that month at 17:00 UTC. No late-payment charge is '
               'agreed.'),
              ('SERVICE CREDIT',
               'For each distinct incident of more than 60 consecutive minutes of complete unavailability of '
               'SVC-ATLAS, Provider owes Customer a credit of INR 10,000. An incident of exactly 60 minutes '
               'does not qualify. Distinct incidents must have separate restoration and outage records. '
               'Total credits are capped at INR 20,000 per UTC calendar month of outage start. Credits are '
               'recoverable by Customer and are not Customer liabilities.'),
              ('MAINTENANCE EXCLUSION',
               'An incident is excluded from clause clause 3.1 of C01 only if Customer approved that '
               'specific maintenance window at least 48 hours before its start and the outage was wholly '
               'inside that window. Provider scheduling alone is not approval. If approval evidence is '
               'missing, applicability is unresolved pending evidence; do not presume approval or its '
               'absence.'),
              ('CREDIT PROCEDURE AND REMEDY',
               'Customer must email a claim identifying the incident within 10 calendar days after '
               'restoration to claims@nimbus.example. A valid claim is due by 17:00 UTC on the tenth '
               'following calendar date. Credits are the sole monetary remedy for service unavailability '
               'under this agreement; no downstream damages are reimbursed.'),
              ('INCIDENT EVIDENCE',
               'Provider restoration logs identify incident ID, service ID, start, end and any scheduled '
               'window. A later signed approval record may supply earlier approval evidence. A repeated log '
               'for the same incident is not a second outage. Corrected records supersede the identified '
               'prior record without creating another incident.'),
              ('NOTICE AND CURE',
               'For a material breach other than service unavailability, written notice must be received at '
               'legal@nimbus.example. Provider has 10 calendar days after receipt to cure, ending at 17:00 '
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
              ('EXECUTION', 'Mira Sen for Aurora and Dev Rao for Nimbus record execution on 2026-12-15.'),
              ('LIMITATION OF LIABILITY',
               'The monthly service-credit cap in clause 3.1 is INR 20,000. For other claims, each party '
               'aggregate liability is capped at INR 1,000,000, except fraud, wilful misconduct and '
               'indemnity obligations. Downstream service liabilities are not reimbursed under this '
               'agreement.'),
              ('INDEMNITY',
               'Each party shall indemnify the other against third-party claims caused by its infringement '
               'of intellectual property rights or unauthorized disclosure of confidential information, '
               'including reasonable defense costs. The indemnified party shall promptly notify the other '
               'party and reasonably cooperate in the defense.'),
              ('CONFIDENTIALITY',
               'Each party shall protect the other party non-public commercial, technical and personal '
               'information, use it only to perform this agreement, and restrict access to personnel bound '
               'by confidentiality. These obligations survive termination for 3 years, except information '
               'already public without breach.'),
              ('COMPLIANCE',
               'Each party shall comply with laws applicable to its own performance, including the Digital '
               'Personal Data Protection Act, 2023 where applicable and GDPR for processing within its '
               'applicable scope. Where personal data is processed, access controls and documented '
               'incident-response procedures shall be maintained. No ISO certification is represented by '
               'this clause.'),
              ('ASSIGNMENT',
               'Neither party may assign this agreement without the other party prior written consent, '
               'except an assignment to an affiliate on 30 calendar days written notice if the assigning '
               'party remains liable. A change of control does not silently replace a contracting party or '
               'waive a consent requirement.'),
              ('FORCE MAJEURE',
               'A party prevented from performing by an event beyond its reasonable control shall notify the '
               'other party within 5 calendar days after discovery and provide evidence of the affected '
               'obligation and mitigation. Accrued payment obligations are not excused. Relief requires a '
               'causal connection and does not apply automatically to every outage or supplier delay.'),
              ('EXCLUSIVITY',
               'This agreement is non-exclusive. No non-compete or restriction on dealing with other '
               'counterparties is imposed except as expressly stated in this clause.'),
              ('TERMINATION FOR CONVENIENCE',
               'Either party may terminate for convenience by written notice received at the other party '
               'legal notice address at least 30 calendar days before the proposed termination date. Accrued '
               'payment obligations and express survival provisions remain effective. Any expressly agreed '
               'early-exit fee remains subject to its stated conditions.')],
  'type': 'vendor',
  'effective_date': '2027-01-01',
  'governing_law': 'India'},
 {'id': 'C02',
  'title': 'Customer Application Service Agreement',
  'parties': ['P01', 'P03'],
  'clauses': [('PARTIES AND APPLICATION',
               'Aurora Systems Private Limited (P01, Service Supplier) supplies APP-ATLAS to Cedar Market '
               'Private Limited (P03, Customer). APP-ATLAS depends entirely on Nimbus service SVC-ATLAS '
               'identified in Aurora hosting agreement C01. Cedar is not a party to C01. Company legal '
               'notice address: aurora-legal@aurora.example. Counterparty legal notice address: '
               'legal@cedar.example.'),
              ('TERM AND FEES',
               'Signed on 2026-12-16; effective 2027-01-01 through 2027-12-31 inclusive, with no automatic '
               'renewal. Cedar pays Aurora INR 300,000 monthly by the fifth day at 17:00 UTC. No late charge '
               'is specified.'),
              ('CUSTOMER SERVICE REMEDY',
               'For each distinct incident of more than 30 consecutive minutes of complete APP-ATLAS '
               'unavailability, Aurora owes Cedar a service credit of INR 15,000, capped at INR 45,000 per '
               'UTC month of outage start. Exactly 30 minutes does not qualify. This credit accrues '
               'automatically on restoration; Cedar need not file a claim. It is Aurora payable exposure.'),
              ('EXCLUSIONS AND DEPENDENCE',
               'No maintenance exclusion applies to the service credits in this agreement, even for '
               'maintenance approved under C01. Nimbus failure does not excuse Aurora performance. Separate '
               'restoration and outage records distinguish incidents. Duplicates and corrections for one '
               'incident do not create additional credits.'),
              ('LIABILITY BOUNDARY',
               'The service credits in clause 3.1 of C02 are the sole monetary remedy for unavailability. Do '
               'not add speculative lost profits. Recoverable hosting credits under C01 do not reduce the '
               'gross amount owed to Cedar; show any net illustration separately and label it contingent on '
               'recovery.'),
              ('NOTICE AND TERMINATION',
               'Material breaches other than unavailability require written notice received at '
               'aurora-legal@aurora.example and a 10-calendar-day cure period ending at 17:00 UTC on the '
               'tenth following date. An uncured breach permits a separate termination notice after the cure '
               'deadline.'),
              ('DISPUTES',
               'Indian law governs. Pune courts have exclusive jurisdiction for disputes arising solely '
               'under C02. A joint proceeding including claims under any other agreement requires a '
               'separately signed forum agreement by all relevant parties; no such agreement is attached.'),
              ('OTHER AGREEMENTS',
               'C02 governs APP-ATLAS subscription services only. A separate agreement between the same '
               'parties does not amend, replace, or consolidate C02 unless it expressly identifies the '
               'changed provisions. Rights already accrued survive expiry.'),
              ('TIME AND EVIDENCE',
               'All dates and times use UTC, with calendar days and no holiday adjustments. Date-only '
               'deadlines end at 17:00 UTC. Logs linking SVC-ATLAS to APP-ATLAS are sufficient incident '
               'observations for this service chain. Financial amounts exclude taxes.'),
              ('EXECUTION', 'Mira Sen for Aurora and Isha Shah for Cedar record execution on 2026-12-16.'),
              ('LIMITATION OF LIABILITY',
               'Service-credit liability is limited to INR 45,000 per UTC calendar month under clause 3.1. '
               'Other aggregate liability is capped at INR 1,000,000, except fraud, wilful misconduct and '
               'indemnity obligations.'),
              ('INDEMNITY',
               'Each party shall indemnify the other against third-party claims caused by its infringement '
               'of intellectual property rights or unauthorized disclosure of confidential information, '
               'including reasonable defense costs. The indemnified party shall promptly notify the other '
               'party and reasonably cooperate in the defense.'),
              ('CONFIDENTIALITY',
               'Each party shall protect the other party non-public commercial, technical and personal '
               'information, use it only to perform this agreement, and restrict access to personnel bound '
               'by confidentiality. These obligations survive termination for 3 years, except information '
               'already public without breach.'),
              ('COMPLIANCE',
               'Each party shall comply with laws applicable to its own performance, including the Digital '
               'Personal Data Protection Act, 2023 where applicable and GDPR for processing within its '
               'applicable scope. Where personal data is processed, access controls and documented '
               'incident-response procedures shall be maintained. No ISO certification is represented by '
               'this clause.'),
              ('ASSIGNMENT',
               'Neither party may assign this agreement without the other party prior written consent, '
               'except an assignment to an affiliate on 30 calendar days written notice if the assigning '
               'party remains liable. A change of control does not silently replace a contracting party or '
               'waive a consent requirement.'),
              ('FORCE MAJEURE',
               'A party prevented from performing by an event beyond its reasonable control shall notify the '
               'other party within 5 calendar days after discovery and provide evidence of the affected '
               'obligation and mitigation. Accrued payment obligations are not excused. Relief requires a '
               'causal connection and does not apply automatically to every outage or supplier delay.'),
              ('EXCLUSIVITY',
               'This agreement is non-exclusive. No non-compete or restriction on dealing with other '
               'counterparties is imposed except as expressly stated in this clause.'),
              ('TERMINATION FOR CONVENIENCE',
               'Either party may terminate for convenience by written notice received at the other party '
               'legal notice address at least 30 calendar days before the proposed termination date. Accrued '
               'payment obligations and express survival provisions remain effective. Any expressly agreed '
               'early-exit fee remains subject to its stated conditions.'),
              ('OFFICE-DEPENDENT SUPPORT',
               'Throughout the term ending 2027-12-31, Aurora shall maintain the staffed APP-ATLAS support '
               'operation at office UNIT-5 covered by lease C05. Relocation requires Cedar prior written '
               'approval. No relocation approval is attached. The initial C05 lease term ends on 2027-06-30 '
               'and has its own renewal and notice provisions.')],
  'type': 'saas',
  'effective_date': '2027-01-01',
  'governing_law': 'India'},
 {'id': 'C03',
  'title': 'Component Supplier Agreement',
  'parties': ['P01', 'P04'],
  'clauses': [('PARTIES AND PURCHASE ORDER',
               'Aurora Systems Private Limited (P01, Buyer) purchases 100 AX-7 controllers from Forge Vale '
               'Private Limited (P04, Supplier) under purchase order PO-AX7. This is a single delivery lot, '
               'LOT-AX7. Company legal notice address: aurora-legal@aurora.example. Counterparty legal '
               'notice address: notices@forge.example.'),
              ('TERM AND DELIVERY',
               'Signed on 2026-12-17 and effective from 2027-01-01 until 2027-03-31. Supplier must deliver '
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
              ('EXECUTION', 'Mira Sen for Aurora and Anil Das for Forge record execution on 2026-12-17.'),
              ('LIMITATION OF LIABILITY',
               'For service unavailability or delivery delay, the exclusive remedies and caps expressly '
               'stated in this agreement apply. For other claims, each party aggregate liability is capped '
               'at INR 1,000,000, except fraud, wilful misconduct and indemnity obligations. No cap from '
               'another contract is incorporated.'),
              ('INDEMNITY',
               'Each party shall indemnify the other against third-party claims caused by its infringement '
               'of intellectual property rights or unauthorized disclosure of confidential information, '
               'including reasonable defense costs. The indemnified party shall promptly notify the other '
               'party and reasonably cooperate in the defense.'),
              ('CONFIDENTIALITY',
               'Each party shall protect the other party non-public commercial, technical and personal '
               'information, use it only to perform this agreement, and restrict access to personnel bound '
               'by confidentiality. These obligations survive termination for 3 years, except information '
               'already public without breach.'),
              ('COMPLIANCE',
               'Each party shall comply with laws applicable to its own performance, including the Digital '
               'Personal Data Protection Act, 2023 where applicable and GDPR for processing within its '
               'applicable scope. Where personal data is processed, access controls and documented '
               'incident-response procedures shall be maintained. No ISO certification is represented by '
               'this clause.'),
              ('ASSIGNMENT',
               'Neither party may assign this agreement without the other party prior written consent, '
               'except an assignment to an affiliate on 30 calendar days written notice if the assigning '
               'party remains liable. A change of control does not silently replace a contracting party or '
               'waive a consent requirement.'),
              ('FORCE MAJEURE',
               'A party prevented from performing by an event beyond its reasonable control shall notify the '
               'other party within 5 calendar days after discovery and provide evidence of the affected '
               'obligation and mitigation. Accrued payment obligations are not excused. Relief requires a '
               'causal connection and does not apply automatically to every outage or supplier delay.'),
              ('EXCLUSIVE PROCUREMENT',
               'From 2027-01-01 through 2027-03-31, Aurora shall source all AX-7 controllers exclusively '
               'from Forge. Aurora shall not commit to purchase AX-7 controllers from another supplier '
               'during that period without Forge prior written waiver. No waiver is attached.'),
              ('TERMINATION FOR CONVENIENCE',
               'Either party may terminate for convenience by written notice received at the other party '
               'legal notice address at least 30 calendar days before the proposed termination date. Accrued '
               'payment obligations and express survival provisions remain effective. Any expressly agreed '
               'early-exit fee remains subject to its stated conditions.'),
              ('CHANGE REQUEST RESPONSE',
               'Supplier shall respond to an Aurora delivery-change request within a reasonable time. The '
               'parties have not specified a numeric response deadline or a monetary remedy for this '
               'response obligation.')],
  'type': 'supply',
  'effective_date': '2027-01-01',
  'governing_law': 'India'},
 {'id': 'C04',
  'title': 'Customer Controller Supply Agreement',
  'parties': ['P01', 'P05'],
  'clauses': [('PARTIES AND GOODS',
               'Aurora Systems Private Limited (P01, Seller) supplies 100 AX-7 controllers from LOT-AX7 to '
               'Harbor Works Private Limited (P05, Customer) under order SO-AX7. Company legal notice '
               'address: aurora-legal@aurora.example. Counterparty legal notice address: '
               'legal@harbor.example.'),
              ('DELIVERY AND DEPENDENCY',
               'Signed on 2026-12-18 and effective 2027-01-01 through 2027-03-31. Aurora must deliver the '
               'entire conforming lot to Harbor by 2027-02-08 at 17:00 UTC. Aurora sources that same lot '
               'under C03, whose latest promised depot delivery is 2027-02-10 at 17:00 UTC. Transfer '
               'requires no minimum additional transit time under this agreement. Supplier failure does not '
               'excuse Aurora delay.'),
              ('PRICE',
               'Harbor owes INR 650,000 within 30 calendar days after full conforming delivery acceptance '
               'and receipt of invoice INV-SOAX7, by 17:00 UTC on the thirtieth following date. No '
               'acceptance or invoice is presumed. Late-payment interest is addressed in clause 19.1.'),
              ('DELAY CHARGES',
               'For each calendar date beginning on 2027-02-09 when the complete conforming lot remains '
               'undelivered to Harbor at 00:00 UTC, Aurora owes Harbor INR 5,000, capped at INR 50,000 per '
               'lot. Delivery later that date preserves that date charge. This is Aurora payable exposure. '
               'These charges are the sole monetary remedy for delay.'),
              ('EVIDENCE',
               'A receipt for SO-AX7 must identify all 100 conforming units and Harbor destination DEPOT-H. '
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
               'not itself invalidate either agreement.'),
              ('CLOCK',
               'All times are UTC and days calendar days, without holiday adjustments. Date-only deadlines '
               'end at 17:00 UTC. Prices and charges exclude taxes.'),
              ('EXECUTION', 'Mira Sen for Aurora and Rhea Nair for Harbor record execution on 2026-12-18.'),
              ('LIMITATION OF LIABILITY',
               'For service unavailability or delivery delay, the exclusive remedies and caps expressly '
               'stated in this agreement apply. For other claims, each party aggregate liability is capped '
               'at INR 1,000,000, except fraud, wilful misconduct and indemnity obligations. No cap from '
               'another contract is incorporated.'),
              ('INDEMNITY',
               'Aurora shall indemnify Harbor against all third-party claims and defense costs arising from '
               'the controllers or their use, including claims caused by Harbor own negligence. Harbor has '
               'no reciprocal indemnity obligation. This indemnity is excluded from the aggregate liability '
               'cap in clause 11.1.'),
              ('CONFIDENTIALITY',
               'Each party shall protect the other party non-public commercial, technical and personal '
               'information, use it only to perform this agreement, and restrict access to personnel bound '
               'by confidentiality. These obligations survive termination for 3 years, except information '
               'already public without breach.'),
              ('COMPLIANCE',
               'Each party shall comply with laws applicable to its own performance, including the Digital '
               'Personal Data Protection Act, 2023 where applicable and GDPR for processing within its '
               'applicable scope. Where personal data is processed, access controls and documented '
               'incident-response procedures shall be maintained. No ISO certification is represented by '
               'this clause.'),
              ('ASSIGNMENT',
               'Neither party may assign this agreement without the other party prior written consent, '
               'except an assignment to an affiliate on 30 calendar days written notice if the assigning '
               'party remains liable. A change of control does not silently replace a contracting party or '
               'waive a consent requirement.'),
              ('FORCE MAJEURE',
               'A party prevented from performing by an event beyond its reasonable control shall notify the '
               'other party within 5 calendar days after discovery and provide evidence of the affected '
               'obligation and mitigation. Accrued payment obligations are not excused. Relief requires a '
               'causal connection and does not apply automatically to every outage or supplier delay.'),
              ('EXCLUSIVITY',
               'This agreement is non-exclusive. No non-compete or restriction on dealing with other '
               'counterparties is imposed except as expressly stated in this clause.'),
              ('TERMINATION FOR CONVENIENCE',
               'Either party may terminate for convenience by written notice received at the other party '
               'legal notice address at least 30 calendar days before the proposed termination date. Accrued '
               'payment obligations and express survival provisions remain effective. Any expressly agreed '
               'early-exit fee remains subject to its stated conditions.'),
              ('LATE-PAYMENT INTEREST',
               'Late-payment interest rate: ____ % per month on overdue invoiced principal. The percentage '
               'has not been completed. No numeric late-payment interest amount can be determined from this '
               'execution copy.')],
  'type': 'supply',
  'effective_date': '2027-01-01',
  'governing_law': 'India'},
 {'id': 'C05',
  'title': 'Office Lease',
  'parties': ['P01', 'P06'],
  'clauses': [('PARTIES AND PREMISES',
               'Aurora Systems Private Limited (P01, Tenant) leases office UNIT-5 at 5 Example Quay from '
               'Willow Estates Private Limited (P06, Landlord). Company legal notice address: '
               'aurora-legal@aurora.example. Counterparty legal notice address: notices@willow.example.'),
              ('TERM AND RENEWAL',
               'Signed on 2026-12-19. The initial term is 2027-01-01 through 2027-06-30 inclusive. It renews '
               'automatically for 6 months on the same rent unless Tenant gives valid non-renewal notice at '
               'least 30 calendar days before the current term end date. The notice cutoff is at 17:00 UTC '
               'on the calculated cutoff date.'),
              ('RENT',
               'Rent is INR 100,000 per calendar month, due on the twentieth day of that month at 17:00 UTC, '
               'with invoice reference RENT-YYYY-MM. The first invoice is RENT-2027-01. No deposit or taxes '
               'are included under this agreement.'),
              ('GRACE AND LATE CHARGE',
               'Unpaid rent has a grace period through 23:59:59 UTC on the twenty-fifth day of the due '
               'month. Starting at 00:00 UTC on the twenty-sixth, a simple charge of 0.1 percent of unpaid '
               'rent principal at that instant accrues for each started UTC calendar date until full '
               'payment. There is no compounding and no charge on earlier charges. Total late charges per '
               'invoice are capped at INR 5,000. A payment later on a date does not reverse that date '
               'charge.'),
              ('PAYMENT ALLOCATION',
               'Only cleared payments identifying the invoice and currency INR reduce its rent principal, '
               'from their occurred_at time. Apply principal before charges. A repeated bank transaction ID '
               'is not another payment; a reversal expressly identifying that transaction removes the '
               'payment from its reversal time. Unrelated invoices do not reduce this rent.'),
              ('VALID NOTICE',
               'Non-renewal notice must be received by notices@willow.example with subject UNIT-5 '
               'NON-RENEWAL and authorized Tenant sender Mira Sen. Dispatch alone, an incorrect address, or '
               'receipt after the cutoff is insufficient. No acknowledgment from Landlord is required if '
               'receipt is evidenced.'),
              ('RENEWAL CONSEQUENCE',
               'A missed or invalid non-renewal notice commits the next 6-month term at INR 100,000 monthly. '
               'Report INR 600,000 as a future committed rent obligation, not a present fine. Do not add it '
               'again to the same months of scheduled rent. The current term remains in effect when a timely '
               'notice prevents renewal.'),
              ('DEFAULT AND TERMINATION',
               'Landlord must give Tenant written material-breach notice at aurora-legal@aurora.example and '
               'allow 10 calendar days after receipt, through 17:00 UTC on the tenth following date, to '
               'cure. An uncured breach permits a separate termination notice; mere late rent does not '
               'automatically terminate this lease.'),
              ('TIME AND FORUM',
               'All times are UTC and all days calendar days. No business-day or holiday adjustment applies. '
               'Indian law and exclusive Bengaluru court jurisdiction govern. No unspecified damages or fees '
               'are inferred.'),
              ('EXECUTION', 'Mira Sen for Aurora and Kavya Paul for Willow record execution on 2026-12-19.'),
              ('LIMITATION OF LIABILITY',
               'Late charges are capped at INR 5,000 per rent invoice under clause 4.1. Accrued rent and '
               'committed renewal rent are payment obligations, not damages. Other aggregate damages are '
               'capped at INR 1,000,000, excluding fraud and indemnity obligations.'),
              ('INDEMNITY',
               'Each party shall indemnify the other against third-party claims caused by its infringement '
               'of intellectual property rights or unauthorized disclosure of confidential information, '
               'including reasonable defense costs. The indemnified party shall promptly notify the other '
               'party and reasonably cooperate in the defense.'),
              ('CONFIDENTIALITY',
               'Each party shall protect the other party non-public commercial, technical and personal '
               'information, use it only to perform this agreement, and restrict access to personnel bound '
               'by confidentiality. These obligations survive termination for 3 years, except information '
               'already public without breach.'),
              ('COMPLIANCE',
               'Each party shall comply with laws applicable to its own performance, including the Digital '
               'Personal Data Protection Act, 2023 where applicable and GDPR for processing within its '
               'applicable scope. Where personal data is processed, access controls and documented '
               'incident-response procedures shall be maintained. No ISO certification is represented by '
               'this clause.'),
              ('ASSIGNMENT',
               'Neither party may assign this agreement without the other party prior written consent, '
               'except an assignment to an affiliate on 30 calendar days written notice if the assigning '
               'party remains liable. A change of control does not silently replace a contracting party or '
               'waive a consent requirement.'),
              ('FORCE MAJEURE',
               'A party prevented from performing by an event beyond its reasonable control shall notify the '
               'other party within 5 calendar days after discovery and provide evidence of the affected '
               'obligation and mitigation. Accrued payment obligations are not excused. Relief requires a '
               'causal connection and does not apply automatically to every outage or supplier delay.'),
              ('EXCLUSIVITY',
               'This agreement is non-exclusive. No non-compete or restriction on dealing with other '
               'counterparties is imposed except as expressly stated in this clause.'),
              ('TERMINATION FOR CONVENIENCE',
               'No unilateral early termination for convenience is granted during a committed lease term. '
               'Non-renewal at term end requires compliance with clauses 2.1 and 6.1. Earlier release '
               'requires a signed agreement between Landlord and Tenant.')],
  'type': 'lease',
  'effective_date': '2027-01-01',
  'governing_law': 'India'},
 {'id': 'C06',
  'title': 'Software Subscription with Embedded Amendment',
  'parties': ['P01', 'P07'],
  'clauses': [('PARTIES AND SUBSCRIPTION',
               'Aurora Systems Private Limited (P01, Subscriber) licenses TOOL-LUMEN from Lumen Stack '
               'Private Limited (P07, Vendor). This document includes the original agreement and an executed '
               'amendment. Company legal notice address: aurora-legal@aurora.example. Counterparty legal '
               'notice address: legal@lumen.example.'),
              ('TERM',
               'The original agreement is signed on 2026-12-20. Subscription runs from 2027-01-01 through '
               '2027-12-31 inclusive and automatically renews for one year unless valid non-renewal notice '
               'is given under clause 3.1 of C06 as amended when applicable.'),
              ('ORIGINAL NOTICE WINDOW',
               'In the original agreement, Subscriber must give notice at least 60 calendar days before the '
               'current term end date. Notice must be received at notices@lumen.example by 17:00 UTC on the '
               'calculated cutoff date and identify TOOL-LUMEN. See the embedded amendment clause 19.1 of '
               'C06-clause 19.3 of C06 for its limited change and effective date.'),
              ('SUBSCRIPTION PRICE',
               'The license fee is INR 120,000 for the initial year, due on 2027-01-31 at 17:00 UTC under '
               'invoice LUMEN-2027. Renewal price remains INR 120,000 per year. There is no agreed late '
               'charge.'),
              ('SERVICE SCOPE',
               'Subscriber may use TOOL-LUMEN for internal document indexing only. This subscription neither '
               'changes APP-ATLAS obligations nor incorporates any Lumen marketing statements.'),
              ('TERMINATION',
               'A material-breach notice received at the other party legal email gives a 10-calendar-day '
               'cure period, ending at 17:00 UTC on the tenth following date. After an uncured breach a '
               'separate termination notice may be served. Vendor legal email is legal@lumen.example; '
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
              ('EXECUTION', 'Mira Sen for Aurora and Nikhil Roy for Lumen record execution on 2026-12-20.'),
              ('LIMITATION OF LIABILITY',
               'For service unavailability or delivery delay, the exclusive remedies and caps expressly '
               'stated in this agreement apply. For other claims, each party aggregate liability is capped '
               'at INR 1,000,000, except fraud, wilful misconduct and indemnity obligations. No cap from '
               'another contract is incorporated.'),
              ('INDEMNITY',
               'Each party shall indemnify the other against third-party claims caused by its infringement '
               'of intellectual property rights or unauthorized disclosure of confidential information, '
               'including reasonable defense costs. The indemnified party shall promptly notify the other '
               'party and reasonably cooperate in the defense.'),
              ('CONFIDENTIALITY',
               'Each party shall protect the other party non-public commercial, technical and personal '
               'information, use it only to perform this agreement, and restrict access to personnel bound '
               'by confidentiality. These obligations survive termination for 3 years, except information '
               'already public without breach.'),
              ('COMPLIANCE',
               'Each party shall comply with laws applicable to its own performance, including the Digital '
               'Personal Data Protection Act, 2023 where applicable and GDPR for processing within its '
               'applicable scope. Where personal data is processed, access controls and documented '
               'incident-response procedures shall be maintained. No ISO certification is represented by '
               'this clause.'),
              ('ASSIGNMENT',
               'Neither party may assign this agreement without the other party prior written consent, '
               'except an assignment to an affiliate on 30 calendar days written notice if the assigning '
               'party remains liable. A change of control does not silently replace a contracting party or '
               'waive a consent requirement.'),
              ('FORCE MAJEURE',
               'A party prevented from performing by an event beyond its reasonable control shall notify the '
               'other party within 5 calendar days after discovery and provide evidence of the affected '
               'obligation and mitigation. Accrued payment obligations are not excused. Relief requires a '
               'causal connection and does not apply automatically to every outage or supplier delay.'),
              ('EXCLUSIVITY',
               'This agreement is non-exclusive. No non-compete or restriction on dealing with other '
               'counterparties is imposed except as expressly stated in this clause.'),
              ('TERMINATION FOR CONVENIENCE',
               'Either party may terminate for convenience by written notice received at the other party '
               'legal notice address at least 30 calendar days before the proposed termination date. Accrued '
               'payment obligations and express survival provisions remain effective. Any expressly agreed '
               'early-exit fee remains subject to its stated conditions.')],
  'amendment': [('A1',
                 'LIMITED CHANGE',
                 'Aurora and Lumen, as the same parties to C06, execute this amendment on 2027-01-10. '
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
                 'Mira Sen for Aurora and Nikhil Roy for Lumen record amendment execution on 2027-01-10. All '
                 'provisions not expressly changed remain in force.')],
  'type': 'saas',
  'effective_date': '2027-01-01',
  'governing_law': 'India'},
 {'id': 'C07',
  'title': 'Data Processing Agreement',
  'parties': ['P01', 'P08'],
  'clauses': [('PARTIES AND DATASET',
               'Aurora Systems Private Limited (P01, Controller) appoints Quill Data Private Limited (P08, '
               'Processor) for dataset DS-CEDAR stored in region REGION-NORTH. The parties handle records '
               'under this agreement. Company legal notice address: aurora-legal@aurora.example. '
               'Counterparty legal notice address: legal@quill.example.'),
              ('TERM AND FEE',
               'Signed on 2026-12-21; term 2027-01-01 through 2027-12-31 with no automatic renewal. Aurora '
               'owes INR 50,000 monthly by the fifth day at 17:00 UTC. No late fee is specified.'),
              ('APPLICABLE RULE',
               'For this agreement, an applicable rule-change notice is a supplied record issued by Data '
               'Standards Board, naming DS-CEDAR, REGION-NORTH and its rule ID, effective date and required '
               'safeguards. The notice must identify the applicable contractual safeguard requirements. A '
               'different dataset, region or issuer does not trigger clause 4.1 of C07.'),
              ('SAFEGUARD RESPONSE',
               'For an applicable notice, Processor must deliver the specified safeguard attestation to '
               'Controller by the later of the rule effective instant and 17:00 UTC on the tenth calendar '
               'date following receipt by Processor. A safeguard attestation matching rule ID, dataset and '
               'region by that deadline satisfies this obligation.'),
              ('REMEDIES AND UNCERTAINTY',
               'If the attestation is missing after the clause 4.1 of C07 deadline, the obligation is '
               'breached and Controller may request immediate remediation and legal review. No regulatory '
               'fine, automatic damages, per-day fee or monetary cap for this event is supplied. Do not '
               'quantify an unspecified fine as zero or as a guessed number.'),
              ('EVIDENCE',
               'A notice records issuer, dataset, region, rule ID, effective time, safeguards and Processor '
               'receipt time. A correction identifies the superseded notice. The contractual receipt time '
               'and the monitoring system received_at time are distinct. System knowledge must be limited to '
               'records received by the simulated clock.'),
              ('CONFIDENTIALITY',
               'Processor must use DS-CEDAR solely to provide this service, restrict access to authorized '
               'staff, and report an observed unauthorized disclosure to Controller within 24 hours of '
               'Processor discovery. No disclosure is assumed without supporting observations.'),
              ('TERMINATION',
               'An uncured material breach may support termination only after written notice received at '
               'legal@quill.example and a 10-calendar-day cure period through 17:00 UTC on the tenth '
               'following date. A separate termination notice is then required. Missing attestation alone '
               'does not prove unauthorized disclosure.'),
              ('CLOCK AND FORUM',
               'All times UTC, days calendar days, no holiday adjustments. Indian law and exclusive '
               'Bengaluru courts apply to the agreement. Fees exclude taxes.'),
              ('EXECUTION', 'Mira Sen for Aurora and Tara Bose for Quill record execution on 2026-12-21.'),
              ('LIMITATION OF LIABILITY',
               'Ordinary contractual damages are capped at INR 1,000,000, excluding fraud, wilful misconduct '
               'and indemnity obligations. This cap is not a regulatory fine, does not set a fine amount, '
               'and does not itself quantify any regulatory liability.'),
              ('INDEMNITY',
               'Each party shall indemnify the other against third-party claims caused by its infringement '
               'of intellectual property rights or unauthorized disclosure of confidential information, '
               'including reasonable defense costs. The indemnified party shall promptly notify the other '
               'party and reasonably cooperate in the defense.'),
              ('CONFIDENTIALITY',
               'Each party shall protect the other party non-public commercial, technical and personal '
               'information, use it only to perform this agreement, and restrict access to personnel bound '
               'by confidentiality. These obligations survive termination for 3 years, except information '
               'already public without breach.'),
              ('COMPLIANCE',
               'Each party shall comply with laws applicable to its own performance, including the Digital '
               'Personal Data Protection Act, 2023 where applicable and GDPR for processing within its '
               'applicable scope. Where personal data is processed, access controls and documented '
               'incident-response procedures shall be maintained. No ISO certification is represented by '
               'this clause.'),
              ('ASSIGNMENT',
               'Neither party may assign this agreement without the other party prior written consent, '
               'except an assignment to an affiliate on 30 calendar days written notice if the assigning '
               'party remains liable. A change of control does not silently replace a contracting party or '
               'waive a consent requirement.'),
              ('FORCE MAJEURE',
               'A party prevented from performing by an event beyond its reasonable control shall notify the '
               'other party within 5 calendar days after discovery and provide evidence of the affected '
               'obligation and mitigation. Accrued payment obligations are not excused. Relief requires a '
               'causal connection and does not apply automatically to every outage or supplier delay.'),
              ('EXCLUSIVITY',
               'This agreement is non-exclusive. No non-compete or restriction on dealing with other '
               'counterparties is imposed except as expressly stated in this clause.'),
              ('TERMINATION FOR CONVENIENCE',
               'Either party may terminate for convenience by written notice received at the other party '
               'legal notice address at least 30 calendar days before the proposed termination date. Accrued '
               'payment obligations and express survival provisions remain effective. Any expressly agreed '
               'early-exit fee remains subject to its stated conditions.')],
  'type': 'nda',
  'effective_date': '2027-01-01',
  'governing_law': 'India'},
 {'id': 'C08',
  'title': 'Supply and Campaign Partnership Agreement',
  'parties': ['P01', 'P03'],
  'clauses': [('PARTIES AND INDEPENDENT SCOPE',
               'Aurora Systems Private Limited (P01) and Cedar Market Private Limited (P03), the same '
               'parties as C02, execute a separate partnership for campaign CAMP-SPRING. This agreement '
               'concerns co-marketing and the separate controller procurement in clause 20.1; C02 continues '
               'to govern APP-ATLAS subscription services. Company legal notice address: '
               'aurora-legal@aurora.example. Counterparty legal notice address: legal@cedar.example.'),
              ('DATES AND EFFECT',
               'Signed on 2027-01-20; effective from 2027-02-01 at 00:00 UTC through 2027-05-31 inclusive, '
               'with no automatic renewal. No obligations under this agreement accrue before its effective '
               'date. Ingestion or upload does not change that date.'),
              ('CAMPAIGN FUNDING',
               'Aurora shall pay Cedar INR 80,000 for CAMP-SPRING by 2027-02-05 at 17:00 UTC against invoice '
               'CAMP-2027. No late charge or unspecified campaign damages are agreed.'),
              ('CEDAR DELIVERABLE',
               'Cedar shall deliver an approved campaign plan for CAMP-SPRING by 2027-02-03 at 17:00 UTC. '
               'Approval requires an Aurora signed approval record identifying the plan. A submitted but '
               'unapproved draft is insufficient. No plan is assumed from the passage of time.'),
              ('NO AMENDMENT OR REPLACEMENT',
               'C08 neither amends nor replaces any part of C02 and does not offset service credits or '
               'combine invoices. APP-ATLAS maintenance and service-credit obligations remain exactly as '
               'stated in C02. This agreement contains no commitment to change C01.'),
              ('DISPUTES AND JOINT CLAIMS',
               'Indian law governs. Mumbai courts have exclusive jurisdiction over claims solely under C08. '
               'Any combined proceeding involving C02 also requires a separately signed forum agreement '
               'under clause 7.1 of C02 and this clause. The parties have not supplied that agreement. Do '
               'not assume one forum automatically controls all claims.'),
              ('TERMINATION AND SURVIVAL',
               'Written breach notice to the other party legal email gives 10 calendar days after receipt to '
               'cure, through 17:00 UTC on the tenth following date. Thereafter an uncured breach permits a '
               'separate termination notice. Accrued payment obligations survive termination.'),
              ('NOTICES',
               'Aurora legal email is aurora-legal@aurora.example and Cedar legal email is '
               'legal@cedar.example. A notice takes effect on proven receipt. A C08 notice does not by '
               'itself terminate C02.'),
              ('TIME AND ACCOUNTING',
               'All times UTC and days calendar days, without holiday adjustments. Date-only deadlines end '
               'at 17:00 UTC. All amounts exclude taxes. Independent scope does not imply the absence of all '
               'business risk; assess each agreement on its evidence.'),
              ('EXECUTION', 'Mira Sen for Aurora and Isha Shah for Cedar record execution on 2027-01-20.'),
              ('LIMITATION OF LIABILITY',
               'For service unavailability or delivery delay, the exclusive remedies and caps expressly '
               'stated in this agreement apply. For other claims, each party aggregate liability is capped '
               'at INR 1,000,000, except fraud, wilful misconduct and indemnity obligations. No cap from '
               'another contract is incorporated.'),
              ('INDEMNITY',
               'Each party shall indemnify the other against third-party claims caused by its infringement '
               'of intellectual property rights or unauthorized disclosure of confidential information, '
               'including reasonable defense costs. The indemnified party shall promptly notify the other '
               'party and reasonably cooperate in the defense.'),
              ('CONFIDENTIALITY',
               'Each party shall protect the other party non-public commercial, technical and personal '
               'information, use it only to perform this agreement, and restrict access to personnel bound '
               'by confidentiality. These obligations survive termination for 3 years, except information '
               'already public without breach.'),
              ('COMPLIANCE',
               'Each party shall comply with laws applicable to its own performance, including the Digital '
               'Personal Data Protection Act, 2023 where applicable and GDPR for processing within its '
               'applicable scope. Where personal data is processed, access controls and documented '
               'incident-response procedures shall be maintained. No ISO certification is represented by '
               'this clause.'),
              ('ASSIGNMENT',
               'Neither party may assign this agreement without the other party prior written consent, '
               'except an assignment to an affiliate on 30 calendar days written notice if the assigning '
               'party remains liable. A change of control does not silently replace a contracting party or '
               'waive a consent requirement.'),
              ('FORCE MAJEURE',
               'A party prevented from performing by an event beyond its reasonable control shall notify the '
               'other party within 5 calendar days after discovery and provide evidence of the affected '
               'obligation and mitigation. Accrued payment obligations are not excused. Relief requires a '
               'causal connection and does not apply automatically to every outage or supplier delay.'),
              ('EXCLUSIVITY',
               'This agreement is non-exclusive. No non-compete or restriction on dealing with other '
               'counterparties is imposed except as expressly stated in this clause.'),
              ('TERMINATION FOR CONVENIENCE',
               'Either party may terminate for convenience by written notice received at the other party '
               'legal notice address at least 30 calendar days before the proposed termination date. Accrued '
               'payment obligations and express survival provisions remain effective. Any expressly agreed '
               'early-exit fee remains subject to its stated conditions.'),
              ('CONVENIENCE NOTICE PERIOD',
               'For termination for convenience under clause 18.1, either party must give 60 calendar days '
               'prior written notice. Clause 18.1 states 30 calendar days for the same notice. Both '
               'provisions form part of this agreement and no order of precedence between them is stated.'),
              ('ADDITIONAL CONTROLLER PROCUREMENT',
               'Aurora commits to purchase 100 AX-7 controllers from Cedar for delivery on 2027-02-20 at '
               '17:00 UTC for INR 600,000, payable on 2027-02-28 at 17:00 UTC against invoice '
               'CEDAR-AX7-2027. This is a separate procurement from order SO-AX7 and does not amend or waive '
               'any restriction in C03. No Forge waiver or Cedar release is attached.')],
  'type': 'supply',
  'effective_date': '2027-02-01',
  'governing_law': 'India'}]
