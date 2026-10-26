"""Every quote in the internal dev-pack answer sheet must be verbatim in the cited .txt."""

import re
from pathlib import Path

import pytest

CORPUS = Path(__file__).resolve().parents[2] / "corpus"
SHEET = CORPUS / "odin_dev_pack_findings.md"
CONTRACTS = CORPUS / "odin_dev_pack" / "bundle" / "contracts"
LINE = re.compile(r'^\s*- (STD|A1|A2|A3|B1|B2|C1|D1)\b[^"]*"([^"]+)"')


@pytest.mark.skipif(not SHEET.exists(), reason="dev pack not present")
def test_answer_sheet_quotes_are_verbatim():
    quotes = [m.groups() for line in SHEET.read_text(encoding="utf-8").splitlines() if (m := LINE.match(line))]
    assert len(quotes) > 50
    texts = {doc: (CONTRACTS / f"{doc}.txt").read_text(encoding="utf-8") for doc in {d for d, _ in quotes}}
    missing = [(doc, q) for doc, q in quotes if q not in texts[doc]]
    assert not missing, missing
