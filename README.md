# Odin contract corpus

The active corpus has 15 contracts across Aurora Software, Forge Electronics and Willow Housing. It includes different drafting forms, commercial tables, distinct effective dates, contractual consequences, timeline conflicts, 64 scenarios and 94 email fixtures. Start with `corpus/README.md` and `corpus/demo/RUNBOOK.md`.

## Rebuild

Use Python 3.10 or newer with `pip install -r requirements.txt` if needed:

```powershell
python tools/build_corpus.py
python tools/build_cases.py
python tools/build_emails.py
python tools/validate_corpus.py
python tools/build_golden.py
python tools/validate_golden.py
python tools/group_contracts.py
python tools/package_corpus.py
```

`tools/contracts.py` and `extra_contracts.py` author the documents. `build_cases.py` and `extra_cases.py` separately author observations and expected constants; neither case module imports the document source. The strict email linter validates fixtures and implements no Gmail client or LLM fallback. Independent human review of the keys is pending.

The evaluator-only [golden dataset](corpus/oracle/golden/README.md) defines inputs and expected outputs for Odin, Thor, Norns, Loki, Heimdall and Tyr. It includes 384 agent/scenario vectors, 15 contract extraction records, 36 worked examples and a complete payment pipeline example. The standalone package is `odin-agent-golden-dataset.zip`; agents must never receive its answer keys.

Use `agent_goldens.jsonl` in RAGNAROK/deliverables for all 384 records in one file. Per-agent and companion JSONL exports are in the golden package; each line is a complete JSON object. JSONL exports are checked against their source records during validation.

Validation checks all clauses and table rows against final pages, exact ingestion metadata, distinct forms and effective dates, event/party references, visibility boundaries, selected independent date/decimal arithmetic, and deterministic PDF generation. It does not execute Odin agents. All work stays under Desktop RAGNAROK. Packages, START_HERE.txt and portfolio-preview.png are in RAGNAROK/deliverables. Scratch scripts and the private problem statement stay under ignored work/.

Company folders are under `corpus/company_contracts/`: `Aurora_Software` (15 agreements), `Forge_Electronics` (8) and `Willow_Housing` (7). A shared agreement appears in both signing companies' folders; these are identical copies of 15 unique contracts. Use the canonical inputs and staged upload packages for ingestion; the company folders contain the full portfolio including held-back C08.

The working branch is `corpus`. Historical HANDOFF.md plans are superseded by the current user requirement of 15 contracts and three companies.
