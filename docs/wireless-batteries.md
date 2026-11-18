# Crimson wireless batteries

Two compact modules follow audio and precede the tray on both monitors:
`custom/mouse-battery` (mouse icon) and `custom/headset-battery` (headset icon).
The existing single-process/all-output layout, local workspaces/window titles,
monitoring, audio controls, tray, clock and power menu are unchanged.

Both modules invoke `home/.config/waybar/scripts/wireless_battery.py` with
`mouse` or `headset`, return JSON, and poll every **60 seconds** per output.
The existing Inter/Nerd Font typography, graphite cards, crimson borders and
hover styling are retained, with narrower padding for these two cards.

| Battery | Appearance |
|---|---|
| Above 20% | Standard text and graphite/crimson card |
| 11–20% | Existing pale-red warning text and dark warning background |
| 0–10% | Existing prominent red critical background and crimson border |
| Unavailable | Muted icon and `--`, never a cached percentage |

No animation, notification, click handler or settings GUI is added. Tooltips
identify the full device, source, percentage/status and polling interval.
Dynamic source strings are not copied into labels/tooltips; output uses JSON
encoding and Waybar's `escape: true`. Percentages must be finite numbers in
0–100. Commands run unprivileged without a shell, with a three-second per-command
timeout and five-second overall query budget. Missing executables, failed
commands, malformed data and unavailable batteries produce valid `--` JSON
without repeated traceback/error logging.

## Mouse: Logitech G PRO X SUPERLIGHT 2

UPower reports the abbreviated model **Logitech PRO X 2**, not the full retail
name. Model matching alone is insufficient because the headset's name resembles
it. The helper enumerates UPower devices over the system bus using `busctl` JSON,
then requires:

- UPower device kind **mouse** (`Type=5`) and the inspected model.
- A dynamically discovered HID++ power-supply native path.
- A sysfs HID parent with Logitech's verified **mouse product ID**.
- UPower `IsPresent`, a recognized battery state, kernel power-supply `online=1`,
  and agreement between UPower percentage and kernel capacity.

No UPower object index, USB port, receiver instance or device serial is pinned.
Product IDs identify models, not individual devices; no serials are published.
Absent/ambiguous matches, an offline power supply, unknown state or a mismatched
cached UPower reading show `--`. The UPower `Online` property is an AC-supply
property, not this wireless mouse's connectivity signal.

UPower and the kernel may retain a battery node/value after disconnection.
The helper therefore checks the kernel's `online` attribute every query rather
than trusting node existence or the old percentage alone. UPower `UpdateTime`
is not treated as a last-radio-contact timestamp: unchanged battery values need
not emit a new update. Hardware/kernel disconnect detection can still lag.

## Headset: Logitech G PRO X 2 LIGHTSPEED

Only this read-only command is used:

```sh
headsetcontrol -d 046d:0af7 -b -o json
```

The helper selects the matching receiver model from JSON and requires a
successful/partial device response, no battery error, and `BATTERY_AVAILABLE`
or `BATTERY_CHARGING` with an actual valid percentage. An absent receiver,
powered-off/disconnected headset, timeout, protocol error or other unavailable
result shows `--`. Charging with an unknown sentinel level also shows `--`;
charging does not imply a fabricated 100%.

During initial live inspection, HeadsetControl intermittently returned
`BATTERY_UNAVAILABLE` / `Protocol error`, while subsequent queries succeeded.
The fallback intentionally remains visible in that situation; the next
scheduled successful query restores the percentage. Receiver presence alone
does not prove that the headset is powered on. Neither a failure nor an
unavailable result is mislabeled as a confirmed power-off state.

No sidetone, EQ, inactive-time, audio-routing or other device setting is changed.
Existing HeadsetControl access permissions are used; no root polling, new udev
rule, driver, service or package installation is necessary.

## Dependencies, validation and recovery

Runtime prerequisites already present: Python 3 standard library, systemd's
`busctl`, UPower, HeadsetControl (validated with 4.2.0 JSON), existing Linux HID++
support, Waybar, and the current Nerd Font. Native Waybar UPower selection does
not provide the combined verified-identity/offline guards and requested battery
threshold styling; one small shared helper handles both sources instead.
The public helper is one exact new allowlist mapping; existing config and CSS
continue through the normal live-to-repository sync transaction.

Run fixtures without devices or privileges:

```sh
python3 -B tests/test_wireless_battery.py
python3 -B tests/test_workflow.py
python3 -B tests/test_recovery.py
./scripts/verify-manifest
./scripts/audit-repo
git diff --check
```

Battery fixtures cover normal/threshold/critical, disconnect with retained
percentage, wrong/ambiguous devices, charging without a level, malformed
responses, missing tools, timeout and failure after success (no stale cache).
Live validation includes underlying-source comparison, JSONC/GTK CSS parsing
and a temporary hidden Waybar startup before reloading the existing process.

The existing Hyprland autostart invokes one `waybar` process. Waybar's packaged
default **SIGUSR2 reloads that process's bars**; no compositor/session restart,
logout or new service is required. Select the actual current PID, not a stored
PID from another boot. Back up the live config/CSS before editing; if validation
or reload fails, restore those exact files and reload the same process.
The new helper can remain unused after restoring the original module list.

The display is a periodic snapshot, not a radio-link heartbeat: source changes
are reflected on the next poll (up to roughly 60 seconds plus query time and
source detection latency). Separate monitor modules can briefly differ when a
query fails. There is no persistent percentage cache or background daemon.
Headset reads from the two output modules are serialized with a POSIX lock
in the existing private `XDG_RUNTIME_DIR`; contention shares the same five-second
query deadline. The empty lock file contains no device data and disappears
with the login runtime directory. This prevents interleaved USB exchanges without
adding a service or changing device settings; independent external tools do not
participate in this lock.
Physical switch-off/unplug tests and interactive clicking/scrolling of existing
controls are not automated by the fixtures; report any untested cases honestly.
