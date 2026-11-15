# Snapshot and documentation verification

## Scope/gate

Approved: 29 individual text sources, three deployed wallpaper images, tooling,
documentation, real local sync, inventory publication and a privacy-safe gallery.
The user separately prohibited capturing the current workspace. No stage, commit, push,
privileged changes, live-config modifications or service actions were performed.

## Current result

- PASS: all 32 approved files copied to `home/` and `system/`; bytes and modes
  match live sources. Initial transaction:
  `transaction-3a65ad0db7fb414e854ddc25cbebb86b`.
- PASS: repeated real-checkout `--apply` reports no changes; the repeat does not
  rewrite repository files or Git metadata. Read-only manifest/audit/rollback
  previews are also checked for no writes.
- PASS: approved inventories saved as four separate manifest artifacts: explicit
  native/foreign packages, enabled system/user units and selected appearance.
- PASS: README component list, shortcuts and three attractive gallery images
  added. Only existing controlled screenshots were used; no current-workspace
  capture or workspace/window changes. Images were visually inspected, framed,
  downsampled and stripped of metadata; exact hashes are registered.
- PASS: **26 sandbox tests**, including three new gallery hash/scope checks;
  tree/index audit, `git diff --check` for current tracked changes and whitespace
  checks for new tooling/docs/inventories.
- Existing source whitespace is preserved byte-for-byte: Hyprland Lua line 50
  has one pre-existing trailing space. It is not a new formatting error introduced
  by sync, but a future staged `git diff --cached --check` will report it unless a
  separately approved live-source cleanup is made. No source normalization or
  Git whitespace suppression was performed.
- Source fingerprints remain equal to the earlier read-only foundation baseline.
  Git index still contains only the pre-existing README; no stage/commit/push.
- Local current-phase evidence:
  `~/Opencode/verification/dotfiles-snapshot/`.

## Foundation checks (historical, before apply)

- Existing repository preserved: `develop`, origin SSH remote unchanged;
  original tracked content was README only.
- PASS: all **23 sandbox tests**, tree/index audit, `git diff --check`, whitespace
  checks including untracked additions, and approved destinations not ignored.
- PASS: before/after fingerprints of every checkout/Git-metadata file prove the
  dry-run, diff preview, manifest verification and audit commands made no writes.
  Approved live source bytes/ownership/modes/mtime were also unchanged.
- No actual `home/`, `system/` or `.git/dotfiles-sync/` was created. Index still
  contains only README, with no staged changes; original commit remains unchanged.
- Dry-run resolves all 32 sources and proposes 32 additions: 8,646,389 bytes at
  inspection. Text is scanned; three metadata-free PNGs match reviewed hashes.
- Inventory proposal prints 79 explicit native packages, three foreign packages,
  14 enabled system unit names, six user unit names and seven appearance keys.
  No inventory artifact is written by that command.
- Tests run in disposable `/tmp/opencode` fake homes and Git repos. Test apply,
  staging and rollback occur only in those sandboxes, never this checkout/index.

Test coverage includes:

- Read-only dry-run; exact copy/mode preservation; repeat-apply idempotency.
- Source updates, repository-only rollback and first-copy removal.
- Missing source without deletion, symlink sources/parents/destinations,
  traversal, out-of-scope sources, binary/oversized/credential content and FIFO.
- Source mode drift, repository manual edits/deletions, staged edit protection.
- Unallowlisted working files and secrets present only in the Git index.
- Rollback refusal after later edits, automatic rollback after partial atomic
  replacement, prominent double-failure reporting, interrupted-rerun refusal,
  stale-transaction protection and rejection of unreviewed images.

Additional tests verify recovery of an unfinished journal through the command's
entrypoint, corrupt-original refusal, preflight refusal of unexpected directory
content, and index-only symlink rejection.

Local supporting evidence (not part of the repository snapshot):
`~/Opencode/verification/dotfiles-foundation/{report.json,dry-run.txt,sandbox-tests.txt}`.

Repeat tests:

```sh
python3 -B tests/test_workflow.py
./scripts/sync-from-system --dry-run
./scripts/verify-manifest
./scripts/audit-repo
git diff --check
```

## Not claimed complete

- Git author identity, remote visibility confirmation, commit or remote backup.
- Full history secret audit, perfect secret detection or hostile-race resistance.
- Privileged Snapper export, firewall/network/WoL reconstruction.
- Fresh-install/bootstrap rehearsal or full-system recovery.
