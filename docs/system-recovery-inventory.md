# Sanitized system recovery inventory — Phase A

**Observed: 2026-11-15.** This is a configuration reference, not a restore script
or evidence of a completed recovery. Original live files and services were not
changed. The existing 32-entry copy manifest is unchanged.

## Coverage matrix

| Area | Captured now | Manual / machine-specific / missing |
|---|---|---|
| Crimson desktop | 32 exact allowlisted configs/helpers/images | Output names, GPU PCI path, account paths require review on another host |
| UFW | Loaded defaults, sanitized SSH rule scope, IPv4/IPv6 policy | Actual private LAN CIDR deliberately excluded; raw rule databases never copied |
| Snapper | Root policy, cleanup/retention settings, effective timer policy | Snapshot data/counts, quota/qgroup state, restore rehearsal not captured |
| Btrfs | Verified system mount/subvolume relationships; top-level default | UUIDs, devices, subvolume IDs, partition map, data and disk images excluded |
| Boot/EFI | UEFI, `/efi`, GRUB preferences/parameters, initramfs hooks, snapshot overlay | EFI files/entries, bootloader installation and disk identifiers excluded |
| Swap/zram | Two active approximately 16-GiB swap areas; priorities | Swapfile physical properties and hibernation prerequisites not fully inspected |
| Wake-on-LAN | Active Ethernet profile persists magic packets; hardware currently `g` | NIC MAC, interface/profile identities, BIOS settings and Debian sender state excluded/unverified |
| SSH/access | Selected daemon policy and relationship to LAN-only firewall rule | Effective full sshd config, host/client keys, authorized_keys and remote access test excluded/deferred |
| Services | Existing inventory categorized with package prerequisites | No bulk enablement; sockets/templates/targets need deliberate interpretation |

## Observation provenance and confidence

Unprivileged inspection used selected readable config fields; mountpoint-specific
`findmnt` queries requesting only TARGET/FSTYPE/OPTIONS; `/proc/cmdline` and
`/proc/swaps` parsed in memory; selected unit queries; and exact package queries.
Source addresses, UUIDs, device identifiers and arbitrary kernel parameters were
never exported into this repository.

WoL persistence was identified by querying **only**
`802-3-ethernet.wake-on-lan` on the active Ethernet connection. Its connection
identity was used transiently to address the query, not logged/exported. No
NetworkManager connection file or secret field was read.

After explicit user approval, the system authentication dialog (`pkexec`) ran
`scripts/inspect-recovery-policy --privileged-read-only`. It read selected Snapper
keys and ran these bounded queries: `ufw status verbose`,
`btrfs subvolume get-default /`, Ethernet DEVICE/TYPE selection and ethtool for
those ports. Only sanitized parsed results were printed. No privileged writes
were performed. The initial `sudo -n` attempt failed before inspection.

Thus loaded firewall state, Snapper values, default subvolume and hardware WoL
are **directly observed**, not inferred from package installation. Firmware WoL,
actual off-host wake, recovery and authentication were not retested.

| Observation | Selective source/query |
|---|---|
| Loaded UFW, Snapper policy, Btrfs default, ethtool flags | Approved bounded inspector; parsers in `scripts/recovery_policy.py` |
| Configured UFW defaults | Selected keys in `/etc/default/ufw` and `/etc/ufw/ufw.conf`; raw rules parsed only in memory |
| Mount relationships/options | `findmnt --json --mountpoint MOUNTPOINT --output TARGET,FSTYPE,OPTIONS` for the exact mountpoints below; numeric IDs filtered out |
| Kernel/GRUB/initramfs | Selected tokens/keys from `/proc/cmdline`, `/etc/default/grub`, `/etc/mkinitcpio.conf`, `/etc/default/grub-btrfs/config` |
| Swap kinds/sizes/priorities | `/proc/swaps` parsed in memory, paths/identities omitted |
| Timer/watch integration | `systemctl cat` on the two Snapper timers and grub-btrfsd; selected active/enabled properties via `systemctl show` |
| snap-pac integration | `pacman -Q` on named recovery packages; hook file presence via `pacman -Ql snap-pac` |
| Persisted WoL | One `nmcli -g 802-3-ethernet.wake-on-lan connection show uuid` query on the active Ethernet connection; identity withheld |

