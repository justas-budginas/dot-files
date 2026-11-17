# Inspected system and portability notes

## Desktop

The manifest includes current Hyprland Lua (including Super+Shift+arrow moves),
Hypridle, Hyprlock, Hyprpaper, Waybar and its GPU helper, all four Rofi theme files,
the executable power menu, Kitty/colors, Starship, Zsh, Mako and GTK3/4 settings.
There were no custom user systemd unit files: installed-unit enablement symlinks
are inventory information, not files to copy.

Dependencies observed in configs include Hyprland, Hyprlock, Hypridle, Hyprpaper,
hyprpolkitagent, Waybar, Python, Rofi, Kitty, Thunar, Mako, swayosd, network-manager-applet,
NetworkManager, pavucontrol, playerctl, brightnessctl, wireplumber/wpctl, grim,
slurp, satty, wl-clipboard, loginctl/systemctl, Inter, JetBrains Mono, Font Awesome,
Nerd Font symbols, adw-gtk3-dark, Flat-Remix-Red-Dark and Bibata-Modern-Classic.
Some referenced programs may be absent or transitive dependencies: a package list
is not proof every binding works. No packages were installed.

`.zshrc` references installed Zsh plugins, optional NVM initialization and an
existing OpenCode executable directory. Only `.zshrc` itself is allowlisted.
NVM trees, OpenCode configuration/authentication and project data are not copied.
Comments may reference the existing local project notes; those notes are not
included wholesale.

## Host-specific settings

- Lenovo DP-1: 2560×1440 at approximately 180 Hz, origin (0,0).
- Dell HDMI-A-2: 2560×1440 at approximately 75 Hz, origin (2560,0).
- Hyprlock password/hint target DP-1; clock/date remain on both.
- Greeter GDK form index 0 was verified as Lenovo on this host. Do not assume
  that index on a new machine.
- GPU helper intentionally targets PCI `0000:03:00.0`, vendor/device `1002:7590`.
  Re-identify hardware rather than falling back silently to an iGPU.
- Wallpaper and power-button references include `/home/neo`; snapshot bytes stay
  unchanged. A future restore must explicitly review path substitutions for a
  different account. It must look up account UID/GID, never assume 1000.
- Zram size, SSH `AllowUsers neo`, output names and display modes are host-specific.
- `ufw.conf` contains enable/logging preferences only; raw firewall rules are not
  copied. Phase A now records a sanitized, directly observed loaded-policy summary.
- WoL persistence was subsequently verified as the NetworkManager active Ethernet
  connection's `magic` property, with hardware flags `g`. Only that specific
  property was queried, not a profile/secret export. No custom service is assumed.
  See the dated [system recovery inventory](system-recovery-inventory.md).

## Selected settings outside plain files

Read-only appearance queries observed: prefer-dark, adw-gtk3-dark,
Flat-Remix-Red-Dark, Bibata-Modern-Classic size 24, Inter 11, and the current
desktop monospace setting Adwaita Mono 11. Kitty independently uses JetBrains
Mono 11. Do not change these to make an inventory look consistent.
`propose-inventories` emits only these seven keys, not the dconf database.

At inspection: 79 explicit native packages, three foreign packages
(`bibata-cursor-theme-bin`, `flat-remix`, `paru`); originally 14 enabled system unit names and
six enabled user unit names. Unit names such as keyring socket activation are
not credentials or keyring database exports. Generic getty templates/aliases and
socket activation must be interpreted before any future enablement automation.

## System configuration scope

The ten approved system text files and one deployed greeter PNG are readable by
the normal account today. No elevated exporter or sudo is needed. If permissions
change, sync stops; do not run the whole tool as root. A future extra root-only
source needs a separately reviewed minimal read/export step.

greetd/nwg-hello, zram, SSH daemon policy, initramfs/package-manager preferences and
the Snapper timer override are snapshots for **manual-only** restore. They do not
include PAM, host keys, runtime state, system defaults or a raw root-only Snapper
config. Phase A adds sanitized Snapper retention, mount/boot and firewall/WoL
observations in separate reviewed docs—not new raw-file sync mappings. Firewall,
SSH, boot and greeter recovery still depend on more than the copied files.

## SATA storage requirements — 2026-11-17

The additional exact mapping is `.config/storage/sata-fstab.conf`, a user-reviewed
SATA-only recovery fragment. It does not replace or automatically configure
fstab. See [storage recovery](storage.md) for the approved UUIDs, automatic startup
mounts, protection/access roles and integrity results. Full fstab and private
inventories are not imported. The manifest now contains 33 mappings.

Recovery needs the existing `util-linux`, `e2fsprogs`, `acl`, `systemd`,
`udisks2`, `gvfs`, Thunar and Polkit integration. These include transitive
dependencies; the explicit native package inventory was not falsified to mark
them all explicitly installed. No packages were installed by the SATA work.
`fstrim.timer` is now separately reviewed/enabled, making 15 system inventory
names; six user inventory names remain unchanged.

## Wallpapers

Only the final two native desktop halves and one blurred/darkened greeter image
are approved: 8,601,665 bytes total, approximately 8.2 MiB. No embedded metadata
was found. The greeter asset is a processed composition of the two desktop halves.
Only these deployed artifacts are included, not large source generations or
duplicate derivatives. Origin/redistribution license was not independently
established: keep the remote private and resolve provenance before public sharing.
The reviewed hashes are pinned in the sync tool; new artwork needs approval.
