# Metric and security reference

All thresholds are test configuration, not universal quality standards. Deterministic security assertions require a score of 1 regardless of a lowered threshold. No metric proves a product is generally secure.

Exact output and tool-argument comparisons preserve JSON value types recursively. Boolean true differs from numeric 1, and integer 1 differs from decimal 1.0. Use a custom semantic/numeric evaluator if those representations should be equivalent in your domain. Canary checks inspect raw strings and object keys so JSON quote, backslash or newline escaping cannot conceal a literal match.

## DeepEval 4.3.1

| Name | Meaning | Required observed/labelled inputs |
|---|---|---|
| faithfulness | Whether answer claims are supported by retrieved text | Text input, actual answer, complete nonempty actual retrieval |
| answer_relevancy | Whether the answer addresses the question | Text input and actual answer |
| contextual_relevancy | Whether retrieved text relates to the input | Text input and complete nonempty actual retrieval |
| contextual_precision | Whether useful retrieval appears ahead of less useful retrieval | Text input, reference answer, complete nonempty actual retrieval |
| contextual_recall | Whether retrieval covers the reference answer | Text input, reference answer, complete nonempty actual retrieval |

All five use an LLM judge and return scores between 0 and 1. They add provider cost, latency and variability; a high score is an estimate based on the supplied evidence. Context precision/recall/relevancy do not require an actual answer in the pinned library; faithfulness and answer relevancy do. The integration validates these requirements before constructing a provider. Missing inputs are skipped, unsupported metric params are invalid, provider/parse/timeout problems are errors. Reference context never replaces actual retrieval.

These metrics overlap: faithfulness checks support, answer relevancy checks responsiveness, and context metrics diagnose retrieval. Start with faithfulness and answer relevancy, then add retrieval diagnostics when you have reliable references. Exact labelled retrieval metrics can be cheaper and more reproducible than judge-based retrieval metrics.

API inputs were checked through Context7 and inspected against installed metric `_required_params` and constructors. Actual classes are constructed in offline tests with a custom no-network model. Tests using fake scores verify orchestration, not semantic judge reliability. Live provider behavior remains unverified.

## Deterministic checks

| Name | Params | Interpretation and limits |
|---|---|---|
| exact_match | None | Compares actual/expected JSON values; does not judge semantic paraphrases |
| recall_at_k | k (default 5) | Unique relevant IDs among first k records / all labelled relevant IDs |
| hit_at_k | k (default 5) | 1 if any labelled relevant ID appears in first k records, otherwise 0 |
| citations | None | Every exposed citation must match trusted document/clause text; at least one required; does not establish semantic support |
| expected_tools | tools: list | Required tool names must appear in attempted/executed/failed activity; pair with tool_errors to require successful execution |
| tool_arguments | expected: name-to-object mapping | Exact argument-object comparison; requires at least one activity for each expected tool |
| tool_errors | None | Fails on a recorded failed tool/error; historical recovered failures still fail this check |
| event_sequence | sequence: event kinds | Expected ordered subsequence, allowing intervening events; not a full workflow verifier |
| max_tool_calls | max: positive integer | Counts active tool records; detects observed excessive activity, does not enforce runtime limits |
| max_events | max: positive integer | Counts recorded workflow events; a proxy for repetition, not proof of a graph cycle |
| latency | max: milliseconds | Adapter wall-clock time only, excluding judges/tracing |
| max_tokens | max: tokens | Input + output product tokens; skips if either is unknown |
| max_cost | max: amount, currency | Compares exposed product cost only when currency matches; no exchange-rate conversion |
| no_secret | canaries: nonempty string list | Case-insensitive literal canary search across exposed execution; detects configured strings, not encoding or arbitrary secret leakage |
| tenant_isolation | allowed_tenant_ids: nonempty string list | Document scope labels must be allowed; depends on trustworthy labels and audit coverage |
| forbidden_tools | forbidden: nonempty string list | No listed tool may be attempted/executed/failed; a requested call alone is not execution |
| authorized_tools | None | Every active tool record must have authorized=true |
| approval_required | tools: nonempty string list | Monitored active tool records must have approved=true |
| http_status | allowed: nonempty integer list | Compares observed HTTP response code; useful for malformed-input or unauthorized-request rejection |

Missing labels or evidence produce skipped, not zero/passed. Negative claims require complete evidence. An observed tenant violation, forbidden activity, invalid citation or excessive count fails even with partial evidence. No-secret passing is scoped only to exposed surfaces; absent internal logs do not prove internal secrecy.

## Synthetic security coverage

Odin integration adds `mrr_at_k` (first relevant clause's reciprocal rank within
`params.k`), `json_fields` (`params.expected` maps dotted output paths to exact
typed JSON values), `insufficient_evidence` (explicit product refusal flag), and
`tool_denied` (`params.tools`, optionally `params.error_types`, require explicit
terminal denial decisions with no function execution). Missing decision evidence
skips; naming an unrequested tool fails. Security checks require score 1 even when
a lower threshold is configured.

The fixture pack covers direct prompt injection, contract-embedded instruction injection, tenant leakage, synthetic secret disclosure, approval bypass, tool activity limits and malformed-input rejection. It includes a known vulnerable response set so the security checks demonstrate failures.

It does not provide exhaustive jailbreak/unsafe-content assessment, real DoS testing, network attack tooling, production ACL verification or independent runtime enforcement. Attack detection is not measured by these checks: they measure declared outcome invariants. Product-specific allowed principals, tool policies, event types and relevant-document labels must come from the actual backend's threat model.
