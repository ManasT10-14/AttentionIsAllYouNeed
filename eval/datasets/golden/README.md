# Custom dataset templates

Current corpus goldens are compiled with `ragnarok corpus-build` into
`eval/datasets/corpus/`. See `docs/CHECKPOINT.md` for the active workflow.
This folder retains the generic schema and earlier authoring notes for additional
team datasets; the awaiting-upload notes below describe the earlier template stage.

# Golden datasets (awaiting upload)

No golden answers or model-accuracy scores are invented here. Supply `rag.json`,
`retrieval.json`, `agent.json` and optionally `security.json` using the generated
`dataset.schema.json`. Set `synthetic: false` on real reference datasets.

Each case needs `id`, `kind`, `input`, and `checks`. RAG input is the question
string; `expected_output` is the reviewed reference answer. Retrieval relevance
labels use `expected_relevant_document_ids` with IDs `CONTRACT:vVERSION:CLAUSE`,
for example `LEASE-1:v2:1.2`. Trusted source clauses belong in `reference_context`
with that same ID, full `text`, `tenant_id` and `clause_id` (printed number).
Never put expected output into the question or target parameters.

Use `metadata.odin_parameters` for per-case contract filters or graph targets.
The trusted company scope is fixed in configuration and cannot be overridden by
cases. RAG may set `contract_ids`; retrieval also accepts `clause_types`, `top_k`
and `current_only`; analysis accepts `contract_ids` and `force`. Event requires
`event_id`; update requires `contract_id`, `from_version`, `to_version`.

RAG checks: `faithfulness`, `answer_relevancy`, `contextual_relevancy`,
`contextual_precision`, `contextual_recall`, `citations`, `insufficient_evidence`.
Only use refusal checks on cases that should refuse. Citation checks test literal
quotes against trusted sources; faithfulness tests semantic grounding separately.

Retrieval checks: `recall_at_k`, `hit_at_k`, `mrr_at_k`, and `tenant_isolation`.
Agent checks: `expected_tools`, `tool_arguments`, `tool_errors`, `event_sequence`,
`max_tool_calls`, `max_events`, and `json_fields`. Graph output includes
`artifacts.extraction`, `.finding`, `.verification`, `.ruling`, `.action`, `.alert`,
`.violation` and `.report` lists for that unique run. `json_fields.params.expected`
maps dotted paths (including list indexes) to exact typed expected values.

Security cases must declare their invariant, severity and required evidence.
Use `tool_denied` with explicit `error_types` to prove the intended product gate
was exercised rather than merely the evaluation sandbox. An attack corpus must
include injection-bearing contracts/emails in the disposable target database;
queries alone cannot test indirect document injection.

Run `uv run --all-extras ragnarok validate eval/datasets/golden/rag.json` before live
execution. Configs deliberately reference missing golden files until supplied.
