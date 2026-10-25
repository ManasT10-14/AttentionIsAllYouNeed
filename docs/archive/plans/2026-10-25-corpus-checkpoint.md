# Corpus evaluation checkpoint implementation plan

Goal: merge current corpus and evaluation code into one cloneable repository,
load the supplied reference material safely, execute real evaluation and tracing,
and leave a verified checkpoint the user can push for teammates.

Architecture: repository root owns src/ragnarok, configs, tests and uv.lock;
backend/odin is the product; corpus/inputs is agent-visible source material;
corpus/oracle is evaluator-only. A trusted release loader obeys received_at and
scenario contract selections. Expected answers never enter product execution.
Keep authored exact assertions separate from semantic rubrics and infrastructure
checks. Record uncovered mappings as unsupported rather than inventing passes.

Tech: Python 3.11, existing Odin/LangGraph, DeepEval, LangSmith, PostgreSQL/SQLite.
Source: origin/corpus 0fda74d, 15 PDFs, 64 scenarios, 384 vectors, 114 typed fields,
276 citations. These are authored goldens, not independently reviewed truth.

Tasks (test-first implementation, inline execution):
- [x] Package existing evaluator in repository; merge corpus preserving backend.
- [ ] Validate corpus hashes, PDF citations, schema and input/oracle boundary.
- [ ] Implement corpus loaders/compiler, typed assertions/rubrics and release replay.
- [ ] Connect and execute RAG/agent/security goldens; trace actual runs and scores.
- [ ] Add clean-clone setup/CI/handoff, run full checks and independent review.
- [ ] Commit verified checkpoint, audit tracked secrets and document push readiness.

Review focus: future C08/events must remain hidden until release; no goldens in
prompts; oracle logical fields require explicit mapping from actual backend data;
money uses Decimal strings; partial work and missing mappings stay visible;
provider/judge errors must not become passes; no email/notice execution; trace
warnings and actual uploaded feedback are verified separately.
