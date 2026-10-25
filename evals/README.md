# Evaluation checkpoint

The complete evaluator is in this repository under `src/ragnarok`. Work from the
repository root, with `uv sync --locked --all-extras`. No parent workspace is
required. See [the teammate checkpoint guide](../docs/CHECKPOINT.md),
[measured results](../docs/CHECKPOINT_RESULTS.md), and
[metric definitions](../docs/metrics.md).

Use `ragnarok corpus-build` to compile source goldens. Ordinary tests are offline;
`configs/corpus.*.json` explicitly enable live product calls, judges and tracing.
Oracle files remain evaluator-only.
