# Odin integration progress

Plan: docs/superpowers/plans/2026-10-25-odin-integration.md

User authorized implementation of the existing evaluation design against the
supplied backend. Continue inline under Superpowers with test-first changes.
The fresh clone isolates product edits from the original independent evaluator.
No existing local backend changes were present. Docker is installed but its
daemon is unavailable; use a temporary SQLite database and BM25-only retrieval
for offline integration checks. Dense pgvector integration remains a live check.

Pre-flight interfaces: hook payloads -> collector -> ExecutionResult -> existing
deterministic/DeepEval checks -> reports and separate LangSmith observer.
No expected/golden output enters product execution.

Tasks 1–3 complete: initial 8 tests RED -> GREEN, then actual SQLite/BM25
retrieval, fake-model compiled analysis graph, subtree tools and subprocess
cancellation tests. Scoped subscribers, complete source telemetry and isolated
adapter/CLI configs are implemented. Golden dataset schema generated.

Task 4 complete: product trace root/child, evaluator score feedback, product link
and hidden I/O verified through synthetic LangSmith API upload/readback. No model
calls or contract uploads were made. Credential lives only in ignored .env files.

Final independent review: fresh gpt-6-astra agent, read-only, no credentials read.
All three P1 findings fixed in one regression pass:
- tool_probe write_state opt-in fence: RED -> GREEN.
- automatic child exception disclosure: PrivateClient sanitizes errors; actual
  RunnableLambda child exception transport regression passes.
- dropped tool document context: observed_documents retains every source for
  security checks; model_context keeps actual initial passages + rendered tool
  messages for DeepEval; foreign-tenant regression RED -> GREEN.
An additional artifact provenance regression showed overwritten records kept the
old writer's run ID; updating run_id on actual writes now makes that test pass.

Final verification: `uv run --locked --all-extras pytest -q --tb=short`:
132 passed, including all 19 original backend tests. Ruff lint and formatting
passed (27 evaluator/example/test files). Wheel + source distribution built;
127 installed packages compatible. Real registry CLI: 9 passed, exit 0.
Existing safe fixture CLI: 18 passed + 5 optional judge skips, exit 0.
Known-vulnerable fixture: 10 failures, exit 1 as expected.

Decisions/limits: workspace root owns the evaluator and backend/ owns the clone;
keep both together. No GitHub push, no model accuracy claim before goldens, no
live dense pgvector test while Docker is unavailable. Exact product usage is
left unknown because the existing provider budget misses failed attempts.
Graphs require disposable DB assertion and database reset between experiments;
evaluation fences are not production prompt-injection classifiers.
