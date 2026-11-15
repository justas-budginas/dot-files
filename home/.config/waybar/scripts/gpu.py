#!/usr/bin/env python3
"""One read-only RX 9060 XT snapshot for Waybar; Python standard library only.

Use the verified PCI address and device ID, never reboot-dependent DRM card IDs.
The display reports AMDGPU engine busy time, not a benchmark or VRAM utilization.
"""
import json
from pathlib import Path

DEVICE = Path("/sys/bus/pci/devices/0000:03:00.0")


def integer(path):
    return int(path.read_text().strip())


def snapshot(device=DEVICE):
    try:
        if ((device / "vendor").read_text().strip(),
                (device / "device").read_text().strip()) != ("0x1002", "0x7590"):
            raise ValueError("Unexpected PCI device")
        busy = integer(device / "gpu_busy_percent")
        if not 0 <= busy <= 100:
            raise ValueError("Invalid GPU busy percentage")
    except (OSError, ValueError):
        return {
            "text": "N/A",
            "tooltip": "RX 9060 XT telemetry unavailable at PCI 0000:03:00.0",
            "class": "unavailable",
        }

    details = [
        "Radeon RX 9060 XT · PCI 0000:03:00.0",
        f"GPU engine busy: {busy}%",
    ]
    try:
        used = integer(device / "mem_info_vram_used")
        total = integer(device / "mem_info_vram_total")
        if 0 <= used <= total and total > 0:
            details.append(f"VRAM allocated: {used / 2**30:.2f} / {total / 2**30:.2f} GiB")
    except (OSError, ValueError):
        pass

    for hwmon in sorted((device / "hwmon").glob("hwmon*")):
        try:
            if (hwmon / "name").read_text().strip() != "amdgpu":
                continue
            for label in sorted(hwmon.glob("temp*_label")):
                name = label.read_text().strip()
                if name not in ("edge", "junction", "mem"):
                    continue
                value = integer(label.with_name(label.name.replace("_label", "_input"))) / 1000
                if -20 <= value <= 150:
                    names = {"edge": "GPU edge", "junction": "GPU junction", "mem": "VRAM"}
                    details.append(f"{names[name]} temperature: {value:.0f}°C")
        except (OSError, ValueError):
            continue
    details.append("AMDGPU sysfs · sampled every 5s · VRAM is driver allocation")
    return {"text": f"{busy}%", "tooltip": "\n".join(details), "class": "available"}


if __name__ == "__main__":
    print(json.dumps(snapshot(), ensure_ascii=False))
