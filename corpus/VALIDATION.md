# Validation record - 2026-10-25

## Performed

- Built exactly 15 PDFs between exactly three registered companies: eight Aurora/Forge and seven Aurora/Willow. No self-contracts or additional contracting entities occur.
- Rewrote openings and subject-specific language; reordered C02, C05, C07 and C08; introduced grouped and nested articles in C09-C15. Checked 15 distinct first headings, drafting forms and effective dates. Required cover keys remain consistent; no visible document versions or fictional-data labels occur.
- Added and verified 15 commercial/operational tables, including purchase orders, rent/notice calendars, processing instructions, milestone billing, equipment registers, dispatch cards and warranty handling.
- Verified 230 numbered body clauses and 46 schedule/annex rows against the final PDF text and one-based page locations. Updated hashes and evaluator evidence after renumbering.
- Rendered and visually inspected the 43 pages. No clipping, missing characters, overlapping blocks or broken tables was seen. Dedicated final signature pages are retained where the execution block does not fit the preceding page. Poppler reports its unused Symbol display-font warning; the document characters render correctly.
- Updated Markdown/structured company context, 64 resettable scenarios, 94 paired .eml/.txt fixtures, expected terms/cases, coverage, 12 trap entries, eight conflict-matrix entries and a 15-contract remedy catalog. All 15 documents appear in scenario assertions. DEMO-PORTFOLIO loads the same 14 initial IDs as the global manifest and later introduces C08.
- Checked clause/schedule regexes without spurious numeric starts, legal-party/signatory references, timestamp order, event enums, source/evaluator isolation, input paths and absence of future C08 details from the initial registry.
- Independently checked selected monetary/date constants, including notice cutoffs, partial-payment fees, outage thresholds/caps, project payment and delay dates, equipment hand-back charges, recovery credits, warranty delay and the 17-date hosting gap. Byte-identical PDF regeneration passes.
- Packaging verifies ZIP CRCs, 14 initial PDFs, one arrival PDF, and no evaluator files in input archives. SHA256SUMS.txt accompanies the distribution.
- Golden dataset validation verifies 384 role/scenario vectors, 15 contract extraction records, 114 typed facts, 276 citation units and 36 worked agent examples. Checks include source hashes, evidence references, agent-specific inputs, clock visibility and separation of expected answers from proposed inputs. No actual agents are executed by this validation.

## Practical limits

The 64 cases are authored expectations, not executed Odin results. Real agent extraction/replay, API/Gmail integration, LLM fallback, dashboard behavior, legal enforceability, independent human oracle review, live rehearsal and latency measurements were not verified. The 13 runtime fault cases remain specifications. No external mail or notice has been sent.

Use the eight root README commands to reproduce checks. Company grouping verifies the three party-based memberships (15/8/7) and byte equality with canonical PDFs. Machine corpus results are in ignored work/validation.json; golden checks print their counts and status. Re-render affected PDFs after any content or layout change.
