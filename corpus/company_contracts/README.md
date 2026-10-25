# Contracts by company

| Folder | Agreements |
| --- | --- |
| Aurora_Software | 15 |
| Forge_Electronics | 8 |
| Willow_Housing | 7 |

Each agreement appears in both signing companies' folders. These are byte-identical browsing copies of the 15 unique agreements in `../inputs/contracts/`; the 30 copies do not create additional agreements. `index.json` maps each copy to its canonical path, party IDs, hash and initial/arrival status.

These folders contain the full portfolio, including C08 in Aurora and Willow. For the initial demo upload, use `odin-initial-upload-v2.zip` with 14 contracts. Release C08 only at its receipt using `odin-live-arrival-v2.zip`. Do not recursively ingest this browsing directory alongside canonical inputs.

Rebuild and verify the copies with `python scripts/corpus/group_contracts.py` from the repository root.
