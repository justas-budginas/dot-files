# Kingston FURY DDR5 boot lighting

`crimson-kingston-ram-rgb.service` applies static `FF0000` using OpenRGB's
headless CLI, then exits. It runs as a system oneshot at `multi-user.target`
without depending on Hyprland, a login or an OpenRGB server. Its isolated
runtime configuration is removed when the service exits.

Requires Arch's `openrgb` package (tested with 1.1), systemd, `kmod`
(`modprobe`), and kernel support for `i2c-dev` and `i2c-piix4`. The unit loads
both modules before OpenRGB runs, without unloading or blacklisting `spd5118`.
The packaged OpenRGB server is not needed.

OpenRGB uses case-insensitive substring matching for device names. With
discovery only, the full `Kingston Fury DDR5 DRAM` selector matched one DRAM
controller with two Fury slots; neither GPU nor motherboard matched. On another
installation, verify this match with `--list-detailed` and an empty, isolated
configuration before attempting any write. Do not remove the device selector
or substitute a numerical index.

The [reviewed unit](../system/etc/systemd/system/crimson-kingston-ram-rgb.service)
is for manual installation as root, not bulk activation. From the checkout:

```sh
sudo install -o root -g root -m 0644 \
  system/etc/systemd/system/crimson-kingston-ram-rgb.service \
  /etc/systemd/system/crimson-kingston-ram-rgb.service
systemd-analyze verify --man=no /etc/systemd/system/crimson-kingston-ram-rgb.service
sudo systemctl daemon-reload
sudo systemctl start crimson-kingston-ram-rgb.service
systemctl show crimson-kingston-ram-rgb.service -p Result -p MainPID -p ActiveState
journalctl -b -u crimson-kingston-ram-rgb.service
# Confirm both sticks are solid red before enabling:
sudo systemctl enable crimson-kingston-ram-rgb.service
```

Success is `Result=success`, `MainPID=0` and `ActiveState=inactive`; the LEDs
stay red without a process. Manual activation passed and both sticks were
visually confirmed solid red. A separate, write-free missing-device test
showed exit code 255 and a failed unit result in systemd. On 2026-11-24 the
boot journal confirmed a successful run and the owner reported the lighting
working after boot.

Disable future runs with `sudo systemctl disable --now crimson-kingston-ram-rgb.service`.
To remove the setup, then remove only `/etc/systemd/system/crimson-kingston-ram-rgb.service`
and run `sudo systemctl daemon-reload`. This does not revert the color already
applied or remove any drivers.
