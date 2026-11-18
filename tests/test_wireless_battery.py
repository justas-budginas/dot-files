#!/usr/bin/env python3
"""Synthetic fixtures only; optional script path permits pre-sync validation."""
import sys
sys.dont_write_bytecode = True
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = (Path(sys.argv.pop(1)) if len(sys.argv) > 1 and not sys.argv[1].startswith("-")
          else Path(__file__).resolve().parents[1] /
          "home/.config/waybar/scripts/wireless_battery.py")
spec = importlib.util.spec_from_file_location("wireless_battery", SCRIPT)
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


def headset_data(level=70, status="BATTERY_AVAILABLE"):
    return {"devices": [{"id_vendor": "0x046d", "id_product": "0x0af7",
                         "status": "success",
                         "battery": {"status": status, "level": level}}]}


class WirelessBatteryTests(unittest.TestCase):
    def setUp(self):
        self.runtime = tempfile.TemporaryDirectory(dir="/tmp/opencode")
        self.addCleanup(self.runtime.cleanup)
        env = patch.dict(b.os.environ, {"XDG_RUNTIME_DIR": self.runtime.name})
        env.start()
        self.addCleanup(env.stop)

    def test_thresholds_and_json(self):
        for value, state in [(100, "normal"), (21, "normal"), (20, "low"),
                             (11, "low"), (10, "critical"), (0, "critical")]:
            result = b.headset(lambda args: headset_data(value))
            self.assertEqual(result["class"], state)
            self.assertEqual(result["text"], f"{value}%")
            self.assertEqual(json.loads(json.dumps(result)), result)

    def test_invalid_percentages_fail_closed(self):
        for value in [-1, 101, 10**400, "99", True, float("nan"), float("inf")]:
            with self.subTest(value=value), patch.object(b, "query", return_value=headset_data(value)):
                result = b.snapshot("headset")
                self.assertEqual(result["text"], "--")
                self.assertNotIn("percentage", result)

    def test_headset_disconnected_missing_and_error(self):
        fixtures = [
            {"devices": []},
            headset_data(-1, "BATTERY_UNAVAILABLE"),
            headset_data(99, "BATTERY_TIMEOUT"),
            headset_data(99, "BATTERY_ERROR"),
            {"devices": [dict(headset_data()["devices"][0], errors={"battery": "<private>"})]},
            {"devices": [dict(headset_data()["devices"][0], id_product="0xffff")]},
            {"devices": [dict(headset_data()["devices"][0], status="error")]},
        ]
        for data in fixtures:
            with self.subTest(data=data):
                result = b.headset(lambda args: data)
                self.assertEqual(result["text"], "--")
                self.assertNotIn("<private>", result["tooltip"])

    def test_charging_requires_real_percentage(self):
        self.assertEqual(b.headset(lambda a: headset_data(-1, "BATTERY_CHARGING"))["text"], "--")
        self.assertEqual(b.headset(lambda a: headset_data(40, "BATTERY_CHARGING"))["text"], "40%")

    def test_no_cache_after_failure(self):
        with patch.object(b, "query", return_value=headset_data(70)):
            self.assertEqual(b.snapshot("headset")["text"], "70%")
        with patch.object(b, "query", side_effect=FileNotFoundError):
            self.assertEqual(b.snapshot("headset")["text"], "--")

    def test_malformed_missing_executable_and_timeout(self):
        for error in [ValueError(), KeyError(), TypeError(), IndexError(),
                      AttributeError(), FileNotFoundError(), PermissionError(),
                      subprocess.TimeoutExpired("fixture", 3),
                      subprocess.CalledProcessError(1, "fixture")]:
            for kind in ("mouse", "headset"):
                with self.subTest(error=error, kind=kind), patch.object(b, "query", side_effect=error):
                    self.assertEqual(b.snapshot(kind)["class"], "unavailable")
        for data in [{}, [], {"devices": None}, {"devices": [None]},
                     {"devices": [{"id_vendor": "0x046d", "id_product": "0x0af7",
                                   "status": "success", "battery": []}]}]:
            with patch.object(b, "query", return_value=data):
                self.assertEqual(b.snapshot("headset")["text"], "--")

    def test_bounded_read_only_command(self):
        with patch.object(b.subprocess, "run") as run:
            run.return_value.stdout = '{"devices":[]}'
            self.assertEqual(b.snapshot("headset")["text"], "--")
            args, kwargs = run.call_args
            self.assertEqual(args[0], ["headsetcontrol", "-d", "046d:0af7", "-b", "-o", "json"])
            self.assertLessEqual(kwargs["timeout"], 3)
            self.assertNotIn("shell", kwargs)

    def test_headset_lock_symlink_refused(self):
        lock = Path(self.runtime.name) / "waybar-headset-battery.lock"
        target = Path(self.runtime.name) / "do-not-open"
        target.write_text("fixture")
        lock.symlink_to(target)
        with patch.object(b, "query") as query:
            self.assertEqual(b.snapshot("headset")["text"], "--")
            query.assert_not_called()
        self.assertEqual(target.read_text(), "fixture")

    def test_headset_lock_deadline_returns_unavailable(self):
        with patch.object(b.fcntl, "flock", side_effect=BlockingIOError), \
                patch.object(b.time, "monotonic", side_effect=[0, 6]), \
                patch.object(b, "query") as query:
            self.assertEqual(b.snapshot("headset")["text"], "--")
            query.assert_not_called()

    def make_mouse(self, base):
        supplies = base / "power_supply"
        supplies.mkdir()
        parent = base / "0003:046D:40A9.9999"
        source = parent / "power_supply/hidpp_battery_7"
        source.mkdir(parents=True)
        (parent / "uevent").write_text("HID_ID=0003:0000046D:000040A9\n")
        for key, val in {"online": "1", "capacity": "65"}.items():
            (source / key).write_text(val)
        (supplies / source.name).symlink_to(source)
        props = {"Type": 5, "Model": "Logitech PRO X 2", "NativePath": source.name,
                 "IsPresent": True, "State": 2, "Percentage": 65}
        return supplies, source, props

    def mouse_query(self, props, paths=None):
        def run(args):
            if args[-1] == "EnumerateDevices":
                return {"data": [paths or ["/org/freedesktop/UPower/devices/battery_hidpp_battery_7"]]}
            return {"data": [{k: {"data": v} for k, v in props.items()}]}
        return run

    def test_mouse_discovery_and_disconnect_with_retained_percentage(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            supplies, source, props = self.make_mouse(Path(tmp))
            run = self.mouse_query(props)
            self.assertEqual(b.mouse(run, supplies)["text"], "65%")
            (source / "online").write_text("0")
            self.assertEqual(b.mouse(run, supplies)["text"], "--")
            (source / "online").write_text("1")
            props["IsPresent"] = False
            self.assertEqual(b.mouse(run, supplies)["text"], "--")

    def test_mouse_identity_not_just_model_or_upower_index(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            supplies, source, props = self.make_mouse(Path(tmp))
            run = self.mouse_query(props)
            props["Type"] = 8
            self.assertEqual(b.mouse(run, supplies)["text"], "--")
            props["Type"] = 5
            parent = source.parents[1]
            (parent / "uevent").write_text("HID_ID=0003:0000046D:00000AF7\n")
            self.assertEqual(b.mouse(run, supplies)["text"], "--")

    def test_mouse_stale_mismatch_unknown_state_and_duplicates(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            supplies, source, props = self.make_mouse(Path(tmp))
            run = self.mouse_query(props)
            (source / "capacity").write_text("64")
            self.assertEqual(b.mouse(run, supplies)["text"], "--")
            (source / "capacity").write_text("65")
            props["State"] = 0
            self.assertEqual(b.mouse(run, supplies)["text"], "--")
            props["State"] = 2
            paths = ["/org/freedesktop/UPower/devices/test"] * 2
            self.assertEqual(b.mouse(self.mouse_query(props, paths), supplies)["text"], "--")

    def test_mouse_low_and_critical(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            supplies, source, props = self.make_mouse(Path(tmp))
            for value, state in [(20, "low"), (10, "critical")]:
                props["Percentage"] = value
                (source / "capacity").write_text(str(value))
                self.assertEqual(b.mouse(self.mouse_query(props), supplies)["class"], state)


if __name__ == "__main__":
    unittest.main(verbosity=2)
