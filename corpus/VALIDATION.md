# Validation record - version 2, 2026-10-25

## Performed

- Rebuilt all eight PDFs without version labels, with exact seven-field first-page covers, uppercase headings, numeric clause starts and no fictional-data labels.
- Checked the supplied clause and schedule regexes against extracted PDF lines, including uniqueness and absence of spurious starts from wrapping.
- Matched 152 numbered body clauses and two Schedule A rows to final PDF text and exact one-based page locations; regenerated evaluator citations and manifest SHA-256 values.
- Rendered and visually inspected all 24 final pages. No clipped text, overlapping elements, broken labels or missing glyphs was visible. Poppler emitted a missing Symbol display-font message but no Symbol glyphs are used.
- Validated the ten company-context keys and the INR 10,00,000 approval threshold, with equivalent structured sidecar.
- Authored 45 isolated scenarios including all requested traps and retained boundary/control cases. Inspected expected terms and references for changed clause identities. Oracle independence is source separation and manual constants, not an independent human review.
- Built 64 paired .eml/.txt fixtures: 44 scenario observations, 16 enum templates and four parser-edge examples. Checked strict syntax, timezone-bearing timestamps, enum coverage, globally unique explicit email IDs, optional missing EVENT_ID, and expected fallback cases.
- Checked scenario visibility/reference rules, selected independent date/decimal calculations, all 37 source requirements, and 13 runtime acceptance specifications. PDF regeneration produces identical hashes.
- Packaging checks archive CRCs, exactly seven initial PDFs, one held-back PDF, and absence of evaluator material from input ZIPs. Distribution SHA-256 checksums accompany the ZIPs.

## Not performed

No Odin agent pipeline, UI, Gmail connection, OAuth flow, token encryption operation, 15-second poller, actual Groq fallback, rejection auto-reply, external notice, live rehearsal or latency measurement was executed. The expected outcomes are not passing Odin results. No independent human evaluator review or OCR benchmark was performed. No commit or push was made.

Run the five commands in the repository README to reproduce authoring checks. Machine-readable results are stored in ignored work/validation.json. Re-render affected PDF pages after changes to document text, typography or pagination.
