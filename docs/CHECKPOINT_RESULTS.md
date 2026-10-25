# Checkpoint results - 2026-10-25

Representative live baseline across all 15 contracts, with full offline corpus
validation. These are measured engineering results, not a claim that all authored
goldens pass or that the product is production-ready.

| Scope | Result |
| --- | --- |
| Corpus validation | 15 PDFs / 43 pages, 64 scenarios, 384 agent vectors, 114 typed assertions and 276 citations validated |
| Retrieval | All 276 queries executed: recall@5 = 1.0000, mean reciprocal rank@5 = 0.9342; 517 passing checks, 35 ranking-threshold failures |
| RAG | 15 contract questions answered; final recorded/retried judging: 65 passing checks, 10 quality failures, zero errors |
| Thor extraction | 15 real extractions; baseline assessments: 5 passing checks, 25 failures, zero errors; includes unmapped typed concepts |
| Integrated agents | PAY-03 executed with actual upstream state for all six roles: 15 passing checks, 8 quality/mapping failures, zero errors |
| Security | Direct injection, document injection and foreign-tenant canary cases: 12 passing checks, zero failures/errors |
| Tracing | Product trace IDs and evaluator feedback uploaded; no observer warnings in the selected baseline reports |

Full observations remain in ignored local reports/. Selected sources are
corpus-retrieval-verified.json, corpus-rag-verified.json,
corpus-thor-rescored.json, corpus-agent-final.json and corpus-security.json.
The entire 384-agent/276-RAG live set was not run; the user chose the representative
baseline. All vectors are compiled and available for later expanded testing.

## Known limitations

- The supplied local PostgreSQL login failed authentication. Evaluation used
  isolated SQLite workspaces and explicitly BM25-only retrieval. PostgreSQL,
  pgvector and dense retrieval have not been validated by this baseline.
- Product extraction and financial schemas do not yet represent every authored
  rate, cap and deadline. Missing mappings are reported, not filled from goldens.
- The product clock stores dates rather than exact UTC timestamps. Detailed
  temporal/financial assertions still require backend improvements.
- Transient judge timeouts were recorded and retried against saved observations.
  Completed results were retained; no product calls were repeated for those retries.
- The corpus is authored reference material, without independent human legal review.
- Historical pre-fix cached latency values are not a performance benchmark.

## Cleanup and verification

The repository root is now Desktop/Ragnarok, with one backend/ directory.
Old parent-workspace copies and virtual environments were archived to the sibling
Ragnarok-cleanup-backup-20261025-180927 directory. Credentials were preserved
locally and remain ignored by Git.

Two pending regressions were completed during cleanup: recurring monthly due
rules no longer use an exceptional first invoice date, and unredacted quality
observations can be re-scored while recorded security outcomes remain protected.
No new live evaluation was performed during repository cleanup.
