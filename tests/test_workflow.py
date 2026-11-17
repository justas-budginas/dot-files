#!/usr/bin/env python3
"""Isolated disposable Git repos and fake homes; no live snapshots or commits."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import copy
import contextlib
import io
import importlib.util
import json
import os
import subprocess
import tempfile
import struct
import zlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "dotfiles", Path(__file__).absolute().parents[1] / "scripts/dotfiles.py")
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


class Workflow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="dotfiles-test-", dir="/tmp/opencode")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / "repo"
        self.home = self.base / "fake-home"
        self.repo.mkdir()
        self.home.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        (self.repo / "manifest").mkdir()
        (self.repo / "README.md").write_text("# sandbox\n")
        self.entries = []
        for rel, mode in [(".zshrc", "0644"), (".local/bin/powermenu", "0755")]:
            p = self.home / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("initial configuration\n")
            p.chmod(int(mode, 8))
            self.entries.append({
                "source": "$HOME/" + rel, "destination": "home/" + rel,
                "mode": mode, "kind": "file", "format": "text",
                "elevated_read": False, "restore": "user-review"})
        self.write_manifest()

    def write_manifest(self):
        (self.repo / "manifest/configs.json").write_bytes(
            d.json_bytes({"schema_version": 1, "files": self.entries}))

    def snapshot(self):
        return d.Snapshot(self.repo, self.home)

    def tree(self):
        return {str(p.relative_to(self.repo)): (p.read_bytes(), p.stat().st_mode)
                for p in self.repo.rglob("*") if p.is_file()}

    def test_dry_run_writes_nothing(self):
        before = self.tree()
        plan = self.snapshot().plan()
        self.assertEqual([p["action"] for p in plan], ["ADD", "ADD"])
        self.assertEqual(before, self.tree())
        self.assertFalse((self.repo / ".git/dotfiles-sync").exists())

    def storage_entry(self):
        return {"source": "$HOME/.config/storage/sata-fstab.conf",
                "destination": "home/.config/storage/sata-fstab.conf",
                "mode": "0644", "kind": "file", "format": "text",
                "elevated_read": False, "restore": "user-review",
                "reason": "Reviewed SATA-only recovery fragment; no personal inventory."}

    def test_storage_scope_remains_one_exact_regular_file(self):
        entry = self.storage_entry()
        d.validate_entry(entry, set())
        for changes in [
            {"source": "$HOME/.config/storage/other.conf"},
            {"source": "/etc/fstab", "destination": "system/etc/fstab"},
            {"destination": "home/.config/storage/../fstab"},
            {"restore": "manual-only"}, {"mode": "0600"},
        ]:
            with self.assertRaises(d.Refused):
                d.validate_entry(dict(entry, **changes), set())
        self.assertIn("fstrim.timer", d.SAFE_SERVICES)
        self.assertNotIn("unreviewed-storage.service", d.SAFE_SERVICES)

    def test_storage_fragment_normal_sync_and_credential_guard(self):
        source = self.home / ".config/storage/sata-fstab.conf"
        source.parent.mkdir(parents=True)
        source.write_text("# synthetic SATA-only recovery fixture\n")
        source.chmod(0o644)
        self.entries.append(self.storage_entry())
        self.write_manifest()
        before = self.tree()
        self.snapshot().plan()
        self.assertEqual(before, self.tree())
        self.snapshot().apply()
        self.assertEqual(source.read_bytes(),
                         (self.repo / self.entries[-1]["destination"]).read_bytes())
        source.write_text("api_" + "key = " + "A" * 32 + "\n")
        with self.assertRaisesRegex(d.Refused, "credential"):
            self.snapshot().plan()

    def test_storage_fragment_symlink_parent_is_refused(self):
        outside = self.base / "unapproved-storage"
        outside.mkdir()
        (outside / "sata-fstab.conf").write_text("# fixture\n")
        (self.home / ".config").mkdir()
        (self.home / ".config/storage").symlink_to(outside, target_is_directory=True)
        self.entries.append(self.storage_entry())
        self.write_manifest()
        with self.assertRaisesRegex(d.Refused, "Symlink"):
            self.snapshot().plan()

    def test_copy_mode_idempotency_and_live_sources_untouched(self):
        original = {e["source"]: (self.home / e["source"][6:]).read_bytes() for e in self.entries}
        self.snapshot().apply()
        for e in self.entries:
            src, dst = self.home / e["source"][6:], self.repo / e["destination"]
            self.assertEqual(src.read_bytes(), dst.read_bytes())
            self.assertEqual(dst.stat().st_mode & 0o777, int(e["mode"], 8))
            self.assertEqual(src.read_bytes(), original[e["source"]])
        before = self.tree()
        self.snapshot().apply()
        self.assertEqual(before, self.tree())

    def test_source_update_and_repository_rollback(self):
        self.snapshot().apply()
        (self.home / ".zshrc").write_text("new live configuration\n")
        self.snapshot().apply()
        s = self.snapshot()
        backup = s.internal / s.state["last_transaction"]
        before = self.tree()
        s.restore(backup)
        self.assertEqual(before, self.tree())
        s.restore(backup, apply=True)
        self.assertEqual((self.repo / "home/.zshrc").read_text(), "initial configuration\n")
        self.assertEqual((self.home / ".zshrc").read_text(), "new live configuration\n")
        s.restore(backup, apply=True)  # repeat recovery is safe

    def test_first_sync_rollback_removes_only_snapshot_files(self):
        self.snapshot().apply()
        s = self.snapshot()
        s.restore(s.internal / s.state["last_transaction"], apply=True)
        self.assertFalse((self.repo / "home").exists())
        self.assertTrue((self.repo / "README.md").exists())
        self.assertTrue((self.home / ".zshrc").exists())

    def test_missing_source_does_not_delete_snapshot(self):
        self.snapshot().apply()
        (self.home / ".zshrc").unlink()
        before = self.tree()
        with self.assertRaisesRegex(d.Refused, "Missing source"):
            self.snapshot().plan()
        self.assertEqual(before, self.tree())

    def test_source_symlink_escape(self):
        p = self.home / ".zshrc"
        p.unlink()
        p.symlink_to("/etc/passwd")
        with self.assertRaisesRegex(d.Refused, "Symlink"):
            self.snapshot().plan()

    def test_destination_parent_symlink(self):
        (self.repo / "home").symlink_to(self.home, target_is_directory=True)
        with self.assertRaisesRegex(d.Refused, "Symlink"):
            self.snapshot().plan()

    def test_parent_source_symlink(self):
        real = self.home / ".local"
        real.rename(self.home / "moved-local")
        real.symlink_to(self.home / "moved-local", target_is_directory=True)
        with self.assertRaisesRegex(d.Refused, "Symlink"):
            self.snapshot().plan()

    def test_path_traversal_and_unapproved_source(self):
        for source, dest in [("$HOME/.zshrc", "../escape"),
                             ("$HOME/.ssh/id_ed25519", "home/.ssh/id_ed25519")]:
            original = copy.deepcopy(self.entries)
            self.entries[0]["source"] = source
            self.entries[0]["destination"] = dest
            self.write_manifest()
            with self.assertRaises(d.Refused):
                self.snapshot()
            self.entries = original

    def test_binary_oversize_secret_and_fifo(self):
        p = self.home / ".zshrc"
        samples = [b"\x00binary", b"x" * (d.TEXT_LIMIT + 1),
                   ("api_" + "key = " + "A" * 32).encode(),
                   ("pass" + "word = short").encode(),
                   ('{"pass' + 'word": "short"}').encode(),
                   ("-----BEGIN OPENSSH " + "PRIVATE KEY-----").encode()]
        for sample in samples:
            p.write_bytes(sample)
            with self.assertRaises(d.Refused):
                self.snapshot().plan()
        p.unlink()
        os.mkfifo(p)
        with self.assertRaisesRegex(d.Refused, "regular file"):
            self.snapshot().plan()

    def test_source_mode_drift(self):
        (self.home / ".zshrc").chmod(0o600)
        with self.assertRaisesRegex(d.Refused, "mode drift"):
            self.snapshot().plan()

    def test_manual_repository_edit_and_deletion(self):
        self.snapshot().apply()
        dst = self.repo / "home/.zshrc"
        dst.write_text("manual repository edit\n")
        with self.assertRaisesRegex(d.Refused, "protected"):
            self.snapshot().plan()
        dst.unlink()
        with self.assertRaisesRegex(d.Refused, "protected"):
            self.snapshot().plan()

    def test_staged_edit_is_not_overwritten(self):
        self.snapshot().apply()
        subprocess.run(["git", "-C", str(self.repo), "add", "home/.zshrc"], check=True)
        (self.home / ".zshrc").write_text("changed live file\n")
        with self.assertRaisesRegex(d.Refused, "Staged"):
            self.snapshot().plan()

    def test_audit_catches_ignored_unallowlisted_and_index_only_secret(self):
        unknown = self.repo / ".env"
        unknown.write_text("not allowed\n")
        with self.assertRaisesRegex(d.Refused, "Unallowlisted"):
            self.snapshot().audit()
        unknown.unlink()
        self.snapshot().apply()
        dst = self.repo / "home/.zshrc"
        original = dst.read_bytes()
        dst.write_text("access_" + "token = " + "X" * 32 + "\n")
        subprocess.run(["git", "-C", str(self.repo), "add", "home/.zshrc"], check=True)
        dst.write_bytes(original)
        with self.assertRaisesRegex(d.Refused, "Suspected credential"):
            self.snapshot().audit()

    def test_rollback_refuses_later_edit(self):
        self.snapshot().apply()
        s = self.snapshot()
        (self.repo / "home/.zshrc").write_text("later edit\n")
        before = self.tree()
        with self.assertRaisesRegex(d.Refused, "Later edit"):
            s.restore(s.internal / s.state["last_transaction"], apply=True)
        self.assertEqual(before, self.tree())

    def test_automatic_rollback_after_partial_atomic_write(self):
        real = d.atomic
        failed = False

        def injected(path, data, mode=0o600):
            nonlocal failed
            real(path, data, mode)
            if path == self.repo / "home/.zshrc" and not failed:
                failed = True
                raise OSError("injected failure after replacement")

        with patch.object(d, "atomic", side_effect=injected):
            with self.assertRaises(OSError):
                self.snapshot().apply()
        self.assertFalse((self.repo / "home").exists())
        self.assertTrue((self.home / ".zshrc").exists())
        self.snapshot().plan()  # recovered journal permits rerun

    def test_rollback_failure_is_reported_and_rerun_blocked(self):
        real = d.atomic

        def fail_copy(path, data, mode=0o600):
            real(path, data, mode)
            if path == self.repo / "home/.zshrc":
                raise OSError("injected copy failure")

        with patch.object(d, "atomic", side_effect=fail_copy), \
             patch.object(d.Snapshot, "restore", side_effect=OSError("injected recovery failure")):
            with self.assertRaisesRegex(d.Refused, "both failed"):
                self.snapshot().apply()
        with self.assertRaisesRegex(d.Refused, "Interrupted transaction"):
            self.snapshot()

    def test_old_transaction_cannot_replace_newer_state(self):
        self.snapshot().apply()
        first = self.snapshot().state["last_transaction"]
        (self.home / ".zshrc").write_text("second\n")
        self.snapshot().apply()
        s = self.snapshot()
        with self.assertRaisesRegex(d.Refused, "latest"):
            s.restore(s.internal / first, apply=True)

    def test_image_rejected_unless_reviewed_hash_and_structure(self):
        with self.assertRaises(d.Refused):
            d.scan_image(b"not a PNG", "crimson-left.png")
        self.assertEqual(len(d.IMAGE_HASHES), 3)

    def test_recovery_entrypoint_handles_unfinished_journal(self):
        self.snapshot().apply()
        s = self.snapshot()
        backup = s.internal / s.state["last_transaction"]
        journal = json.loads((backup / "journal.json").read_bytes())
        journal["status"] = "installing"
        d.atomic(backup / "journal.json", d.json_bytes(journal))
        with self.assertRaisesRegex(d.Refused, "Interrupted transaction"):
            self.snapshot()
        args = SimpleNamespace(transaction=backup.name, apply=False)
        before = self.tree()
        d.with_recovery(self.repo, args)
        self.assertEqual(before, self.tree())
        args.apply = True
        d.with_recovery(self.repo, args)
        self.assertFalse((self.repo / "home").exists())
        self.snapshot().plan()

    def test_unexpected_content_blocks_rollback_before_any_changes(self):
        self.snapshot().apply()
        s = self.snapshot()
        (self.repo / "home/extra.txt").write_text("unrelated work\n")
        before = self.tree()
        with self.assertRaisesRegex(d.Refused, "Unexpected content"):
            s.restore(s.internal / s.state["last_transaction"], apply=True)
        self.assertEqual(before, self.tree())

    def test_corrupt_backup_refuses_before_restoring_anything(self):
        self.snapshot().apply()
        (self.home / ".zshrc").write_text("updated source\n")
        self.snapshot().apply()
        s = self.snapshot()
        backup = s.internal / s.state["last_transaction"]
        (backup / "0.original").write_text("corrupted backup\n")
        before = self.tree()
        with self.assertRaisesRegex(d.Refused, "Corrupted backup"):
            s.restore(backup, apply=True)
        self.assertEqual(before, self.tree())

    def test_index_symlink_refused_even_with_clean_working_file(self):
        dst = self.repo / "README.md"
        dst.unlink()
        dst.symlink_to("/etc/passwd")
        subprocess.run(["git", "-C", str(self.repo), "add", "README.md"], check=True)
        dst.unlink()
        dst.write_text("clean working file\n")
        with self.assertRaisesRegex(d.Refused, "index entry"):
            self.snapshot().audit()

    def make_gallery(self):
        def chunk(kind, data):
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        image = (b"\x89PNG\r\n\x1a\n" +
                 chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)) +
                 chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00")) +
                 chunk(b"IEND", b""))
        images = []
        for name in sorted(d.GALLERY_PATHS):
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(image)
            images.append({"path": name, "sha256": d.digest(image), "width": 1, "height": 1})
        (self.repo / "manifest/screenshots.json").write_bytes(
            d.json_bytes({"schema_version": 1, "files": images}))
        return images

    def test_reviewed_gallery_hashes_and_unknown_images(self):
        self.make_gallery()
        self.snapshot().audit()
        path = self.repo / "assets/screenshots/desktop.png"
        path.write_bytes(path.read_bytes() + b"changed")
        with self.assertRaises(d.Refused):
            self.snapshot().audit()

    def test_unregistered_gallery_binary_is_refused(self):
        path = self.repo / "assets/screenshots/desktop.png"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"unregistered image")
        with self.assertRaisesRegex(d.Refused, "Unallowlisted"):
            self.snapshot().audit()

    def test_gallery_registry_cannot_expand_image_scope(self):
        images = self.make_gallery()
        images[0]["path"] = "assets/screenshots/unreviewed.png"
        (self.repo / "manifest/screenshots.json").write_bytes(
            d.json_bytes({"schema_version": 1, "files": images}))
        with self.assertRaisesRegex(d.Refused, "Unapproved"):
            self.snapshot()

    def test_duplicate_mapping_and_unexpected_destination_refused(self):
        self.entries.append(copy.deepcopy(self.entries[0]))
        self.write_manifest()
        with self.assertRaisesRegex(d.Refused, "Duplicate"):
            self.snapshot()
        self.entries.pop()
        self.entries[0]["destination"] = "home/.config/other"
        self.write_manifest()
        with self.assertRaisesRegex(d.Refused, "mismatched"):
            self.snapshot()

    def test_mapping_reason_and_category_policy_validation(self):
        original = copy.deepcopy(self.entries)
        for changes in [{"reason": ""}, {"reason": "x" * 501},
                        {"reason": "api_" + "key = " + "A" * 20},
                        {"format": "png"}, {"restore": "manual-only"},
                        {"elevated_read": True}, {"unknown_field": "unexpected"}]:
            self.entries = copy.deepcopy(original)
            self.entries[0].update(changes)
            self.write_manifest()
            with self.assertRaises(d.Refused):
                self.snapshot()
        self.entries = original
        self.entries[0]["reason"] = "Reviewed shell configuration; no project data."
        self.write_manifest()
        self.snapshot().plan()

    def test_missing_source_has_actionable_nondestructive_guidance(self):
        (self.home / ".zshrc").unlink()
        with self.assertRaisesRegex(d.Refused, "config-change-review.md") as error:
            self.snapshot().plan()
        self.assertIn("no automatic prune", str(error.exception))

    def test_diff_preview_uses_requested_checkout_and_makes_no_writes(self):
        self.snapshot().apply()
        (self.home / ".zshrc").write_text("updated sandbox source\n")
        snapshot = self.snapshot()
        before = self.tree()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            d.show_plan(snapshot.plan(), diff=True, root=self.repo)
        self.assertIn("-initial configuration", output.getvalue())
        self.assertIn("+updated sandbox source", output.getvalue())
        self.assertEqual(before, self.tree())

    def test_history_cannot_extend_live_image_approval(self):
        self.make_gallery()
        image = (self.repo / "assets/screenshots/desktop.png").read_bytes()
        old = d.digest(image)
        with patch.dict(d.IMAGE_HISTORY, {"crimson-left.png": [old]}):
            # Historical snapshot accepted, but never a newly approved live source.
            d.scan_snapshot_image(image, "crimson-left.png")
            with self.assertRaises(d.Refused):
                d.scan_image(image, "crimson-left.png")
            with self.assertRaises(d.Refused):
                d.scan_snapshot_image(image, "unreviewed.png")

    def test_explicit_image_reapproval_can_use_normal_transaction_and_rollback(self):
        self.make_gallery()
        old = (self.repo / "assets/screenshots/desktop.png").read_bytes()
        # A distinct valid PNG with the same pixels but another zlib encoding.
        def chunk(kind, data):
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        new = (old[:33] + chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00", level=0)) +
               chunk(b"IEND", b""))
        self.assertNotEqual(d.digest(old), d.digest(new))
        rel = ".local/share/wallpapers/crimson/crimson-left.png"
        source = self.home / rel
        source.parent.mkdir(parents=True)
        source.write_bytes(old)
        self.entries.append({"source": "$HOME/" + rel, "destination": "home/" + rel,
                             "kind": "file", "format": "png", "mode": "0644",
                             "elevated_read": False, "restore": "user-review",
                             "reason": "Visually reviewed wallpaper fixture."})
        self.write_manifest()
        with patch.dict(d.IMAGE_HASHES, {"crimson-left.png": d.digest(old)}):
            self.snapshot().apply()
        source.write_bytes(new)
        with self.assertRaises(d.Refused):
            self.snapshot().plan()  # Original behavior: no silent pin refresh.
        with patch.dict(d.IMAGE_HASHES, {"crimson-left.png": d.digest(new)}), \
             patch.dict(d.IMAGE_HISTORY, {"crimson-left.png": [d.digest(old)]}):
            before = self.tree()
            self.snapshot().plan()
            self.assertEqual(before, self.tree())
            self.snapshot().apply()
            self.assertEqual((self.repo / ("home/" + rel)).read_bytes(), new)
            s = self.snapshot()
            s.restore(s.internal / s.state["last_transaction"], apply=True)
            self.assertEqual((self.repo / ("home/" + rel)).read_bytes(), old)
            self.assertEqual(source.read_bytes(), new)

    def test_malformed_image_history_fails_closed(self):
        for value in [["invalid"], [{"not": "a hash"}], ["a" * 64, "a" * 64]]:
            with patch.dict(d.IMAGE_HISTORY, {"crimson-left.png": value}):
                with self.assertRaises(d.Refused):
                    self.snapshot()

    def test_partial_existing_update_failure_restores_original_copies_and_state(self):
        self.snapshot().apply()
        s = self.snapshot()
        previous = s.load_state()
        for rel in [".zshrc", ".local/bin/powermenu"]:
            (self.home / rel).write_text("updated source\n")
        real = d.atomic
        failed = False

        def injected(path, data, mode=0o600):
            nonlocal failed
            real(path, data, mode)
            if path == self.repo / "home/.local/bin/powermenu" and not failed:
                failed = True
                raise OSError("injected existing-copy failure")

        with patch.object(d, "atomic", side_effect=injected):
            with self.assertRaises(OSError):
                self.snapshot().apply()
        self.assertEqual(self.snapshot().load_state(), previous)
        for rel in [".zshrc", ".local/bin/powermenu"]:
            self.assertEqual((self.repo / "home" / rel).read_text(), "initial configuration\n")
            self.assertEqual((self.home / rel).read_text(), "updated source\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
