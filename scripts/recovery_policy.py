"""Bounded sanitizers for an optional, locally approved privileged inspection.

No arbitrary source/command arguments, configuration copies, temporary files,
network-profile exports, identifiers or setting changes. Output is a proposal
for human review, never automatically saved/imported by configuration sync.
"""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

SNAPPER_BOOLEANS = {
    "NUMBER_CLEANUP", "TIMELINE_CREATE", "TIMELINE_CLEANUP",
    "EMPTY_PRE_POST_CLEANUP",
}
SNAPPER_NUMBERS = {
    "NUMBER_MIN_AGE", "NUMBER_LIMIT", "NUMBER_LIMIT_IMPORTANT",
    "TIMELINE_MIN_AGE", "TIMELINE_LIMIT_HOURLY", "TIMELINE_LIMIT_DAILY",
    "TIMELINE_LIMIT_WEEKLY", "TIMELINE_LIMIT_MONTHLY", "TIMELINE_LIMIT_YEARLY",
    "EMPTY_PRE_POST_MIN_AGE", "SPACE_LIMIT", "FREE_LIMIT",
}


def snapper_summary(text):
    result = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        key = key.strip()
        if not sep:
            continue
        value = value.strip().strip("\"'")
        if key in SNAPPER_BOOLEANS:
            if value not in ("yes", "no"):
                raise ValueError("Unexpected Snapper boolean; raw value withheld")
            result[key] = value == "yes"
        elif key in SNAPPER_NUMBERS:
            if not re.fullmatch(r"\d+(?:[.-]\d+)?", value):
                raise ValueError("Unexpected Snapper numeric policy; raw value withheld")
            result[key] = value
        elif key == "SUBVOLUME":
            if value != "/":
                raise ValueError("Unexpected Snapper target; raw value withheld")
            result[key] = "/"
        elif key == "FSTYPE":
            if value != "btrfs":
                raise ValueError("Unexpected Snapper filesystem; raw value withheld")
            result[key] = "btrfs"
    if not {"SUBVOLUME", "FSTYPE"} <= result.keys():
        raise ValueError("Snapper root policy missing expected fields")
    return result


def source_scope(value):
    if value == "Anywhere":
        return "any"
    try:
        network = ipaddress.ip_network(value, strict=False)
    except ValueError:
        return "unpublished"
    if network.version == 4 and any(
        network.subnet_of(ipaddress.ip_network(c))
        for c in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
    ):
        return "private-host" if network.prefixlen == 32 else "private-lan"
    return "restricted-source-unpublished"


def ufw_summary(text):
    status = re.search(r"^Status: (active|inactive)$", text, re.M)
    if not status:
        raise ValueError("Unrecognized UFW output; raw output withheld")
    result = {"active": status.group(1) == "active", "defaults": {},
              "ssh_rules": [], "unreviewed_rule_rows": 0}
    default = re.search(r"^Default: (.+)$", text, re.M)
    if default:
        for policy, direction in re.findall(
            r"\b(deny|allow|reject|disabled) \((incoming|outgoing|routed)\)",
            default.group(1)
        ):
            result["defaults"][direction] = policy
    in_rules = False
    for line in text.splitlines():
        if re.match(r"^-+\s+-+", line):
            in_rules = True
            continue
        if not in_rules or not line.strip():
            continue
        match = re.fullmatch(
            r"\s*(22/tcp|22|OpenSSH)(?:\s+(\(v6\)))?\s+"
            r"(ALLOW|LIMIT|DENY|REJECT)\s+(IN|OUT)\s+(\S+)(?:\s+.*)?",
            line,
        )
        if not match:
            result["unreviewed_rule_rows"] += 1
            continue
        result["ssh_rules"].append({
            "family": "ipv6" if match.group(2) else "ipv4",
            "port": 22, "transport": "tcp" if match.group(1) != "22" else "any",
            "action": match.group(3).lower(), "direction": match.group(4).lower(),
            "source_scope": source_scope(match.group(5)),
        })
    return result


def btrfs_default_summary(text):
    if re.fullmatch(r"\s*ID 5 \(FS_TREE\)\s*", text):
        return "top-level"
    path = re.search(r"\bpath (.+)$", text.strip())
    if path and path.group(1) in ("@", "@home", "@log", "@snapshots", "@swap"):
        return path.group(1)
    raise ValueError("Unrecognized default subvolume; identifiers withheld")


def wol_summary(text):
    result = {}
    for label, field in (("Supports Wake-on", "supported_flags"), ("Wake-on", "current_flags")):
        match = re.search(r"^\s*" + re.escape(label) + r": ([pumbagsdf]+)\s*$", text, re.M)
        if match:
            result[field] = match.group(1)
    return result


def run(program, *args):
    # Absolute packaged executables only; no shell, arbitrary commands or writes.
    allowed = (
        (program == "ufw" and args == ("status", "verbose"))
        or (program == "btrfs" and args == ("subvolume", "get-default", "/"))
        or (program == "nmcli" and args == ("-t", "-f", "DEVICE,TYPE", "device", "status"))
        or (program == "ethtool" and len(args) == 1
            and re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", args[0]))
    )
    if not allowed:
        raise ValueError("Command outside the bounded read-only scope")
    result = subprocess.run(
        ["/usr/bin/" + program, *args], capture_output=True, text=True, timeout=20,
        env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
    )
    if result.returncode:
        raise ValueError("Selected read-only query unavailable; raw diagnostics withheld")
    return result.stdout


def read_snapper_root():
    path = Path("/etc/snapper/configs/root")
    for component in [*reversed(path.parents), path]:
        if component.is_symlink():
            raise ValueError("Replaced policy path")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 128 * 1024:
            raise ValueError("Unexpected root policy type/size")
        data = stream.read(128 * 1024 + 1)
    if len(data) > 128 * 1024:
        raise ValueError("Unexpected root policy size")
    return data.decode("utf-8")


def collect():
    # Contents are parsed in memory; only selected nonsecret fields leave this function.
    result = {
        "schema_version": 1, "scope": "privileged-read-only-sanitized-proposal",
        "snapper_root": snapper_summary(read_snapper_root()),
        "ufw_loaded": ufw_summary(run("ufw", "status", "verbose")),
        "btrfs_default_subvolume": btrfs_default_summary(run("btrfs", "subvolume", "get-default", "/")),
        "ethernet_wol": [],
    }
    # DEVICE/TYPE only: no connection identity, address, key or profile content.
    devices = run("nmcli", "-t", "-f", "DEVICE,TYPE", "device", "status")
    for line in devices.splitlines():
        fields = line.split(":")
        if len(fields) != 2 or fields[1] != "ethernet":
            continue
        interface = fields[0]
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", interface):
            raise ValueError("Unexpected interface name; withheld")
        result["ethernet_wol"].append(wol_summary(run("ethtool", interface)))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--privileged-read-only", action="store_true",
                        help="explicit opt-in; requires separately approved local sudo")
    args = parser.parse_args()
    try:
        if not args.privileged_read_only or os.geteuid() != 0:
            raise ValueError("Needs explicit --privileged-read-only and locally approved sudo. No writes.")
        print(json.dumps(collect(), indent=2, sort_keys=True))
    except (OSError, ValueError, subprocess.SubprocessError):
        # Never print raw content, command stderr, network values or exception data.
        print("READ-ONLY INSPECTION STOPPED: a selected query or policy value is unavailable/unexpected; "
              "raw data withheld. No settings changed.", file=sys.stderr)
        raise SystemExit(1) from None
