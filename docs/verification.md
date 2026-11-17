# Verification history

## 2026-11-17 — SATA configuration and cleanup

- Both UUID-based ext4 startup mounts passed fstab and generated systemd-unit
  validation, effective source/type/rw checks and user access tests.
- Apacer's same-filesystem backup rename preserved the payload-root inode,
  ordinary paths/types/sizes and all modification timestamps. Named read-only
  access ACLs retained root ownership; writable ordinary storage is separate.
- Existing full SHA-256 evidence and fresh structural/access/health checks gated
  deletion of only the exact temporary NVMe backup. Control evidence was
  preserved privately outside the deletion target; snapshots were not changed.
- Stock weekly `fstrim.timer` is enabled/active and has a scheduled execution.
  Its non-writing dry run includes both SATA mounts; NVMe async discard is
  unchanged and overlaps with the packaged timer's NVMe coverage.
- **37 workflow + 11 sanitizer/privilege-boundary tests = 48 passed.**
  Three new regressions cover the exact SATA-fragment scope/policy, normal
  transactional sync with credential rejection, and symlink-parent refusal.
- Before the update, all 32 existing live-source mappings matched the checkout.
  The reviewed sync preview added only the SATA-only recovery fragment; one
  normal allowlist transaction copied that file. All 33 mappings then matched,
  with zero pending copies; existing configuration snapshots were unchanged.
- Working-tree/index scoped audit and whitespace checks passed. The exception
  publishes only approved SATA UUID/configuration and sanitized storage results,
  not raw fstab, serials, personal file paths, inventory/checksum lists or logs.

Storage details and bootstrap prerequisites: [storage.md](storage.md).
Actual reboot persistence and the first real scheduled trim remain untested.
The storage update is separately authorized for review, commit and SSH push to
`origin/develop`; no force push, authentication change or bootstrap rewrite.
The older records below retain their historical pre-publication status wording.

## 2026-11-15 — Phase A, historical local-improvement record

Baseline: local `develop` initially `8f32d82`; cached origin matched but an
authenticated strict-host-key `git ls-remote` showed GitHub at `5ff9f41`.
The user then pulled. Reinspection confirmed clean local/cached/GitHub `develop`
at `5ff9f41`; only the user's README-line removal changed. That change was
preserved, and no pull/rebase/reset/history edit was performed by this phase.
The existing snapshot is committed/present remotely; the new Phase A edits are
not staged, committed or pushed. Remote visibility remains unverified.

### Actual checks

- Baseline: all 26 original sandbox tests, verify-manifest, audit-repo,
  safe dry-run/diff and `git diff --check` passed.
- Updated suite: **34 workflow + 11 sanitizer/privilege-boundary tests = 45**,
  unprivileged in isolated fixtures. All original regressions remain included.
- New cases: duplicate/mismatched mappings, reason/category/policy validation,
  actionable missing-source guidance, non-mutating checkout-local diffs, explicit
  image reapproval with transactional update/rollback, historical-pin isolation,
  malformed pins and partial failure while updating existing copies.
- Recovery fixtures cover omitted private fields/endpoints/IDs, unknown firewall
  rows, IPv6 scope, invalid values, default/no-opt-in refusal, rejected write or
  arbitrary commands, minimal subprocess environment and diagnostic non-disclosure.
- Final audit includes current tree (also ignored/untracked files) and Git index,
  with exact new tooling/doc paths allowlisted. `manifest/configs.json` remains
  unchanged at 32 entries. No recovery file/database was added as a raw mapping.
- All 32 live source hashes/ownership/modes/mtime are compared with this phase's
  baseline; sources/copies remain unchanged. Secret scans and whitespace checks
  apply to the new code/docs; existing source formatting is preserved.
- Actual-host verification uses only dry-run/read-only commands; **no real sync
  apply or rollback apply was executed during Phase A**. Idempotency and injected
  failures are tested only in disposable repos in this phase.

The explicitly approved privileged read was performed through the system
authentication window (`pkexec`), not by collecting a password. It observed
sanitized loaded UFW policy, selected Snapper keys, the Btrfs default subvolume
and hardware WoL flags. No privileged write/service action was requested.
Those facts and limitations are in `system-recovery-inventory.md`.

New Phase A paths:

- `docs/system-recovery-inventory.md`: observed facts, confidence/provenance,
  coverage matrix and separate manual reconstruction procedures.
- `docs/service-recovery-map.md`: all 14 system/six user names categorized.
- `docs/config-change-review.md`: review-only source/remove/image procedure.
- `scripts/inspect-recovery-policy`, `scripts/recovery_policy.py`: opt-in,
  bounded privileged read/sanitization, never part of routine sync.
- `tests/test_recovery.py`: sanitizer and privilege-boundary fixture regressions.

Existing README, recovery/security/setup/roadmap docs, shared sync validation and
workflow tests are updated. Prior wallpaper pins remain unchanged; prior-image
history is empty until a future individual review. Existing Git/GitHub identity,
remote, branch and full history remain untouched.

| Modified path | Purpose |
|---|---|
| `README.md` | Verified published Git state, develop policy, review/publish workflow and recovery links |
| `docs/recovery-notes.md` | Repo-only rollback vs unimplemented fresh-machine restoration |
| `docs/security.md` | New exact artifact scope, bounded privileged reads, prior-image pin semantics and historical-audit limits |
| `docs/setup-notes.md` | Replace outdated WoL/missing-policy narrative with dated recovery references |
| `docs/bootstrap-roadmap.md` | Explicit Phase B/C stop/go gates; no prototype implemented |
| `docs/verification.md` | Separate this dated Phase A evidence from archived foundation/gallery results |
| `scripts/dotfiles.py` | Stricter mapping validation, missing-source guidance, safe prior-image pins and checkout-local diffs |
| `tests/test_workflow.py` | Eight new isolated regressions; all original 26 retained |

Evidence: `~/Opencode/verification/dotfiles-phase-a/`. Originals before edits:
`.git/dotfiles-phase-a-20261115-203233-d738319e/` with a checksum manifest.

### Boundaries and remaining gaps

No Local LLM project, model, inference service or private configuration was
enumerated or imported. No screen capture, live configuration edit, service
action, package install, snapshot operation, reboot or login/logout occurred.
The source's inherited trailing space at Hyprland Lua line 50 remains unchanged.

Not established: remote visibility; full historical-object confidentiality;
firmware/sender WoL behavior; snapshot counts/quota enforcement; complete effective
SSH policy/remote login; EFI/disk/data backups; a full-machine restore.
Phase B bootstrap implementation and Phase C recovery rehearsal have not begun.
Review is required before any staging, commit, push or public publication.

## 2026-11-15 — Archived snapshot/gallery milestone

The following evidence belongs to the earlier implementation milestone, before
the user committed/pushed it. It does not describe the current Git index/remote
or imply the running desktop was just re-tested.

### Historical scope/gate

Approved: 29 individual text sources, three deployed wallpaper images, tooling,
documentation, real local sync, inventory publication and a privacy-safe gallery.
The user separately prohibited capturing the current workspace. No stage, commit, push,
privileged changes, live-config modifications or service actions were performed.

### Historical result

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

### Earlier foundation checks (before that apply)

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

### Unverified at that historical milestone

- Git author identity, remote visibility confirmation, commit or remote backup.
- Full history secret audit, perfect secret detection or hostile-race resistance.
- Privileged Snapper export, firewall/network/WoL reconstruction.
- Fresh-install/bootstrap rehearsal or full-system recovery.

Some of those historical gaps are now covered by the Phase A observations above;
none of the historical wording is an instruction to remove published history.
