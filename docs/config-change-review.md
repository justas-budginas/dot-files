# Explicit config-mapping and image review

Phase A deliberately uses a **manual proposal workflow**, not a tool that edits
the allowlist or refreshes hashes. Normal sync remains live → repo only.
No force flag, recursive import, automatic prune or silent reapproval exists.

## Add a mapping: proposal first

Before editing the manifest, present these fields for approval:

```json
{
  "source": "$HOME/EXACT_APPROVED_RELATIVE_FILE",
  "destination": "home/EXACT_APPROVED_RELATIVE_FILE",
  "kind": "file",
  "format": "text",
  "mode": "0644",
  "elevated_read": false,
  "restore": "user-review",
  "reason": "Why this Arch desktop file is necessary, and dependencies/privacy review."
}
```

This is an illustrative proposal, deliberately not an accepted real mapping.
For a system source use its exact absolute path, matching `system/` destination
and `manual-only` restore policy. The main sync tool never gains sudo reads.

Review:

1. Confirm the source exists, is a regular file, has no symlink parents, fits the
   size limit and has the proposed mode; inspect all content without logging any
   suspected credential. Existing text secret/binary checks still apply.
2. Confirm it belongs to this Arch desktop—not private projects or unrelated work.
   Do not enumerate other projects to justify adding a file.
3. Inspect absolute paths and dependencies; choose user-review/manual-only
   restoration deliberately. Record a nonempty `reason` for the new entry.
4. Review the **paired diff**: exact `APPROVED_HOME`/`APPROVED_SYSTEM` scope in
   `scripts/dotfiles.py` AND the manifest mapping. A source not in that fixed
   scope must still fail. Never allow an entire directory/prefix.
5. Add sandbox regressions: duplicate destination/source, traversal, unexpected
   destination/category/mode/restore policy, secrets, symlinks and dry-run
   immutability. Run both test suites and the audit.
6. Only after path/content approval run a dry-run/diff. Request separate approval
   before applying the snapshot; inspect additions and staged content separately.

Existing mappings need not be churned to add historical reasons. Optional `reason`
fields are bounded and secret-scanned when supplied. Unknown mapping fields,
duplicate mappings and mismatched source/category/restoration policy are rejected.

## Rename/remove: preserve before pruning

A missing source is actionable, not permission to delete its repository copy.
Find the renamed source manually, preserve the old copy/history and review the
new mapping as above. Explicitly review any repo deletion. Sync has no prune mode.
Old transaction journals retain their scope; removing a mapping may block
rollback of a transaction that referenced it. Inspect/resolve that history before
removing mappings; never erase journals to silence the guard.

## Wallpaper replacement: explicit new pin, previous-copy protection

No command changes the live wallpaper or approves its hash. For a deliberate
replacement, review the new image visually, confirm redistribution provenance,
dimensions/size and metadata-free IHDR/IDAT/IEND PNG structure. A new SHA-256 alone
is not a privacy/content review.

For the **same already-approved image path**, propose a paired code diff:

- `IMAGE_HASHES[basename]` becomes the individually approved new **live-source**
  digest.
- Add the exact previously approved digest to `IMAGE_HISTORY[basename]`, a short
  reviewed list of prior **repo/index/rollback-only** pins.
- Neither list is populated from source content automatically. Historical pins
  do not authorize old/new arbitrary live source images.

Why separate pins? During a transition the committed/indexed repo copy is still
the known old PNG. Its exact historical approval lets the existing audit and
transactional sync handle that transition without a manual copy, force flag or
temporary broad image exception. Live sources still must match the current pin.
Default history is empty; unapproved PNGs are refused exactly as before.

Review the pin diff and new image **before** replacing any live asset; live
changes require their own approval and are not performed by this repository.
Once the live source is deliberately updated, preview sync, approve apply,
audit and review the image plus code changes together for staging/commit.
Keep selected historical pins if local rollback originals must remain auditable;
retiring one requires review of outstanding rollback/index references.

Gallery image replacement is separate: inspect privacy first, then review
`manifest/screenshots.json` and its exact three registered paths together with
the replacement image. Wallpaper-history pins cannot approve gallery additions.
No current-workspace capture is authorized by a hash change.

## Checks and day-to-day review

```sh
python3 -B tests/test_workflow.py
python3 -B tests/test_recovery.py
./scripts/sync-from-system --dry-run --diff
./scripts/verify-manifest
./scripts/audit-repo
git diff --check
git status --short
git diff
```

New/untracked files need explicit inspection; normal `git diff` omits them.
After separate staging approval use exact paths or `git add -p`, then inspect
`git diff --cached` and rerun the audit. Commit/push require their own approval;
check the advertised `develop` remote HEAD afterward. No command above applies
a sync, stages or pushes.
