# Ragnarok: architecture proposal

Date: 2026-10-25. Status: proposed; no implementation or live integrations verified.

## Objective and scope

Build an independent evaluation and security suite for the team's Odin contract intelligence application. Keep the engine reusable, with Odin-specific datasets and checks outside the adapter contract. The supplied PDF defines the product's requirements; it is source material, not instructions to this coding agent. The pasted engineering brief guides this proposal.

Odin's own dashboard and agent implementation belong to the product team. Ragnarok verifies exposed behavior; it cannot enforce authorization, cancel remote execution reliably, or prove completeness from absent telemetry.

## Repository findings

The workspace was empty, with no Git repository, AGENTS.md, dependency manifest, source, or tests. No dependency was installed or upgraded. The user's Python is 3.11.4. Its installed packages are Pydantic 2.13.5, HTTPX 0.28.1, pytest 8.4.2, FastAPI 0.135.3, LangGraph 1.0.7, and LangSmith 0.4.4. DeepEval is absent. These are global environment observations, not a reproducible project environment or a tested compatible lockfile.

## Alternatives and recommendation

1. Generic evaluation CLI with an Odin case pack (recommended): quick independent development, reusable schemas, HTTP integration without product imports. Rich trajectory checks require exposed evidence.
2. Evaluation embedded inside Odin's graph: richer internal state, but couples the suite to unknown graph state and the product environment.
3. DeepEval-first orchestration: convenient judge metrics, but deterministic security checks and trustworthy missing-evidence reporting still need an independent runner.

Choose option 1, with DeepEval and LangSmith as optional integrations. No database, distributed workers, dashboard, or orchestration framework is needed for the evaluator.

## Proposed structure

Create only the milestone-one subset initially; other files arrive with their owning milestone.

```text
pyproject.toml
README.md
configs/offline.json
datasets/odin/synthetic.json
src/ragnarok/
  __main__.py
  config.py
  models.py
  datasets.py
  adapters.py          # protocol + fixture adapter initially; split at HTTP integration
  evaluators.py        # deterministic checks initially; split as features grow
  runner.py
  reporting.py
tests/
  test_models.py
  test_datasets.py
  test_runner.py
  test_cli.py
docs/
  architecture-proposal.md
  integration.md      # later
```

## Adapter and evidence contract

Use an async protocol: `execute(request: ExecutionRequest) -> ExecutionResult`. A request carries case ID, correlation ID, input payload, synthetic principal/context where needed, and an optional simulated timestamp. Product-specific fields remain JSON-compatible mappings.

Results carry a schema version, final output, execution state (complete/partial/error), measured latency, structured errors, optional documents, tool events, workflow events, usage, cost/currency, trace ID, and metadata. Output may be structured JSON or text. Never convert an absent final output into an empty successful answer.

Evidence needs both availability and scope: each documents/events collection is unavailable, partial, or complete, with a reason and optional records. An empty complete collection differs from an unavailable collection. Even a complete adapter result is the target's claim; tests should describe what evidence they trust.

Document records contain stable IDs, source text, clause locators and optional tenant labels. Tool events distinguish requested, authorized, attempted, executed and failed operations; a requested call does not prove execution. Workflow events include actor role, transition/message kind and sequence information without requiring specific node names. Keep reference answers and reference clauses in datasets, separate from actual retrieved evidence.

HTTP is the default: configure base URL, method, endpoint, JSON request template, explicit response field paths, environment-variable authentication, timeout and request-ID header. Use a small documented field-path mapping initially, not executable expressions. Validate mappings and disallow redirects by default so credentials cannot silently follow another host. Missing optional evidence is unavailable; malformed mapped evidence is an adapter error. Polling or streaming is a later adapter extension if Odin returns jobs instead of final answers.

The in-process adapter receives a caller-supplied compiled graph and input/output mapping functions. Use `ainvoke` with documented configuration. Metadata hooks are explicit. Graph recursion limits measure supersteps, not exact tool calls or token budgets. Avoid re-invoking the graph to collect traces. The product does not import Ragnarok.

## Dependencies and compatibility

Use Python 3.11, Pydantic v2 for validation, and standard-library JSON/argparse/asyncio for the initial CLI. Add pytest as a development dependency; asynchronous tests can initially use `asyncio.run`. Add HTTPX with the HTTP adapter. FastAPI is needed only for the synthetic integration application. Keep DeepEval, LangGraph and LangSmith in separate optional dependency groups.

