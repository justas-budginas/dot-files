# SATA storage and recovery — 2026-11-17

Configuration/cleanup complete; an actual reboot-persistence test is pending.
This page records the explicitly approved storage configuration, not permission
to format devices, delete backups or run a broad bootstrap.

## Filesystems and startup mounts

| Drive | Filesystem / label | Filesystem UUID | Mountpoint |
|---|---|---|---|
| Crucial MX500 | ext4 / `Crucial` | `00b8c58d-1b0d-4c42-8fff-4d68933e3057` | `/mnt/Crucial` |
| Apacer AS350 | ext4 / `Apacer` | `decd9b98-b9d5-4675-ba91-6bbc14136008` | `/mnt/Apacer` |

On 2026-11-24 the Apacer label and mountpoint changed from `Games` and
`/mnt/Games` to `Apacer` and `/mnt/Apacer`. The UUID, mount options and
on-disk directory names are unchanged. Update any saved absolute paths that
still begin with `/mnt/Games`; no compatibility symlink is installed.

The reviewed recovery fragment is
[`home/.config/storage/sata-fstab.conf`](../home/.config/storage/sata-fstab.conf).
It contains only these two SATA entries, using UUIDs and:

```text
rw,noatime,nosuid,nodev,nofail,x-systemd.device-timeout=10s,x-gvfs-show
```

The final fields are `0 2` for ext4. These are ordinary startup mounts, not
click-to-mount or `x-systemd.automount` entries. `nofail` and the 10-second device
timeout keep a missing drive from blocking normal boot; they do not guarantee
that applications will find storage when a drive is absent.
There is no continuous SATA discard option.

The live `/etc/fstab` was backed up before editing. Its existing NVMe/EFI/Btrfs/
swap entries were preserved byte-for-byte. Candidate and active fstab validation,
generated mount-unit verification, actual source/UUID/type/rw checks and `neo`
access tests passed. Both systemd mount units are active.
GVfs exposes both mounted volumes to Thunar at these paths; extra bookmarks were
unnecessary. No desktop restart or reboot was performed.

The recovery fragment is a regular user-reviewed file, **not automatically
parsed by systemd or mount**. Never replace a whole fstab with this fragment.
On another installation, verify the physical identities/filesystems first,
back up that machine's fstab, create the mountpoint directories, and manually
merge only reviewed matching entries without duplicates. Then:

```sh
# Privileged, attended recovery only; no formatting:
findmnt --verify --verbose
systemctl daemon-reload
mount /mnt/Crucial
mount /mnt/Apacer
findmnt -M /mnt/Crucial -o SOURCE,TARGET,FSTYPE,OPTIONS,UUID
findmnt -M /mnt/Apacer -o SOURCE,TARGET,FSTYPE,OPTIONS,UUID
```

Validate before activation and restore the saved fstab on a failed configuration
gate. A changed UUID is a reason to investigate, never to format a replacement
device or silently substitute a kernel device name.

## Roles, layout and access

```text
/mnt/Crucial/                  primary writable restored data, neo:neo
  <original ordinary hierarchy>
  lost+found/                 root-only ext4 housekeeping

/mnt/Apacer/                   root-controlled filesystem root
  Backup/                     retained original hierarchy directly here
  Games/                      ordinary writable storage, neo:neo, 0700
  lost+found/                 root-only ext4 housekeeping
  <historical recovery-control directory retained>
```

The Apacer backup was renamed within the same ext4 filesystem from its dated
`files/` wrapper to `Backup/`; the payload-root inode did not change.
All ordinary paths, types, sizes and modification timestamps matched before/
after. Only the now-empty wrapper was removed. Nonempty historical acquisition
control artifacts were deliberately retained rather than deleted.
Private checksum/inventory paths remain relative to the payload root; private
location is now `/mnt/Apacer/Backup/`.

- Crucial root/payload ownership: `neo:neo`; original permission modes retained.
  Ordinary directories/files are 0700; root is 0755. `lost+found` stays root:root,
  0700. Owner execute bits inherited from the NTFS mapping were not normalized.