Re-running a source query is not permission to save its raw stdout. Review and
sanitize any proposed documentation update first; ordinary sync never refreshes
these observations.

## UFW: observed state

- Enabled and active; low logging; IPv6 support enabled.
- Configured default input DROP, output ACCEPT, forwarding DROP.
- Loaded UFW defaults: deny incoming, allow outgoing, routed disabled.
- One reviewed user rule: allow inbound IPv4 TCP/22 from a restricted RFC1918
  private LAN subnet. Its literal address/prefix is intentionally not recorded.
- No additional user rule rows were reported; no IPv6 SSH allow rule appeared.
- This does not imply UFW's standard ICMP/DHCP/before/after handling is absent.
  Packaged rules and kernel behavior must be reviewed during reconstruction.

`system/etc/ufw/ufw.conf` alone is **not** a backup of this policy. Raw user.rules,
before/after databases and endpoint lists remain excluded.

### Future reconstruction procedure — NOT executed

Use a local TTY/out-of-band console, not the only working SSH connection.
Install UFW and OpenSSH, choose the correct private LAN CIDR locally, validate the
SSH listening port/authentication policy, then deliberately reconstruct the
default deny-in/allow-out policy and a TCP/22 allow restricted to that LAN.
Review IPv6 and routing separately; do not accidentally add an unrestricted
`allow ssh` rule. Check normal/verbose UFW status and a second attended access
test before relying on remote administration. Enabling/reloading UFW requires
new approval and is not part of this phase.

## Snapper: root policy observed through the bounded probe

Root target `/`, filesystem `btrfs`:

| Setting | Observed value |
|---|---|
| Number cleanup | enabled |
| Number minimum age | 3600 seconds |
| Number limit / important limit | 10 / 3 |
| Timeline creation / cleanup | enabled / enabled |
| Timeline minimum age | 3600 seconds |
| Hourly / daily retention | 0 / 7 |
| Weekly / monthly / yearly retention | 0 / 0 / 0 |
| Empty pre/post cleanup / minimum age | enabled / 3600 seconds |
| SPACE_LIMIT / FREE_LIMIT | 0.5 / 0.2 |

These are policy settings, **not** claims about current snapshot counts or
guaranteed storage enforcement. Quota/qgroup state has not been inspected.
Account/ACL fields and the raw root-only config were not exported.

Both cleanup/timeline timers are enabled and active:

- Effective timeline override resets the packaged hourly calendar and replaces
  it with **daily**, persistent scheduling.
- Cleanup timer: OnBootSec=10m, OnUnitActiveSec=1h.
- `snap-pac` is installed and its pre/removal/post libalpm hook files exist.
  No package transaction or snapshot creation was triggered.

## Btrfs mount design: verified selected mountpoints

| Mountpoint | Filesystem | Subvolume |
|---|---|---|
| `/` | Btrfs | `@` |
| `/home` | Btrfs | `@home` |
| `/var/log` | Btrfs | `@log` |
| `/.snapshots` | Btrfs | `@snapshots` |
| `/swap` | Btrfs | `@swap` |
| `/efi` | VFAT | not applicable |

Btrfs options observed on those mounts: rw, noatime, compress=zstd:3, ssd,
discard=async, space_cache=v2. Subvolume numeric IDs are omitted. No separate
`/var/cache`, `/boot` or `/boot/efi` mount was returned by the exact mountpoint
queries; do not invent an `@cache` subvolume.

The default Btrfs subvolume is **top-level**, while the running root explicitly
uses `@`. Root snapshots do not include separately mounted home/log/swap
subvolumes. This repository and independent user-data backups remain necessary.

**Restore caveat:** do not blindly run `snapper rollback` or change the default
subvolume and assume it changes the booted root. GRUB's explicit root subvolume
selection and this layout must be reconciled in a separately approved recovery
rehearsal. No snapshot mount, deletion, rollback or subvolume change was attempted.

