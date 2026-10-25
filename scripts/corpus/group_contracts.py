"""Build company browsing copies from the canonical fifteen-contract manifest."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / 'corpus'
OUT = ROOT / 'company_contracts'
COMPANIES = {'P01': 'Aurora_Software', 'P02': 'Forge_Electronics', 'P03': 'Willow_Housing'}


def build():
    manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
    contracts = manifest['contracts']
    assert len(contracts) == 15 and len({c['contract_id'] for c in contracts}) == 15
    index = {}
    for party_id, folder in COMPANIES.items():
        directory = OUT / folder
        directory.mkdir(parents=True, exist_ok=True)
        selected = [c for c in contracts if party_id in c['party_ids']]
        expected_names = {Path(c['file']).name for c in selected}
        existing = {p.name for p in directory.glob('*.pdf')}
        assert existing <= expected_names, f'Unexpected PDFs in {directory}: {existing - expected_names}'
        for contract in selected:
            data = (ROOT / contract['file']).read_bytes()
            assert hashlib.sha256(data).hexdigest() == contract['sha256']
            destination = directory / Path(contract['file']).name
            destination.write_bytes(data)
            assert destination.read_bytes() == data
        index[party_id] = dict(folder=folder, contracts=selected)
        assert {p.name for p in directory.glob('*.pdf')} == expected_names
    assert [len(index[party]['contracts']) for party in COMPANIES] == [15, 8, 7]
    (OUT / 'index.json').write_text(json.dumps(dict(
        purpose='Full-portfolio company browsing copies; use canonical manifest paths for ingestion.',
        unique_contracts=15, pdf_copies=30, companies=index,
        visibility='C08 remains held back until its receipt. These full-portfolio folders are not initial-upload packages.'
    ), indent=2) + '\n', encoding='utf-8')
    (OUT / 'README.md').write_text(
        '# Contracts by company\n\n'
        '| Folder | Agreements |\n| --- | --- |\n'
        '| Aurora_Software | 15 |\n| Forge_Electronics | 8 |\n| Willow_Housing | 7 |\n\n'
        'Each agreement appears in both signing companies\' folders. These are byte-identical '
        'browsing copies of the 15 unique agreements in `../inputs/contracts/`; '
        'the 30 copies do not create additional agreements. `index.json` maps each copy '
        'to its canonical path, party IDs, hash and initial/arrival status.\n\n'
        'These folders contain the full portfolio, including C08 in Aurora and Willow. '
        'For the initial demo upload, use `odin-initial-upload-v2.zip` with 14 contracts. '
        'Release C08 only at its receipt using `odin-live-arrival-v2.zip`. '
        'Do not recursively ingest this browsing directory alongside canonical inputs.\n\n'
        'Rebuild and verify the copies with `python scripts/corpus/group_contracts.py` from the repository root.\n',
        encoding='utf-8')
    print('Company folders verified: Aurora 15, Forge 8, Willow 7; 15 unique agreements, 30 identical copies.')


if __name__ == '__main__':
    build()
