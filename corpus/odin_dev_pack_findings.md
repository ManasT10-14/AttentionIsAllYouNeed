# Odin dev pack — internal answer sheet (regression oracle)

INTERNAL ONLY. Never put this file in a prompt. Hand-verified 2026-10-26 against
`corpus/odin_dev_pack/bundle/*`. Every `"quote"` below is an exact single-line
substring of the cited `.txt` (checked by `backend/tests/test_dev_pack_oracle.py`).
Citation format: `DocID ref "quote"`.

Family map: STD = shared terms incorporated by A1, B1, C1 (cover page controls
over STD). A1+A2+A3 = StratoNode family (SLA controls over A1 for uptime/credits;
A3 controls over A2, effective 2027-01-01). B1+B2 = Harbor family (B2 controls for
data processing / security / breach notification). C1 = Vantage. D1 = Pixelwright
(standalone, does not incorporate STD).

Key numbers: StratoNode fee $8,000/mo; Harbor $40,000/mo ($41,200 from 2027-09-15);
Vantage $18,500/mo + $12,000 setup; Pixelwright $65,000 fixed (M1 10k, M2 15k,
M3 20k, M4 12k, M5 8k). Minutes: Feb 2027 = 40,320; Mar/May 2027 = 44,640.

---------------------------------------------------------------------------
## 1. Cross-contract contradictions & territorial conflicts

1.1 **Overlapping Pacific-Northwest exclusivities (B1 vs C1).** Quillhub granted Harbor
exclusivity for Route Optimizer Enterprise in WA/OR retail grocery (B1, Sept 2026), then
granted Vantage exclusivity over *all tiers including Enterprise* in WA/OR third-party
logistics (C1, Nov 2026) with no carve-out for the existing Harbor licence. Same product,
same territory; a WA/OR grocer that runs its own warehousing/last-mile (or any 3PL serving
grocery) falls in both. Consequence: any new PNW licence risks breaching one exclusivity →
material breach / termination for cause (STD §5.2), damages capped at 12 months' fees
(neither exclusivity is an Unlimited Claim): Harbor $480,000, Vantage $222,000.
- B1 §6.1 "grants Harbor Retail the exclusive right to use the Route Optimizer"
- B1 §6.1 "sector (defined as retail grocery operations headquartered in the"
- C1 §4.1 "grants Vantage Logistics the exclusive right to use the Route"
- C1 §4.1 "Optimizer platform (including all tiers: Standard, Pro, and"
- C1 §4.1 "(defined as third-party logistics companies headquartered in the"

1.2 **Conflicting governing law / forum** across a back-to-back chain: A1 Oregon
(Multnomah), B1 Washington (King County), C1 Oregon, D1 Texas. A Harbor SLA/data-breach
claim is litigated in WA while recovery from StratoNode must be pursued in OR — no
consolidation, inconsistent outcomes.
- A1 Section H "Governing Law:    State of Oregon"
- B1 Section K "Governing Law:    State of Washington"
- C1 Section G "Governing Law:    State of Oregon"
- D1 §10.3 "This Agreement will be governed by the laws of the State"

