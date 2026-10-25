# Security and eval suite: plug-in points (nothing is built here yet)

The product is wired so that both suites attach **without any changes to the graphs**.

## Hooks: `backend/odin/core/hooks.py`
| Hook | Fires on | Use |
|---|---|---|
| `GuardHook.pre_llm / post_llm` | every LLM call (`llm/call.py`) | prompt-injection / PII / output policy |
| `GuardHook.pre_tool / post_tool` | every tool call (`tools/registry.py`) | scope checks, arg sanitising; raise `Blocked` to veto |
| `GuardHook.on_ingest` | contract + company-context upload | malicious documents |
| `GuardHook.on_email` | every event email | injection in emails (see `samples/emails/06_prompt_injection.txt`) |
| `EvalHook.record(kind, agent, inputs, output, meta)` | every LLM output (`kind="llm"`) and every retrieval (`kind="retrieval"`) | DeepEval metrics, LangSmith datasets |

Register hooks without touching any code:
`ODIN_GUARD_HOOKS=mypkg.guards:InjectionGuard` and `ODIN_EVAL_HOOKS=mypkg.evals:DeepEvalRecorder`.

## The tool surface
`GET /api/tools` lists every tool with its scope, side effects, approval requirement, PII flag and the
agents allowed to call it. Every call is audited in the `tool_calls` table, and calls that were blocked
are flagged.

## LangSmith
- Set `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY`.
- Each graph run uses the Odin `run_id` as its root run id, so `runs.trace_url` links straight to the trace.
- Each LLM call is named `<agent>:<provider>` and tagged with the agent, provider and `whatif`.
- Metadata on each call: `company_id`, `run_id`, `contract_id`, `prompt_hash`, `event_id`.

## Suggested metrics
- Citation faithfulness: the share of quotes that pass `core/citations.verify`.
- Field accuracy against goldens: build these from `samples/contracts` plus expected extraction JSON.
- Hallucinated-clause rate.
- Conflict recall on the planted cross-contract traps.
- Alert precision.
- Retrieval recall@k and MRR: `EvalHook.record(kind="retrieval")` logs the dense and sparse rankings.