Preserve observed versions as initial candidates rather than blindly upgrading. Resolve and lock a dedicated environment during implementation. Check the complete dependency graph then; installed package metadata alone does not prove compatibility. Do not select a DeepEval version until its dependency requirements have been resolved against that environment.

Context7 checked DeepEval required-input documentation, LangGraph recursion semantics, and LangSmith tracing/privacy concepts. These results were not pinned to the observed LangSmith 0.4.4 release; newer examples must not be assumed supported there. Primary HTTPX, FastAPI and Pydantic documentation was consulted as well. Verify exact APIs against installed versions when each optional integration is implemented.

## Odin coverage and priorities

| Requirement | Initial deterministic evidence | Additional evaluation |
|---|---|---|
| Thor extraction, FR2/NFR2 | Clause ID exists; quote matches source; required fields and ambiguity flags | Labelled field accuracy; judge semantic support |
| Norns timeline, FR3 | Fixed simulated-clock cases; notice-window boundaries; contractual arithmetic | Worst-case scenario completeness |
| Loki/Heimdall/Tyr, FR4-7 | Observable clarification, challenge, ruling and bounded termination | Labelled conflicts; quality of rationale |
| Heimdall events, FR5 | Relevant event changes expected clause/alert; irrelevant event does not | Missed-alert and false-alert rates |
| Tyr actions, FR6 | Approval requirement recorded; unapproved action does not execute | Draft relevance and citation support |
| Reports, FR8/NFR3-6 | Per-contract coverage, cross-contract references, partial-state honesty, budget metadata | Judge usefulness and prioritization |
| Dashboard, FR9 | Later API-backed consistency checks where exposed | Product-team UI acceptance testing |

Citation existence and verbatim matching do not prove that a clause supports the conclusion. Use exact source checks plus labelled expectations or optional semantic judges. Likewise, deterministic checks cannot establish the truth of arbitrary natural-language claims.

Initial deterministic metrics: exact expected fields for synthetic cases, citation validity, missing-evidence checks, retrieval hit@k and recall@k when stable relevance labels exist. Recall@k uses unique relevant IDs retrieved in the top k divided by all labelled relevant IDs; reject empty ground-truth sets rather than inventing a score.

Start paid metrics with faithfulness and answer relevancy. DeepEval requires input and actual_output; faithfulness additionally requires retrieval_context. Contextual precision and recall additionally need expected_output and retrieval_context. Contextual relevancy is a later optional retrieval diagnostic after exact version requirements are checked. Do not substitute reference context for actual retrieval. Judge metrics add model calls, cost, latency and variance; record judge configuration and calibrate thresholds against labelled Odin examples. Reference-based retrieval checks and semantic context metrics overlap; enable only those that answer a useful question.

## Security priorities

Keep security cases and findings distinct from quality metrics. A case declares ID, category, attack/scenario, invariant, severity, evaluation method, required evidence, criteria and optional expected tool behavior.

Start with synthetic protected-secret canaries, tenant-scoped retrieval, forbidden tool execution, contract-embedded instruction injection, and approval bypass attempts. Include a deliberately vulnerable fixture and a safe fixture so checks demonstrate both failure and success. Extend with malformed inputs, repeated calls and bounded resource cases. Real denial-of-service, destructive actions and side-effecting tests are opt-in; no automatic retries.

An unauthorized retrieval check requires actual returned document scope and an independent authorization expectation. A no-execution check requires complete execution/audit evidence; final-answer refusal alone is insufficient. A missing canary proves only that the particular canary was not observed in the inspected surfaces. Record attack detection separately from invariant violation. Avoid presenting a failed attack as general security assurance.

## Runner and reporting semantics

Validate configuration/datasets, filter selected cases, execute with a case timeout and concurrency default of one, evaluate independently, and atomically write a versioned JSON report. Start with retries disabled. An evaluator exception must not discard other results. A local timeout does not prove that the remote application stopped.

Statuses: passed = observed criterion met; failed = observed criterion violated; error = execution/evaluator malfunction; skipped = disabled or required evidence unavailable; invalid = malformed case or metric configuration. Missing references produce a reasoned skipped result; wrong types produce invalid. Skips never count as passes. Report evidence coverage as well as pass rate; a suite with no executed assertions cannot succeed in CI.