## Boot, EFI and initramfs

- Firmware mode observed as UEFI; ESP currently mounted at `/efi` as VFAT.
  EFI contents, NVRAM boot entries, disk geometry and identifiers are not captured.
- GRUB default entry 0; timeout 5; timeout style menu.
- `/etc/default/grub`: default Linux parameters `loglevel=3 quiet`; extra Linux
  parameters empty.
- Selected running kernel parameters also show rw and `rootflags=subvol=@`.
  Root device/boot-image identifiers were deliberately omitted.
- Captured initramfs config: MODULES, BINARIES and FILES arrays empty.
  HOOKS: base, systemd, autodetect, microcode, modconf, kms, keyboard, sd-vconsole,
  block, filesystems, fsck, sd-volatile.
- `grub-btrfsd` is enabled/active, with installed ExecStart
  `/usr/bin/grub-btrfsd --syslog /.snapshots`.
- Selected grub-btrfs snapshot parameter: `systemd.volatile=overlay`.
  Snapshot boot overlay is temporary; it is not proof of a persistent restore.

The GRUB defaults and grub-btrfs setting are sanitized observations here, **not new
raw-file sync mappings**. Do not regenerate GRUB/initramfs, install a bootloader
or change EFI on the working machine as part of this task.

## Swap and zram

The selected `/proc/swaps` summary showed approximately 16 GiB each:

- zram: priority 100, matching the captured zram-generator settings
  (size 16384, compression zstd).
- file-backed swap: priority 10, with swap placed under the separate swap
  subvolume design. Its exact file path/physical extent details are not exported.

A future Btrfs swapfile must meet kernel/Btrfs constraints (no CoW/compression on
the file, suitable allocation/extent layout and sufficient space). Mount-level
compression does not establish the file's actual flags. No resume parameter was
observed in the inspected running command line; hibernation recovery is not
claimed. Do not infer it from swap size.

## Wake-on-LAN: actual mechanism, not a hypothetical service

- NetworkManager's **active Ethernet connection** has persisted wake-on-lan
  property `magic`.
- Privileged ethtool inspection confirmed supported flags `pumbg`, current `g`.
  No SecureOn value, MAC, profile name/UUID or interface identity was exported.
- No custom WoL unit/config was found in the bounded custom networking paths.
  The verified persistence mechanism is the NetworkManager property.
- Firmware/UEFI WoL and power-state behavior were not retested. A `g` report
  alone does not prove wake from every shutdown/suspend state.

### Future reconstruction procedure — NOT executed

On the replacement Arch machine, identify its physical Ethernet connection
locally and set its wake-on-lan property to `magic` only with new approval.
Avoid a generic systemd service competing with NetworkManager. Verify the
hardware setting with ethtool after connection activation and reboot, then
perform an attended suspend/shutdown wake test.

On the Debian sender, install/use a magic-packet sender such as `wakeonlan`
or `etherwake` and supply the target MAC and any necessary LAN broadcast/interface
values from a private local record. The sender's package/configuration and
firmware support were not inspected here. No packet was sent and no power-state
transition occurred. Never commit those private identifiers to fill this gap.

## SSH, TTY and lockout prevention

The captured custom SSH drop-in says root login no, password authentication yes,
public-key authentication yes, and a restricted AllowUsers list. These existing
authentication semantics were not hardened or changed. UFW's loaded IPv4 rule
limits TCP/22 to the private LAN. Full effective sshd configuration and a new
authenticated network session were not tested in this phase.

Before any future access/firewall change: retain a working local TTY, verify
console login, preserve originals, validate config syntax, keep an existing
session open, and test a second connection before ending it. Do not restart
greetd from the only working graphical session. Keys, PAM and keyring wiring are
outside this backup and require independent secure recovery.

## Remaining independent-backup gaps

No personal data, snapshot contents, complete `/home`, EFI/bootloader image,
partition table, SATA disk data, secret store or firmware settings are backed up
by these documents. Phase B implementation and Phase C disposable-system
rehearsal each require separate approval; neither was started.
