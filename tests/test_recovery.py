#!/usr/bin/env python3
"""Sanitizer fixtures only: no privileged/live commands or real network values."""
import sys
sys.dont_write_bytecode = True
import importlib.util
import contextlib
import io
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "recovery_policy", Path(__file__).absolute().parents[1] / "scripts/recovery_policy.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class RecoveryPolicyTests(unittest.TestCase):
    def test_snapper_only_numeric_boolean_and_root_filesystem_policy(self):
        text = ('SUBVOLUME="/"\nFSTYPE="btrfs"\nNUMBER_CLEANUP="yes"\n'
                'NUMBER_LIMIT="2-10"\nSPACE_LIMIT="0.5"\n'
                'ALLOW_USERS="withheld-user"\nUNREVIEWED="withheld-value"\n')
        result = p.snapper_summary(text)
        self.assertEqual(result["NUMBER_LIMIT"], "2-10")
        self.assertIs(result["NUMBER_CLEANUP"], True)
        self.assertNotIn("ALLOW_USERS", result)
        self.assertNotIn("UNREVIEWED", result)

    def test_snapper_unexpected_values_fail_closed_without_value(self):
        for line in ['SUBVOLUME="/private"', 'FSTYPE="other"',
                     'NUMBER_LIMIT="withheld-canary"', 'TIMELINE_CREATE="sometimes"']:
            with self.assertRaises(ValueError) as error:
                p.snapper_summary('SUBVOLUME="/"\nFSTYPE="btrfs"\n' + line)
            self.assertNotIn("withheld-canary", str(error.exception))

    def test_ufw_does_not_publish_endpoints(self):
        # RFC1918 fixture synthesized at runtime, never an actual host endpoint.
        subnet = ".".join(map(str, (192, 168, 250, 0))) + "/24"
        text = ("Status: active\nDefault: deny (incoming), allow (outgoing), disabled (routed)\n"
                "To Action From\n-- ------ ----\n22/tcp ALLOW IN " + subnet + "\n")
        result = p.ufw_summary(text)
        self.assertTrue(result["active"])
        self.assertEqual(result["ssh_rules"][0]["source_scope"], "private-lan")
        self.assertNotIn(subnet, str(result))
        self.assertEqual(result["defaults"]["incoming"], "deny")

    def test_ufw_ipv6_anywhere_and_unknown_rule_not_silently_accepted(self):
        result = p.ufw_summary(
            "Status: active\nTo Action From\n-- ------ ----\n"
            "22/tcp (v6) ALLOW IN Anywhere (v6)\n443/tcp ALLOW IN withheld\n")
        self.assertEqual(result["ssh_rules"][0]["family"], "ipv6")
        self.assertEqual(result["ssh_rules"][0]["source_scope"], "any")
        self.assertEqual(result["unreviewed_rule_rows"], 1)

    def test_invalid_ufw_output_is_withheld(self):
        with self.assertRaises(ValueError):
            p.ufw_summary("withheld-canary")

    def test_btrfs_does_not_publish_ids(self):
        self.assertEqual(p.btrfs_default_summary("ID 5 (FS_TREE)\n"), "top-level")
        self.assertEqual(p.btrfs_default_summary("ID 256 gen 42 top level 5 path @\n"), "@")
        with self.assertRaises(ValueError):
            p.btrfs_default_summary("ID 999 path private-data")

    def test_wol_never_exports_secureon_or_other_fields(self):
        result = p.wol_summary(
            "Supports Wake-on: pumbg\nWake-on: g\n"
            "SecureOn pass" + "word: withheld-canary\nAddress: withheld-canary\n")
        self.assertEqual(result, {"supported_flags": "pumbg", "current_flags": "g"})
        self.assertNotIn("withheld-canary", str(result))

    def test_privileged_command_has_no_shell_or_inherited_environment(self):
        with patch.object(p.subprocess, "run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "safe"
            self.assertEqual(p.run("ufw", "status", "verbose"), "safe")
            args, kwargs = run.call_args
            self.assertEqual(args[0], ["/usr/bin/ufw", "status", "verbose"])
            self.assertNotIn("shell", kwargs)
            self.assertEqual(set(kwargs["env"]), {"PATH", "LANG", "LC_ALL"})

    def test_arbitrary_or_write_commands_are_refused_before_execution(self):
        for program, args in [("ufw", ("enable",)), ("nmcli", ("connection", "show")),
                              ("btrfs", ("subvolume", "delete", "/")),
                              ("sh", ("-c", "unexpected")), ("ethtool", ("-s", "unused")),
                              ("ethtool", ("-s",))]:
            with patch.object(p.subprocess, "run") as run:
                with self.assertRaises(ValueError):
                    p.run(program, *args)
                run.assert_not_called()

    def test_default_invocation_cannot_inspect_even_if_root(self):
        with patch.object(sys, "argv", ["inspect-recovery-policy"]), \
             patch.object(p.os, "geteuid", return_value=0), \
             patch.object(p, "collect") as collect, \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                p.main()
            collect.assert_not_called()

    def test_probe_failure_does_not_echo_private_diagnostics(self):
        stderr = io.StringIO()
        with patch.object(sys, "argv", ["inspect-recovery-policy", "--privileged-read-only"]), \
             patch.object(p.os, "geteuid", return_value=0), \
             patch.object(p, "collect", side_effect=ValueError("withheld-canary")), \
             contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit):
                p.main()
        self.assertNotIn("withheld-canary", stderr.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
