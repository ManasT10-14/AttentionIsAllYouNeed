# New-contract email events

Each business row is an independent reset case. Open the paired .txt file for the subject and body, or use the .eml file. Replace the placeholder recipient with the logged-in company inbox. No mail has been sent.

| Event | Contract / routing | Type | Observation |
| --- | --- | --- | --- |
| EVT-V3-0001 | AUR-2027-001 | INVOICE_RECEIVED | Nimbus issued invoice NIM-JAN-01 for the January hosting fee of INR 200,000 for PROD-AUR |
| EVT-V3-0002 | AUR-2027-001 | SERVICE_OUTAGE | Incident INC-PROD-01 affected PROD-AUR and RESIDENT-ONE continuously from 10:00 to 13:00 IST today |
| EVT-V3-0003 | AUR-2027-001 | SLA_BREACH | Incident INC-MAINT-02 interrupted PROD-AUR and RESIDENT-ONE for 45 minutes today, from 10:15 to 11:00 IST |
| EVT-V3-0004 | AUR-2027-002 | PAYMENT_LATE | Willow has not paid the January portal invoice PORT-JAN-01 for INR 120,000 |
| EVT-V3-0005 | AUR-2027-002 | SERVICE_OUTAGE | RESIDENT-ONE incident PORT-45 lasted from 09:00 to 09:45 IST on March 2 |
| EVT-V3-0006 | AUR-2027-002 | RENEWAL_NOTICE_RECEIVED | Willow sent a written notice today requesting non-renewal of RESIDENT-ONE at December 31 |
| EVT-V3-0007 | AUR-2027-003 | DELIVERY_LATE | The complete PO-AX9-100 lot reached UNIT-A at 17:00 IST on May 23, three calendar dates after its May 20 deadline |
| EVT-V3-0008 | AUR-2027-003 | DELIVERY_RECEIVED | Receipt DEL-AX9-100 confirms physical delivery of the complete 100-unit AX9 lot at UNIT-A today at 17:00 IST |
| EVT-V3-0009 | AUR-2027-003 | INVOICE_RECEIVED | Forge issued balance invoice FORGE-BAL-01 for INR 560,000 after the complete lot arrived May 23 |
| EVT-V3-0010 | AUR-2027-004 | PRICE_CHANGE | Copperline asks to increase the AX9 unit price from INR 7,500 to INR 8,250 for future call-offs with immediate effect |
| EVT-V3-0011 | AUR-2027-004 | CUSTOM | Procurement audit found a separate signed purchase order PO-AX9-EXTRA-02 placed by Aurora with Forge on February 10 for one AX9 lot for an Indian project |
| EVT-V3-0012 | AUR-2027-004 | FORCE_MAJEURE | Copperline reports a factory shutdown and asks Aurora to source AX9 elsewhere |
| EVT-V3-0013 | AUR-2027-005 | PAYMENT_MADE | Bank confirmation TX-RENT-60000 shows Aurora paid INR 60,000 toward January rent on January 8 |
| EVT-V3-0014 | AUR-2027-005 | TERMINATION_NOTICE_RECEIVED | Willow served a written convenience termination notice received by Aurora today |
| EVT-V3-0015 | AUR-2027-005 | CUSTOM | UNIT-A inspection HOLD-01 and Aurora's admission confirm Aurora has remained in possession continuously from July 1 through today, July 4, without a signed extension or termination variation |
| EVT-V3-0016 | AUR-2027-006 | INVOICE_RECEIVED | SwiftRoute delivered consignment FR-AX9-100 on May 25 at 16:00 IST and issued a valid freight invoice FREIGHT-01 for INR 30,000 at 18:00 IST today |
| EVT-V3-0017 | AUR-2027-006 | DELIVERY_LATE | Consignment FR-AX9-100 was fully delivered today at 16:00 IST |
| EVT-V3-0018 | AUR-2027-006 | FORCE_MAJEURE | SwiftRoute alleges a route closure and requests a two-day extension of booking FR-AX9-100 |
| EVT-V3-0019 | AUR-2027-007 | SLA_BREACH | Sentinel received valid priority-one alert SOC-P1-01 in its monitored mailbox at 10:00 IST today and acknowledged it at 10:40 IST |
| EVT-V3-0020 | AUR-2027-007 | PARTY_CHANGE | Sentinel says it intends to assign the monitoring contract to another legal entity on April 1 |
| EVT-V3-0021 | AUR-2027-007 | CUSTOM | Aurora sent a low-priority advisory question to Sentinel on March 10 at 15:00 IST and has no answer as of March 12 at 15:00 IST |
| EVT-V3-0022 | AUR-2027-008 | SLA_BREACH | Nimbus received valid priority-one restore request RESTORE-01 at 10:00 IST today |
| EVT-V3-0023 | AUR-2027-008 | CUSTOM | This case includes two notifications for the same RESTORE-01 completion: message RESTORE-FIRST at 16:00 and RESTORE-REPEAT at 16:05 today |
| EVT-V3-0024 | AUR-2027-008 | CUSTOM | Aurora asks whether Nimbus must accept a new production recovery ticket today under the backup schedule |
| EVT-V3-0025 | AUR-2027-009 | INVOICE_RECEIVED | Forge issued M1 invoice INT-M1-01 for INR 300,000 on March 1 |
| EVT-V3-0026 | AUR-2027-009 | CUSTOM | Forge demonstrated M1 today at 17:00 IST, after its February 28 deadline |
| EVT-V3-0027 | AUR-2027-009 | DISPUTE_RAISED | Aurora wants to end the SOW for convenience on April 24 after giving notice today |
| EVT-V3-0028 | ALL | REGULATORY_CHANGE | Aurora compliance distributes advisory REG-APR-01 concerning possible new personal-data reporting guidance |
| EVT-V3-0029 | UNKNOWN | SERVICE_OUTAGE | Service PROD-AUR and resident application RESIDENT-ONE were unavailable continuously from 11:00 to 12:00 IST today |
| EVT-V3-0030 | AUR-2027-005 | PAYMENT_MISSED | Aurora has made no payment toward January UNIT-A rent of INR 100,000 as of January 12 at 18:00 IST |

There are also seven additional email files for comma-list routing, EVENT_ID replay, missing EVENT_ID, recoverable fallback, missing time, invalid date and invalid type. The eighth parser/dedup case replays an existing Gmail message and therefore needs no additional email file.

Expected results are in oracle/event_goldens.jsonl and oracle/parser_goldens.jsonl. Keep these out of agent prompts. See EMAIL_INTEGRATION.md for strict parsing, bounded fallback, rejection, deduplication, clock and label requirements.
