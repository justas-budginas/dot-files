# Future bootstrap: design only

Phase A completes backup/documentation hardening only. Phase B implementation and
Phase C disposable-system recovery rehearsal each require separate approval.
No bootstrap prototype, VM restore or live restore was started during Phase A.
Use `system-recovery-inventory.md` and `service-recovery-map.md` as observations
and prerequisites, not machine-executable desired state.

No install/restore/apply module is implemented or tested on a fresh system.
The manifest already records individual destination paths, modes and restoration
policy so a future preview can explain each proposed action.

Implement and test independently, first in a disposable Arch VM:

1. **Preflight:** correct host/user, Arch base, network, mount layout, free space,
   recovery access and independent backups. Resolve account UID/GID dynamically.
2. **Packages:** separately reviewed native/foreign lists; install missing items
    only. Review AUR build scripts, do not blindly upgrade or install LLM tools.
    Set up the [Serein package source](#serein-package-source) before processing
    the native package list.
3. **User config:** preview mapping from `home/` to chosen home, back up existing
   files, preserve approved modes; explicitly review hardcoded account paths.
4. **Appearance/assets:** install theme/font packages, approved images and
   individually reviewed GSettings keys; verify outputs/hardware.
5. **System config:** preview each manual-only `system/` mapping. Use narrow,
   separately approved privileged transactions; never mass-copy `/etc`.
   Preserve PAM/keyring/account semantics and recoverable greeter access.
6. **Services:** interpret reviewed unit names/templates/aliases; distinguish
    enable from start, skip absent units and request approval for both.
    The [Kingston RAM RGB oneshot](kingston-ram-rgb.md) is hardware-specific:
    verify the exact controller before installing, testing and enabling it.
7. **Verification:** compositor parsing/errors, bar helpers, lock/unlock,
   output-specific forms, wallpaper/startup, portal/audio/notifications, SSH and
    firewall access. Report observed versus user-confirmed results.

The completed SATA storage work adds manual recovery prerequisites, not a
bootstrap implementation: follow [storage.md](storage.md) to re-identify drives,
review the SATA-only fstab fragment, preserve existing root/EFI/Btrfs/swap
configuration, validate mounts/access/ACL protection, and deliberately enable
the packaged weekly `fstrim.timer`. Never infer permission to format or delete
personal data from a matching label, UUID or service-inventory entry.

Must be idempotent: dry-run first, compare state, avoid rewriting matching files,
back up every replacement, stop on ambiguous edits and verify before disruption.
No automatic greeter restart, logout, reboot or irreversible operations.

Never automate partitioning, formatting, disk restoration, secrets import,
key generation/import or authentication changes. GRUB/EFI, filesystem mounts,
Snapper policy and firewall/network reconstruction require separate safeguards.

This repository is not an independent full-system backup. Not backed up: personal
data, app state, secrets, EFI, bootloader installation, SATA disks, system snapshots,
root-only Snapper policy, network connection state or the Local LLM project.

## Serein package source

Serein is part of the desktop package list. It is installed through pacman from
the upstream `serein` nightly repository, not from the official Arch repositories
or the AUR. On a fresh install, follow the
[upstream Arch instructions](https://github.com/viceverse-cz/Serein) to review the
repository and verify and trust its signing key. Configure the repository with
signature verification required before installing `serein` from the native list.
If the repository or its signatures cannot be verified, stop and report the
missing prerequisite rather than weakening pacman's signature policy.