1.3 **Notice / breach-notification timing mismatch (upstream 72h vs downstream 24h).**
StratoNode only has to notify Quillhub of a Security Incident within 72h; Quillhub must
notify Harbor of a Data Breach within 24h of becoming aware, and of any unplanned
disruption within 4h. Back-to-back gap: Quillhub can be in breach before StratoNode is
even obliged to tell it.
- A1 Section F "Standard Terms, StratoNode will notify Quillhub within 72 hours of becoming"
- STD §3.3 "undue delay (and in any event within 72 hours) after Provider becomes"
- B1 §5.1 "within twenty-four (24) hours of becoming aware of the Data Breach."
- B2 §3.1 "Retail within twenty-four (24) hours of becoming aware of the Data"
- B1 §4.1 "Retail's contact (nora.chen@harborretail.com) within four (4) hours"
- A1 Section I.1 (I.1) "will use commercially reasonable efforts to notify Quillhub's" (StratoNode's 4h is efforts-only)

1.4 **"Becomes aware" defined differently.** B1 §5.1 triggers on "actual or reasonably
suspected" access; B2 §3.1 only at "a reasonable degree of certainty". B2 controls for
breach notification (B2 preamble), but B1 §5.1 says it is "in addition to" STD §3.3 —
ambiguity a regulator/Harbor will read against Quillhub.
- B1 §5.1 "If Quillhub becomes aware of any actual or"
- B2 §3.1 "certainty that a security incident has resulted in unauthorized access"
- B2 preamble "this Addendum controls with respect to data processing,"

1.5 **Liability asymmetry.** Data Breach obligations to Harbor are Unlimited Claims
(B1 Section J, B2 §8.1); StratoNode's liability to Quillhub is capped at 12 months' fees
($96,000) with unlimited only for Confidentiality / Restrictions (A1 Section G). A
StratoNode-caused breach of Harbor data leaves Quillhub uncapped downstream, capped upstream.
- B1 Section J "Unlimited Claims:    Data Breach obligations under Section 5;"
- B2 §8.1 "Data Breach obligations under Section 3 of this Addendum are Unlimited"
- A1 Section G "Unlimited Claims:    Breach of Section 10 (Confidentiality);"

1.6 **Term mismatch.** A1 initial term ends 2028-07-31 and StratoNode may now non-renew
on only 60 days' notice (A3 Section 3), but Quillhub owes hosting-dependent service to
Vantage to 2029-05-14 and Harbor to 2029-09-14. Migration help only 90 days, paid.
- A1 Section B "Initial Subscription Period: 24 months (ending July 31, 2028)"
- B1 Section B "Initial Subscription Period: 36 months (ending September 14, 2029)"
- A1 Section I.2 (I.2) "a period of up to 90 days following the effective date of termination,"

1.7 **Maintenance definitions don't line up.** StratoNode maintenance: 48h notice, ≤4h,
≤2/month. Harbor maintenance: 72h notice, ≤2h, ≤1/month. StratoNode-compliant maintenance
can be Harbor Downtime (see E-01).
- A2 §1.3 "Customer about at least 48 hours in advance via email to the Customer's"
- A2 §1.3 "Maintenance windows will not exceed four (4) hours per occurrence and"
- B1 §3.1 "notified Harbor Retail about at least 72 hours in advance via email to"
- B1 §3.1 "two (2) hours per occurrence and will not be scheduled more than once"

1.8 (minor) STD auto-renews for "the same length" but cover pages set 12/24-month renewal
terms — cover page controls. STD §1.6 lets Provider train ML on Customer Content; B2 §1.3
restricts Harbor Personal Data to documented instructions (B2 controls).
- STD §5.1 "automatically renew for additional Subscription Periods of the same"
- STD (preamble) "If the Cover Page and these Standard Terms conflict, the Cover Page controls."
- STD §1.6 "Usage Data and Customer Content may be used to develop,"
- B2 §1.3 "Quillhub will process Personal Data only on documented instructions"

---------------------------------------------------------------------------
## 2. Upstream vs downstream financial recovery gaps

2.1 **Structural uptime gap.** Harbor target 99.9% / Vantage 99.5% vs StratoNode 99.5%.
Any month between 99.5% and 99.9% → Quillhub owes Harbor 15% ($6,000) and recovers $0 from
the StratoNode table (only the A3 +5% $400 if one incident >60 min).
- B1 §3.1 "ninety-nine and nine-tenths percent (99.9%) of the minutes in each"
- A2 §2.1 "and one-half percent (99.5%) of the minutes in each calendar month, not"
- B1 §3.3 "Harbor Retail fifteen percent (15%) of the Monthly Fee for that month"
- C1 §3.2 "Vantage Logistics ten percent (10%) of the Monthly Fee for that month"

2.2 **Cap gap.** Max monthly downstream: Harbor 20% × $40,000 = $8,000 + Vantage
10% × $18,500 = $1,850 → $9,850. Max upstream: 50% × $8,000 = $4,000. StratoNode credits
are the sole remedy, so the rest is unrecoverable.
- B1 §3.4 "will not exceed twenty percent (20%) of the Monthly Fee for that month."
- A2 §3.3 "will not exceed fifty percent (50%) of the Monthly Fee for that month."
- A2 §3.4 "Sole Remedy. Service Credits are Customer's sole and exclusive remedy"

2.3 **Claim-window gap.** Upstream credit request 15 days after month end (A3, was 30 in
A2); downstream Harbor may claim 45 days, Vantage 30 days. Quillhub must file upstream
before customers are even due to claim. Upstream claims also need monitoring evidence and
the calculated uptime %.
- A3 Section 1 "submit a written request to Provider's Notice Address within fifteen"
- B1 §3.5 "within forty-five (45) days after the end of the calendar month in"
- C1 §3.3 "writing within thirty (30) days after the end of the calendar month"
- A3 Section 1 "(d) the calculated Monthly Uptime"

2.4 **March 2027 incident (E-04, 190 min, single incident).** Uptime (44,640−190)/44,640
= 99.57%. StratoNode: ≥99.5% → table credit $0; A3 >60-min add-on 5% = $400 (arguable: the
add-on sits in §3.1 whose trigger is falling below the target — flag as disputed).
Harbor: 99.57% < 99.9% → $6,000 owed if claimed in time. Gap $5,600–$6,000.
StratoNode request deadline 2027-04-15 (A3), not 2027-04-30 (A2).
- A3 Section 2 "Additionally, if Downtime in a single incident exceeds sixty (60)"
- A3 Section 2 "Credit equal to five percent (5%) of the Monthly Fee for that month,"

2.5 **May 2027 incident (E-12, 505 min).** Uptime 98.87%. StratoNode band 95.0–<99.0 →
25% = $2,000 + 5% add-on $400 = $2,400 (under $4,000 cap). Harbor 15% = $6,000. Vantage
$0 (incident precedes 2027-05-15 go-live, despite E-15 saying "MISSED"). Gap $3,600.
StratoNode request deadline 2027-06-15 (A3) — same day Harbor's formal request (E-17)
arrives. StratoNode may dispute "unavailable" (60% request failure, packet loss) under
A2 §1.2. Ledger shows full $8,000 StratoNode payments for June/July — no credit applied.
- A2 §3.1 "95.0% to < 99.0%                   25% of Monthly Fee"
- A2 §1.2 "Cloud Service is unavailable, excluding Scheduled Maintenance and any"

2.6 **Exclusions gap.** StratoNode excludes force majeure and third-party (ISP/DNS/CA)
downtime (A2 §5.4, §5.5); Harbor's Downtime excludes only Scheduled Maintenance (B1 §3.2).
- A2 §5.5 "Downtime resulting from actions or inactions of third parties outside"
- B1 §3.2 "minutes during which the Platform is unavailable, excluding"

---------------------------------------------------------------------------
## 3. Silent amendment supersession (A3 over A2 and over A1)

A3 effective 2027-01-01, "this Amendment controls" over the SLA.
3.1 A3 Section 1 replaces A2 §3.2: credit request window 30 → **15 days**; adds content
requirements (specific times of each incident, own-monitoring/status-page evidence,
calculated uptime %) and a 10-business-day Provider response.
- A2 §3.2 "submit a written request to Provider's Notice Address within thirty (30)"
- A3 Section 1 "Section 3.2 of the SLA is deleted in its entirety and replaced with the"
- A3 Section 1 "(10) business days. If Provider confirms that the Uptime Target was"
3.2 A3 Section 2 replaces A2 §3.1: same table + 5% add-on for any incident >60 consecutive
minutes, subject to the §3.3 cap.
- A3 Section 2 "Section 3.1 of the SLA is deleted in its entirety and replaced with the"
3.3 **A3 Section 3 silently amends the A1 cover page** (an "SLA amendment" changing the
hosting agreement): non-renewal notice 90 → **60 days**. A1 renewal notice deadline is now
2028-06-01 (was 2028-05-02). StratoNode can exit with less runway for Quillhub.
- A3 Section 3 "Section B of the Cover Page (Contract ID: QH-STRATO-2026-001) is amended as"
- A3 Section 3 "The Non-Renewal Notice Period is changed from ninety (90) days to sixty"
- A1 Section B "Non-Renewal Notice Period: 90 days before the end of the then-current"
3.4 A1 Section E: SLA controls over the cover page for uptime/credits (reverse of the usual
cover-page-controls rule).
- A1 Section E "and the SLA, the SLA controls with respect to uptime commitments and service"
- A3 preamble "Except as expressly modified by this Amendment, the SLA remains in full force"
- A3 preamble "AMENDMENT EFFECTIVE DATE:  January 1, 2027"

---------------------------------------------------------------------------
## 4. Hidden external defaults & lapsed policies

4.1 **Insurance expiry vs Harbor requirement.** B1 §7.1 requires CGL ≥ $2M/occurrence and
Tech E&O/Cyber ≥ $3M/claim throughout the Subscription Period (to 2029-09-14). Quillhub's
policies meet the limits exactly but both expire 2027-06-30 with no renewal confirmation.
E-16 (2027-06-10): instructions needed by 2027-06-25 or policies lapse 2027-06-30 23:59.
Lapse = material breach (B1 §7.2); Quillhub must notify Harbor in writing within 5 business
days (≈ by 2027-07-08 counting the 2027-07-05 holiday); Harbor may terminate if not cured
within 15 days of its notice (B1 §8.2) — puts $40,000/month (~$1.1M remaining) at risk.
No contract other than B1 has an insurance clause.
- B1 §7.1 "$2,000,000 per occurrence; and (b) Technology Errors & Omissions and"
- B1 §7.1 "Cyber Liability insurance with limits of at least $3,000,000 per"
- B1 §7.2 "A lapse in required"
- B1 §7.2 "Retail in writing within five (5) business days. A lapse in required"
- B1 §8.2 "insurance required by Section 7 and does not cure the lapse within"
- context.txt: "Expiry:       June 30, 2027" / "No renewal confirmation has been" (not a contract; cite as company context)

4.2 **C1 Effective Date is a blank placeholder** until written go-live confirmation;
E-14 (2027-05-15, CEO) fixes Effective Date 2027-05-15, term to 2029-05-14.
- C1 Section B "Effective Date:              [TO BE INSERTED UPON GO-LIVE]"
4.3 **B2 is incomplete** — Exhibits A and B missing; processing description / TOMs
unverifiable.
- B2 (end) "was not included in this copy. The document appears to be incomplete.]"
4.4 D1 deemed acceptance runs on the *Company's* holiday CSV, which has wrong dates (see 7.3).
- D1 §4.2 "by Company (data/holidays.csv in this bundle)."

---------------------------------------------------------------------------
## 5. Timeline & obligation tracking (deadlines)

| Date | Obligation | Source |
|---|---|---|
| 2027-03-10 | Harbor RCA for Mar-3 outage (5 business days after restore) — no event shows it sent | B1 §4.2 |
| 2027-03-12 | M3 Rejection Notice deadline (received Sun 2027-02-28) else deemed accepted | D1 §4.2/§4.3 |
| 2027-03-31 | M5 due (no delivery event) | D1 Exhibit A |
| 2027-04-15 | StratoNode credit request for March (A3: 15 days; A2 would be 04-30) | A3 Section 1 |
| 2027-05-04 | M4 Rejection Notice deadline (received Tue 2027-04-20) else deemed accepted → $12,000 | D1 §4.2/§4.3 |
| 2027-05-07 | Harbor RCA for May 1–2 outage | B1 §4.2 |
| 2027-05-15 | Harbor's last day to request March credit (45 days) | B1 §3.5 |
| 2027-05-17 | Harbor April invoice due (E-09) | B1 Section C |
| 2027-06-15 | StratoNode credit request for May ($2,400) | A3 Section 1 |
| 2027-06-25 | Insurer renewal instructions (E-16) | context / E-16 |
| 2027-06-30 | Insurance expiry → B1 §7.1 lapse | B1 §7.1/§7.2 |
| ~2027-07-08 | Notify Harbor of non-renewal of insurance (5 business days) | B1 §7.2 |
| 2027-07-15 | Harbor's last day to request May credit | B1 §3.5 |
| 2027-07-31 | Vantage setup fee due (E-18) | C1 Section C |
| 2027-09-15 | Harbor fee → $41,200 | B1 Section C |
| 2027-12-31 | D1 term ends, no auto-renewal | D1 §2.1/§2.2 |
| 2028-06-01 | A1 non-renewal notice (60 days, as amended by A3) | A3 Section 3 |
| 2029-02-13 | C1 non-renewal notice (90 days before 2029-05-14) | C1 Section B |
| 2029-03-18 | B1 non-renewal notice (180 days before 2029-09-14) | B1 Section B |

Checkpoint snapshots:
- **2027-03-15** (E-01..E-07): March already below Harbor 99.9% (190 min); Harbor 4h
  notice missed (E-05 sent ~28h after onset); RCA due 03-10 not evidenced; M3 deemed
  accepted 03-12 (and paid 02-18 *before* delivery); M4 overdue since 02-28; StratoNode
  March request due 04-15; insurance expires in 107 days.
- **2027-06-01** (+E-08..E-15): Harbor April invoice $40,000 overdue since 05-17
  (1.5%/month interest STD §4.4; suspension right after 30 days STD §2.2); March StratoNode
  window closed 04-15 (no filing event → $400 lost); May StratoNode request $2,400 due
  06-15; Harbor May exposure $6,000; M4 deemed accepted 05-04 → $12,000 payable; M5 overdue;
  Vantage live since 05-15 with setup fee + May/June fees unbilled; insurance expires in 29 days.
- **2027-09-15** (+E-16..E-18): absent renewal evidence, insurance lapsed 06-30 → B1 material
  breach, Harbor termination risk; Harbor credit request (E-17): May $6,000 valid, March
  $6,000 time-barred (requested 06-15 > 05-15); Vantage setup fee $12,000 due 07-31 (no
  payment recorded); May StratoNode window closed 06-15; Harbor fee now $41,200.
- **Harbor §8.1 termination NOT triggered**: misses in March and May are not consecutive
  (E-17 itself says so) — E-15's "second consecutive month" note is wrong. A June miss would
  make May+June consecutive.
  - B1 §8.1 "Percentage falls below the Harbor Uptime Target in any two (2)"

---------------------------------------------------------------------------
## 6. Event monitoring & action drafting (expected handling)

| Event | Classification | Expected consequence / action |
|---|---|---|
| E-01 StratoNode maintenance 01-25 02:00–05:00 UTC | maintenance | 3h window, notice 64.5h ahead: OK for StratoNode (48h, ≤4h) but sent to Dana, not the Operations contact ops@ (A2 §1.3). For Harbor it breaks the 72h/2h rule → any actual interruption is Harbor Downtime (99.6% if full 180 min → $6,000). Email says "Saturday" but 2027-01-25 is a Monday. Action: notify Harbor / log. |
| E-02 Harbor uptime question (Feb 3 & 7) | inquiry | Not a credit request; Feb met 99.97% (E-07). Reply with uptime data. |
| E-03 M3 delivered Sun 02-28 (due 01-31, late) | milestone | Review window to 03-12; 84.2% ≥ 80% coverage. Ledger shows M3 paid 02-18 before delivery. |
| E-04 StratoNode outage 03-03, 190 min | SLA incident | Draft StratoNode credit request to legal@stratonode.com / Portland Notice Address by 04-15 with A3 §3.2(a)–(d) contents ($400 add-on; table $0). Harbor exposure $6,000. |
| E-05 Quillhub notice to Harbor 03-04 14:30 | outbound notice | ~28h after onset → misses B1 §4.1 4h window; RCA due 03-10. |
| E-06 StratoNode marketing newsletter | **noise** | No action. |
| E-07 Feb uptime report | report | All targets met. |
| E-08 Vantage "thinking about not renewing" (phone-style email to Raj) | informal | NOT written notice: C1 Section B excludes emails not sent to the Notice Address; also not definite and the term had not started. Action: account-retention reply, no legal effect. |
| E-09 Harbor April invoice, due 05-17 | billing | Ledger marks it overdue (true only after 05-17). |
| E-10 Pixelwright phone call re M4 delay | informal | No written extension (D1 §10.6); internally inconsistent dates (call 04-15 targets "March 7"). M4 already late since 02-28. |
| E-11 M4 delivered Tue 04-20 | milestone | Rejection Notice by 05-04 to elena@pixelwright.co (WCAG 3 issues, 98.4% pass rate vs "must pass all automated tests") or deemed accepted → $12,000. |
| E-12 StratoNode outage 05-01/02, 505 min, no notice | SLA incident | StratoNode credit request by 06-15: 25% + 5% = $2,400. |
| E-13 Quillhub notice to Harbor 05-05 | outbound | ~3 days late vs 4h; RCA due 05-07. |
| E-14 Vantage go-live 05-15 (CEO) | effective date | C1 Effective Date 2027-05-15, term to 2029-05-14; fees start; 40h integration support 6 months. |
| E-15 May uptime report | report | Harbor MISSED ($6,000). Vantage claim wrong (pre go-live). "second consecutive" claim wrong. |
| E-16 Meridian renewal notice | **critical** | Renew by 06-25; else lapse → B1 §7.2 breach + 5-business-day notice to Harbor. Action: renewal instruction + certificate to Harbor. |
| E-17 Harbor formal credit request (to Notice Address) | claim | Accept May $6,000; March claim late under B1 §3.5 (may reject or concede for goodwill). Reply via Harbor Notice Address legal@harborretail.com. |
| (blank/malformed line, drop 2 line 8) | **rejected** | Not JSON — reject with reason, continue. |
| E-18 Vantage setup fee invoice 07-01 | billing | Fee was "payable upon execution" (Nov 2026) — billed 8 months late; monthly fees from 05-15 (≈ May pro-rata $10,145 + June $18,500) not billed. |

Expected drafted notices: (a) StratoNode SLA credit requests (March, May) to StratoNode
Notice Address within the A3 15-day window with (a)–(d) contents; (b) Rejection Notice for
M4 before 05-04; (c) Harbor reply on E-17 (accept May, reserve on March as time-barred);
(d) insurance renewal instruction + Harbor lapse notice if not renewed; (e) Vantage reply to
E-08 (no formal notice received; formal non-renewal must go to the Notice Address ≥90 days
before term end); (f) DPA/Data Breach notice template to Harbor General Counsel within 24h
(B1 §5.1 / B2 §3.1) — no breach event exists in the drops, so only a template.

Notice addresses:
- A1 StratoNode "Email: legal@stratonode.com"
- B1 Harbor "Email: legal@harborretail.com"
- C1 Vantage "Email: contracts@vantagelogistics.com"
- D1 §10.2 Pixelwright "Email: elena@pixelwright.co"
- C1 Section B "emails sent" … "do not constitute written" (quote: "to addresses other than the Notice Address) do not constitute written")

---------------------------------------------------------------------------
## 7. Data hygiene & resilience

7.1 Drop 2 line 8 is not JSON ("this is a malformed event line…") → reject, keep going.
7.2 Ledger anomalies (`payments_ledger.csv`):
  - M3 $20,000 paid 2027-02-18, before the deliverable was submitted (2027-02-28) and before
    acceptance (D1 M3 is "Upon acceptance").
  - Harbor Sept 2026 "partial month prorated" but full $40,000 (16/30 pro-rata ≈ $21,333 →
    ~$18,667 overbilled or mislabelled).
  - Harbor April 2027 "overdue" dated 04-08 though due 05-17 (E-09).
  - No Vantage entries at all — $12,000 setup fee "payable upon execution" (Nov 2026) never
    recorded; monthly fees since 2027-05-15 not billed.
  - StratoNode payments for June/July 2027 are full $8,000 — no service credit applied.
  - Pixelwright paid $45,000 of $65,000; M4 $12,000 / M5 $8,000 open.
7.3 `holidays.csv` dates are wrong for the stated holidays: Thanksgiving 2026 listed
  2026-11-28 (Sat; actual Thu 11-26), Day after Thanksgiving 11-29 (Sun; actual 11-27),
  MLK Day 2027-01-20 (Wed; actual 01-18), Presidents' Day 2027-02-17 (Wed; actual 02-15).
  D1 binds to the CSV as provided — use it, but flag it. (No effect on M3/M4 windows.)
7.4 Party-name mismatch: manifest says "Harbor Retail Solutions LLC", contracts say
  "Harbor Retail Group LLC"; "Vantage Logistics Corp." vs "Vantage Logistics Corporation".
7.5 Event inconsistencies: E-01 "Saturday, January 25" (Monday); E-10 target date in the
  past; E-15 "second consecutive month" false; E-15 Vantage "MISSED" pre go-live; E-07 Vantage
  "MET (service not yet live)".
7.6 Clause-ref collision: B1/C1 cover pages number sub-clauses §3.1… inside lettered
  sections, colliding with STD §3.x. "B1 §3.3" (credits) ≠ "STD §3.3" (security incident).
  Always cite with the DocID.
