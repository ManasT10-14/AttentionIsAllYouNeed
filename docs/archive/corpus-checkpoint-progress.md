# Corpus checkpoint ledger

Plan: docs/superpowers/plans/2026-10-25-corpus-checkpoint.md

Previous turn: progress — produced verified backend hooks and evaluator. Current
goal starts by verifying current filesystem/remotes rather than trusting history.

Canonical repository is now this directory (Desktop/Ragnarok/backend). Copied
the original evaluator into the repository so a teammate's clone is complete.
Product hooks/evaluator committed as 3ee3351 before merging corpus history.
Remote corpus advanced from 7b22fdb to 0fda74d. Common ancestor 0e14da0 confirmed.
Local branch is corpus as requested by the corpus repository instructions.
README/.gitignore add/add conflicts resolved by retaining backend instructions,
linking corpus, and combining ignore rules. Updated root workspace .env copied
to canonical repository .env; secrets were not printed or staged.

Scope is full checkpoint integration and real testing. Golden-quality failures
are reportable results, not a reason to weaken assertions or claim fake success.

## Repository cleanup - 2026-10-25

Promoted the Git root to Desktop/Ragnarok; backend/ now directly contains odin/,
tests/ and its Dockerfile. No backend/backend nesting remains. Old duplicate
workspace files and both previous virtual environments were archived outside
the repository at Ragnarok-cleanup-backup-20261025-180927. A fresh virtual
environment was created at the new root. Environment copies matched before
promotion and the private environment remains ignored. Completed the two
previously interrupted regressions without running new live model tests.

Cleanup verification: 164 offline tests passed in the rebuilt environment; lint
and formatting passed; corpus hashes/citations and original golden validator
passed; wheel/source distribution built and 148 installed packages are
compatible. Credential scan found no key literals in deliverables. Private .env,
reports, work and virtual environments are ignored. Remote corpus is an ancestor
of this branch, with no remote commits missing from the checkpoint.