- Apacer root and `Backup/` remain root-controlled. All backup inodes were
  initially root-only, so a named POSIX ACL `user:neo:r-X` was necessary to grant
  read/traverse access throughout. Ownership remains root:root; `neo` has no
  backup file or directory write permission and cannot rename/delete `Backup/`
  through its root-owned parent. This is accidental-change protection, not an
  immutable or offline backup; root can still change it.
- Existing private access was not made world-readable, and no chmod 777 was used.
  The ACL changes permission metadata but not file contents or modification
  timestamps. ACLs are persistent ext4 metadata, not a per-mount uid/gid option.
- `neo` browsed all backup directories, read representative files, and passed
  create/read/delete tests on Crucial and `/mnt/Apacer/Games/`. Backup write-access
  checks were denied as intended.

For a future recovery, resolve the account UID/GID on that installation; do not
assume numeric IDs. Restore ownership only on the positively identified payload
filesystem, exclude `lost+found`, avoid symlink following/cross-filesystem
traversal, and review an ACL change before applying it. Do not chown all of
`/mnt`, the system home or unrelated backups.

## Integrity and temporary-copy cleanup

The preserved ordinary payload is **141,234 files**, **13,780 directories
excluding root**, **144,559,419,823 bytes**:

- Apacer destination-only SHA-256 read every copied file successfully.
- The temporary NVMe copy matched all saved Apacer digests.
- Crucial ext4 restoration matched all saved digests, paths, types, counts and
  file sizes; `lost+found` was separately accounted for. Rsync exited 0.
- The intentionally omitted 428 NTFS alternate streams remain omitted; Windows
  ACL/security metadata was not required.

These checks establish restored-content equality with the saved Apacer baseline,
not independently established equality with every original pre-acquisition NTFS
byte. Formatting did not cure or erase the Crucial's earlier health history.
Monitor future hardware/read errors and maintain independent protection.

Before deleting the temporary NVMe directory, fresh non-content structural,
access, mount and hardware-health gates passed for both SATA copies.
No unnecessary full 145-GB source reread was done.
The exact dated temporary backup under `$HOME/Backups/` was removed only after
canonical path, Btrfs `@home`, no-symlink/no-submount and unrelated-content checks.
Its trusted control manifests/reports were preserved privately outside it.
The parent `Backups/` and all existing snapshots were retained.
Measured available-space recovery was approximately **127.8 GiB**; available NVMe
space after cleanup was approximately **441.9 GiB**. Physical Btrfs recovery
differs from apparent content size because of compression, allocation and metadata.

Only Crucial and Apacer are the intended long-term redundant copies now.
**Both are inside the same computer: this is not off-site, offline or disaster
protection.** Private file inventories, digests, paths and operational logs are
intentionally absent from this repository. Do not delete the retained Apacer
backup without separate approval.

## Periodic SSD maintenance

The existing stock **`fstrim.timer` is enabled and active**, with weekly,
persistent scheduling and packaged randomization. Both SATA drives advertise
discard capability. A non-writing `fstrim --dry-run` included both mounted ext4
filesystems. No manual large trim, `blkdiscard` or layout change was performed.

The packaged service uses `/etc/fstab` and mount information, so it covers the
mounted SATA filesystems. It also includes NVMe, whose existing Btrfs
`discard=async` is unchanged: weekly trim overlaps with asynchronous discard.
That is potentially redundant maintenance, not justification for changing Btrfs
mount policy here. A dry run checks selection, not actual hardware trim success.
Inspect the first real timer/service result later.

Recovery prerequisites: `util-linux`, `e2fsprogs`, `acl`, `systemd`, `udisks2`,
`gvfs`, Thunar and the existing Polkit agent. No new package was installed.
After deliberate recovery approval and capability/mount review:

```sh
systemctl enable --now fstrim.timer
systemctl is-enabled fstrim.timer
systemctl list-timers fstrim.timer
```

Do not bulk-enable the service inventory or automatically change Snapper,
partitions, desktop/session services or other mounts.

## Remaining checks

After the user's next normal reboot, confirm both UUIDs at the expected
mountpoints, `neo` access, Thunar visibility and timer scheduling. No automatic
reboot/logout is part of this work. Off-host backup and any later permission
normalization remain separate decisions; Phase B/C bootstrap work is unchanged.
