#!/usr/bin/env python3
"""Read-only wireless battery snapshots; no cache, settings writes or dependencies."""
import json
from contextlib import contextmanager
import fcntl
import math
import os
from pathlib import Path
import re
import subprocess
import stat
import sys
import time

UPOWER = "org.freedesktop.UPower"
MOUSE = "Logitech G PRO X SUPERLIGHT 2"
HEADSET = "Logitech G PRO X 2 LIGHTSPEED"


@contextmanager
def headset_lock(deadline):
    # Each output has its own module. Never interleave USB exchanges from them.
    runtime = Path(os.environ["XDG_RUNTIME_DIR"])
    if not runtime.is_absolute() or runtime.stat().st_uid != os.getuid():
        raise ValueError("Invalid runtime directory")
    fd = os.open(runtime / "waybar-headset-battery.lock",
                 os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError("Invalid runtime lock")
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Battery query lock deadline")
                time.sleep(0.05)
        yield
    finally:
        os.close(fd)


def query(args, timeout=3):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                            check=True)
    return json.loads(result.stdout)


def output(name, source, value=None, status="Unavailable"):
    if value is None:
        return {"text": "--", "class": "unavailable",
                "tooltip": f"{name}\nBattery unavailable · {status}\n{source} · every 60s"}
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Invalid percentage")
    if not 0 <= value <= 100 or not math.isfinite(value):
        raise ValueError("Invalid percentage")
    state = "critical" if value <= 10 else "low" if value <= 20 else "normal"
    text = f"{value:g}%"
    return {"text": text, "class": state, "percentage": value,
            "tooltip": f"{name}\nBattery: {text} · {status}\n{source} · every 60s"}


def mouse_identity(props, supplies):
    # UPower's model is abbreviated and shared-looking: require mouse kind and
    # the verified HID++ product ID as well. Never pin hidpp_battery_N or serial.
    if props.get("Type") != 5 or props.get("Model") != "Logitech PRO X 2":
        return None
    native = props.get("NativePath", "")
    if not isinstance(native, str) or not re.fullmatch(r"hidpp_battery_[0-9]+", native):
        return None
    supply = supplies / native
    for parent in supply.resolve(strict=True).parents:
        if parent.name.startswith("0003:046D:40A9."):
            fields = dict(line.split("=", 1) for line in
                          (parent / "uevent").read_text().splitlines() if "=" in line)
            if fields.get("HID_ID") == "0003:0000046D:000040A9":
                return supply
    return None


def mouse(run=query, supplies=Path("/sys/class/power_supply")):
    paths = run(["busctl", "--system", "--json=short", "--timeout=2", "call",
                 UPOWER, "/org/freedesktop/UPower", UPOWER, "EnumerateDevices"])["data"][0]
    if not isinstance(paths, list) or len(paths) > 8:
        raise ValueError("Unexpected UPower device list")
    matches = []
    for path in paths:
        if not isinstance(path, str) or not re.fullmatch(
                r"/org/freedesktop/UPower/devices/[A-Za-z0-9_]+", path):
            raise ValueError("Unexpected UPower path")
        raw = run(["busctl", "--system", "--json=short", "--timeout=2", "call",
                   UPOWER, path, "org.freedesktop.DBus.Properties", "GetAll",
                   "s", UPOWER + ".Device"])["data"][0]
        props = {key: val["data"] for key, val in raw.items()}
        supply = mouse_identity(props, supplies)
        if supply is not None:
            matches.append((props, supply))
    if len(matches) != 1:
        return output(MOUSE, "UPower / HID++", status="Mouse absent or ambiguous")
    props, supply = matches[0]
    # UPower can retain a device/percentage after radio disconnection. Check the
    # kernel's live online flag and capacity, not UPower's non-applicable AC Online.
    if (props.get("IsPresent") is not True or
            (supply / "online").read_text().strip() != "1"):
        return output(MOUSE, "UPower / HID++", status="Disconnected")
    statuses = {1: "Charging", 2: "Discharging", 4: "Fully charged"}
    status = statuses.get(props.get("State"))
    value = props.get("Percentage")
    kernel_value = int((supply / "capacity").read_text().strip())
    if status is None or value != kernel_value:
        return output(MOUSE, "UPower / HID++", status="Battery state not confirmed")
    return output(MOUSE, "UPower / HID++", value, "Connected · " + status)


def headset(run=query):
    data = run(["headsetcontrol", "-d", "046d:0af7", "-b", "-o", "json"])
    devices = data["devices"]
    if not isinstance(devices, list):
        raise ValueError("Invalid headset response")
    matches = [d for d in devices if d.get("id_vendor") == "0x046d" and
               d.get("id_product") == "0x0af7"]
    if len(matches) != 1:
        return output(HEADSET, "HeadsetControl", status="Receiver absent or ambiguous")
    device = matches[0]
    if device.get("status") not in ("success", "partial"):
        return output(HEADSET, "HeadsetControl", status="Device query failed")
    battery = device["battery"]
    status = battery.get("status")
    if device.get("errors", {}).get("battery"):
        return output(HEADSET, "HeadsetControl", status="Battery query failed")
    if status not in ("BATTERY_AVAILABLE", "BATTERY_CHARGING"):
        return output(HEADSET, "HeadsetControl",
                      status="Off, disconnected or battery query unavailable")
    value = battery.get("level")
    # Charging-only reports sometimes use -1: never invent a charging percentage.
    if value == -1 and status == "BATTERY_CHARGING":
        return output(HEADSET, "HeadsetControl", status="Charging · percentage unavailable")
    return output(HEADSET, "HeadsetControl", value,
                  "Connected · Charging" if status == "BATTERY_CHARGING" else "Connected")


def snapshot(kind):
    name, source = (MOUSE, "UPower / HID++") if kind == "mouse" else (HEADSET, "HeadsetControl")
    try:
        deadline = time.monotonic() + 5
        def bounded(args):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Battery query deadline")
            return query(args, timeout=min(3, remaining))
        if kind == "mouse":
            return mouse(run=bounded)
        with headset_lock(deadline):
            return headset(run=bounded)
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError,
            subprocess.SubprocessError):
        # No raw command output/device identifiers in tooltips or recurring stderr.
        return output(name, source, status="Query failed or source unavailable")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("mouse", "headset"):
        raise SystemExit("Usage: wireless_battery.py mouse|headset")
    print(json.dumps(snapshot(sys.argv[1]), ensure_ascii=False))