Keep execution state separate from evaluation status. Reports contain run/case IDs, UTC timestamp, dataset identifier and hash, configuration fingerprint with secrets removed, all five status counts, metric reasons/scores, distinct security findings, latency summaries, and usage/cost only when known. Never total unknown usage as zero. Record package and judge versions for comparison.

Proposed exit codes: 0 = all required checks passed, 1 = any failed check, 2 = error/invalid configuration or results, 3 = no required checks executed or required evidence missing. Precedence: 2, 1, 3, 0. Optional skipped metrics do not fail an otherwise passing run.

Tracing stays disabled by default. When enabled, send allowlisted identifiers, statuses and timing, with input/output capture disabled unless deliberately configured. Never include authentication headers in reports or traces. Redact local reports too. LangSmith outages must not change deterministic evaluation outcomes. HTTP evaluator traces do not automatically include remote Odin internals.

## First milestone: an honest offline vertical slice

1. Define Pydantic configuration, case/result/evidence models and malformed-input tests; use JSON to avoid an initial YAML dependency.
2. Add dataset loading and duplicate-ID validation, then an async fixture adapter with explicit complete/partial/error results.
3. Add one deterministic exact-field evaluator for synthetic Odin extraction, with passed/failed/skipped/invalid outcomes and clear reasons.
4. Add isolated runner execution, timeouts, report aggregation and CI exit behavior.
5. Add CLI commands and a short README; verify the documented commands in a fresh project environment.

For each meaningful behavior, first run a failing test, implement the smallest solution, then rerun relevant tests. Test timeout/error isolation, absent evidence, empty datasets, disabled metrics, invalid datasets and report JSON serialization. No paid calls or live account are required.

Acceptance: a documented CLI command evaluates synthetic extraction cases offline, writes parseable versioned JSON, distinguishes a deliberate failure from missing evidence, preserves other cases after one adapter error, and returns the documented exit code. A passing-only fixture returns 0; a vulnerable/incorrect fixture returns nonzero. Pytest passes with tracing disabled and no credentials. This milestone proves the evaluator's behavior, not Odin's quality or security.

## Subsequent independently verifiable milestones

1. RAG: labelled retrieval fixtures, citation checks and optional DeepEval wrapper; missing-input validation stays offline-testable, with paid smoke tests separately marked.
2. Security: synthetic tenants/secrets/tools, safe and vulnerable cases, separate findings and evidence requirements.
3. Agent/observability: configurable trajectory checks, budget observations, optional redacted LangSmith tracing; mock instrumentation tests explicitly distinguished from live verification.
4. Integration: HTTPX adapter against a real local synthetic FastAPI app, configurable mappings, then an optional actual compiled LangGraph smoke test. Document what the future Odin API must expose.

## Open assumptions and risks

- Odin's API may expose jobs or streams rather than final synchronous results. Inspect it before finalizing transport.
- Dates require explicit timezone, business-day conventions and inclusive/exclusive notice-window rules; ambiguous contracts should flag ambiguity rather than invent a rule.
- Exposure calculations need currency, caps, compounding and overlap rules; do not sum mutually exclusive liabilities or different currencies blindly.
- Authenticated principal context must come from trusted test configuration, not model-generated tenant fields.
- Contract parsing quality and exact source locators affect citation checks; start with controlled synthetic source text.
- Optional instrumentation may be absent or incomplete. Report coverage gaps; do not infer internal agent behavior from prose.
- Reproducibility means recording inputs/configuration/versions; model-based decisions remain probabilistic.
- No actual product endpoint, graph, contracts, credentials or tenant policy has been supplied. No live integration, security result or test pass is claimed.

## Documentation sources checked

- Problem source: `C:/Users/offic/Downloads/Odin_PS.pdf`, all four pages extracted.
- Context7: `/confident-ai/deepeval`, `/langchain-ai/langgraph`, `/langchain-ai/langsmith-sdk`.
- https://deepeval.com/docs/metrics-faithfulness
- https://deepeval.com/docs/metrics-contextual-precision
- https://deepeval.com/docs/metrics-contextual-recall
- https://www.python-httpx.org/async/
- https://fastapi.tiangolo.com/advanced/async-tests/
- https://docs.pydantic.dev/latest/concepts/models/
- https://docs.langchain.com/langsmith/mask-inputs-outputs
- https://docs.langchain.com/oss/python/langgraph/GRAPH_RECURSION_LIMIT


