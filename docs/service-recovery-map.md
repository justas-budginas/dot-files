# Service inventory interpretation — not bulk enablement

Observed 2026-11-15 from the existing reviewed `manifest/services.json`, selected
unit definitions/state queries and named recovery-package queries. Package
prerequisites below are reconstruction guidance, not exhaustive ownership proof. The inventory
originally contained **14 system + 6 user names**. The approved 2026-11-17 storage
update adds only `fstrim.timer`: **15 system + 6 user names** now.
Enabled is not synonymous with
running; inactive event/oneshot units can be normal.

## System units

| Inventory entry | Category / prerequisite | Future handling |
|---|---|---|
| NetworkManager.service | Daemon; networkmanager | Enable candidate after reviewing network access; never import connection secrets |
| NetworkManager-dispatcher.service | Event/D-Bus helper; networkmanager | Inspect packaged activation/dependencies; inactive at observation, not an error |
| NetworkManager-wait-online.service | Startup oneshot; networkmanager | Enable only if consumers need network-online; not a permanent daemon |
| greetd.service | Display manager; greetd, nwg-hello, Hyprland, themes/assets | Manual-only; validate greeter, account/VT and TTY recovery before any enable/start |
| sshd.service | Remote access; openssh | Manual-only; validate policy/keys and LAN-only UFW relationship first |
| ufw.service | Firewall; ufw | Manual-only; reconstruct reviewed policy before enabling; retain console access |
| grub-btrfsd.service | Snapshot-menu watcher; grub-btrfs, grub, Btrfs/Snapper layout | Manual-only; confirm `/.snapshots`, overlay/initramfs and boot integration |
| swayosd-libinput-backend.service | Input backend; swayosd | Candidate only when the compositor's swayosd-server integration is intended |
| systemd-timesyncd.service | Time sync; systemd | Review existing time provider; avoid competing daemons |
| systemd-userdbd.socket | Socket activation; systemd | Respect distro defaults/dependencies; not a desktop daemon to clone blindly |
| remote-fs.target | Synchronization target; systemd/mount design | Do not treat as an application service or infer remote mounts from its enablement |
| getty@.service | Template; systemd | Select actual console instance/VT policy; never bulk-enable the bare template |
| snapper-timeline.timer | Timer; snapper + configured root policy | Candidate after validating root policy and daily override |
| snapper-cleanup.timer | Timer; snapper + configured root policy | Candidate after retention/storage validation; snapshots are not independent backups |
| fstrim.timer | Stock weekly SSD maintenance; util-linux/systemd, mounted discard-capable filesystems | Enabled for reviewed SATA storage; preserve NVMe Btrfs async discard, note weekly overlap |

Selected runtime queries showed the named daemons/timers active, while dispatcher
and wait-online were inactive. Bare getty template state was not a runnable
instance check. No aliases, wants-directory symlinks or service files were copied
to reconstruct enablement.

## User units

| Inventory entry | Category / prerequisite | Future handling |
|---|---|---|
| pipewire.socket | Socket activation; pipewire | Use packaged audio setup, not copied runtime state |
| pipewire-pulse.socket | Pulse compatibility socket; pipewire-pulse | Coordinate with PipeWire; do not enable conflicting PulseAudio setup |
| wireplumber.service | Session manager; wireplumber | Preserve packaged PipeWire dependencies/aliases |
| gnome-keyring-daemon.socket | Secret-service socket; gnome-keyring | Preserve PAM/session integration separately; never export keyrings |
| p11-kit-server.socket | PKCS#11 socket; p11-kit | Respect packaged activation; no private token/key material |
| xdg-user-dirs.service | Session setup oneshot; xdg-user-dirs | Account/home-specific; not a persistent daemon or permission to import user data |

This is a package/prerequisite interpretation, not a promise those packages are
all explicitly installed (some are transitive dependencies). File presence and
effective behavior must be checked on a replacement installation.

## Non-automatic operating rule

Review candidates one at a time after packages and configurations are validated.
Distinguish `enable` (future activation links) from `start` (immediate action).
Never turn the JSON list into `systemctl enable --now ...`, never copy aliases or
template symlinks wholesale, and do not change services on this working host.
Phase B/C are still separate approval gates. The separately approved storage
work enabled only the reviewed `fstrim.timer`; see [storage.md](storage.md).
