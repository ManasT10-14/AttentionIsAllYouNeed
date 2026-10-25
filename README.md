# Odin contract corpus

Start with `corpus/README.md`, `corpus/INTERFACE.md`, and `corpus/demo/RUNBOOK.md`.

Version 2 follows the user-supplied authoring and email integration specification: eight contract PDFs with Key: Value covers, numeric clauses, uppercase section headings without version labels; company_context.md; copy-ready event emails; separate evaluator keys. Fictional-data labels have been removed from the PDFs and agent-visible context/events. C08 remains held back for live arrival.

## Rebuild

Use Python 3.10 or newer and `pip install -r requirements.txt` if needed. Run from this repository:

```powershell
python tools/build_corpus.py
python tools/build_cases.py
python tools/build_emails.py
python tools/validate_corpus.py
python tools/package_corpus.py
```

The document source and separately authored expected constants do not import each other. Independent human review of the keys remains pending. PDF metadata and content are deterministic; validation checks byte-identical regeneration and the exact user numbering regex. The email linter checks fixtures only and implements no Gmail client or LLM fallback.

All work is under Desktop RAGNAROK. Distribution ZIPs and START_HERE.txt are in RAGNAROK/deliverables. Prior version files are archived under ignored work/archive-v1. The authoritative problem statement was reviewed from the supplied local PDF; no source copy is published. No Git commit, push or external email has been performed.
