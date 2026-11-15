# Two different kinds of recovery

## A. `rollback-sync`: repository copies only

This command reverses a previous live → repository sync. It **never** restores a
live configuration, changes services or reverts a running desktop. It also does
not revert Git commits, stage files or restore a full machine.

Preview only:

```sh
cd ~/Repos/dot-files
./scripts/rollback-sync --dry-run
```

Only after reviewing the exact proposed repository changes and obtaining approval:

```sh
./scripts/rollback-sync --apply
./scripts/audit-repo
git status --short
```

The latest transaction is recorded in `.git/dotfiles-sync/state.json`; unique
transaction directories retain journals and overwritten repo originals.
All targets are preflighted against their exact original/copied hashes and modes.
Later edits, unexpected directory content, missing/corrupt originals and stale
transactions cause refusal. Existing files restore atomically; newly introduced
copies are removed only if their current state matches. Directories are removed
empty-only. The previous state is restored, permitting reverse-order recovery.

**Published snapshot warning:** a historical transaction may have introduced
files that are now tracked/committed. Its rollback can propose working-tree
deletions of those snapshots; it does not remove their Git history. Never execute
it merely to undo a README edit or uninstall the desktop. Inventory/gallery/doc
changes are independent of a configuration-copy transaction.

No collision/force override exists. There is no automatic prune. The transaction
backup is local `.git` metadata, not an independent backup and not transported by
a clone. Removing/changing manifest mappings may block old recovery scope; review
that relationship before deleting mappings or history.

### Interrupted transactions

Normal copy/post-check exceptions attempt automatic repo-only rollback. Original
and rollback errors are separately reported if both fail. SIGKILL, power loss,
filesystem failure or some process termination may prevent automatic recovery.
Unfinished journals block blind reruns.

Use the **actual** transaction basename from the diagnostic:

```sh
./scripts/rollback-sync --transaction transaction-HEX --dry-run
```

After separate approval, use the same arguments with `--apply`. Corrupt/missing
journals, unexpected files, changed mappings or ambiguous content require manual
inspection. Never delete journals or broad paths to defeat a refusal.

### Undoing the Phase A repo edits

Phase A began from clean `develop` at `5ff9f41` after the user pulled GitHub's
branch. Unrelated/user changes and the full history are preserved. These edits
are not a configuration-sync transaction and must not be undone with rollback-sync.

Review `git status --short` and file-by-file diffs against that baseline. An
ignored, repository-local copy of the original tooling/docs/manifests is under
`.git/dotfiles-phase-a-20261115-203233-d738319e/`, with a checksum manifest.
Compare originals and any later work before individually restoring a file.
Remove only this phase's new files after reviewing their current content.
Do not reset the branch, discard later edits, delete the repo or restore an
ancient README-only foundation. No live-system rollback is needed.

## B. Fresh-machine restoration: NOT implemented

The existing snapshot is committed and present on GitHub; **that does not make it
a tested installer or disaster-recovery image**. Phase A improves configuration
references, not deployment. Phases B/C require their own approvals.

Start future recovery from the selected `develop` revision and independently
verified backups. Read [the sanitized inventory](system-recovery-inventory.md)
and [service prerequisites](service-recovery-map.md) before deciding any action.

Manual prerequisites include:

- Independent personal-data/EFI/disk backups and securely stored keys/secrets.
- Correct Arch base, account/home, dynamically resolved UID/GID and mount layout.
- Explicit review of output names, GPU path, home paths and greeter GDK index.
- Private reconstruction of LAN CIDR/NIC identity; local TTY and firewall/SSH
  lockout prevention. Never import network connection profiles or secrets.
- Snapper retention, Btrfs root/default-subvolume and GRUB/overlay semantics.
  Root snapshots exclude separately mounted home/log/swap subvolumes.
- Backups and validation before each approved system-file replacement; no bulk
  `/etc` copy, auto service enable/start or automatic greetd restart.

There is no permission here to restore this working PC, change bootloader/EFI,
partition/format disks, import authentication material or roll back snapshots.
See the design-only [bootstrap roadmap](bootstrap-roadmap.md).
