# Repository-only recovery

Nothing here deploys files back to the live system. Snapshot rollback reverses
repository copies only. It must never change the running desktop, authentication,
services or idle behavior.

## Undo the latest applied sync

```sh
cd ~/Repos/dot-files
./scripts/rollback-sync --dry-run
./scripts/rollback-sync --apply
./scripts/audit-repo
git status --short
```

The latest transaction is recorded under `.git/dotfiles-sync/state.json`.
Each unique transaction retains a journal and any overwritten repository files.
Rollback preflights original hashes/modes and accepts original or copied states;
later edits cause refusal. New copies are removed only if their state matches
the transaction. New directories are removed empty-only. Existing files restore
atomically with their original modes. No Git reset/checkout/index mutation occurs.
Do not blindly roll back after staging or committing a sync; review resulting
working/index differences yourself. Backups are local, not versioned.

Undoing updates works in reverse order; the state points back to the previous
transaction after rollback. Repeating a completed rollback is safe when explicitly
targeting that same transaction and no later state has superseded it.

## Interrupted sync / recovery

Ordinary copy or post-check exceptions attempt automatic repository rollback.
An unsuccessful rollback prints both errors and retains all recovery artifacts.
Power loss, SIGKILL, disk failure and some process termination cannot guarantee
automatic rollback. A journal blocks normal sync rather than silently proceeding.

Use the transaction basename printed in the diagnostic:

```sh
./scripts/rollback-sync --transaction transaction-HEX --dry-run
./scripts/rollback-sync --transaction transaction-HEX --apply
```

Replace `transaction-HEX` with the actual generated name. Corrupt/missing journals,
unexpected temporary files or changed manifests may require manual inspection.
Never delete broad paths or bypass the scope guards. Empty-only cleanup may stop
if another file was added to a newly created directory.

## Repository manual edits

After a sync, edit the live source for intentional configuration changes, then
review the sync dry-run. If both the repo copy and live source changed, reconcile
them manually with an editor after preserving both versions; there is no force
flag. Missing sources are errors, not deletion requests. Removing an entry/copy
requires separate human review, including any Git deletion.

## Undo this uncommitted foundation

The first local snapshot has now been applied; use the guarded rollback command
above to undo its copies. Inventory and gallery publication are independent
repository additions, not part of the live-source sync transaction.

To abandon the uncommitted foundation, inspect `git status --short`; remove only
the new files from this task, preserving any subsequent work. The sole pre-existing working file was
`README.md` containing `# dot-files` and a newline; restore that content manually
only if it has no later user edits. Do not delete/reinitialize the existing repo
or reset its branch. No live-system rollback is required.

Before README/gallery changes, foundation originals were backed up locally in:
`.git/dotfiles-readme-backup-4929739b3c434170b003ea6a5425da94/`.
That directory contains a manifest and copies of the files changed in this phase.
Compare against later work before restoring any of them; do not automatically
overwrite later edits. New inventory/gallery files can be removed individually
only after checking they still match this phase's content and are not needed.
If removing the gallery, remove its registry/images/README references together;
do not weaken the audit to tolerate unregistered binary files.

## Restoring an actual machine later

The manifest supplies source/destination mappings and manual-only classifications,
not authorization to deploy them. A fresh install needs reviewed packages,
account/home-path substitutions, original system ownership, existing-file backups,
greeter recovery access and independent disk backups. Do not run a full restore
on this working PC. See the bootstrap roadmap.
