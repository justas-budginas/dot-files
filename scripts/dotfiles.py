"""Standard-library-only, allowlisted snapshot tools. No live-config write API."""
import argparse
from contextlib import contextmanager
import difflib
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import subprocess
import sys
import tempfile
import uuid
import zlib

TEXT_LIMIT = 128 * 1024
IMAGE_LIMIT = 8 * 1024 * 1024
APPROVED_HOME = {
    ".config/hypr/" + n for n in
    ("hyprland.lua", "hypridle.conf", "hyprlock.conf", "hyprpaper.conf")
} | {
    ".config/waybar/config.jsonc", ".config/waybar/style.css",
    ".config/waybar/scripts/gpu.py", ".config/rofi/config.rasi",
    ".config/rofi/crimson.rasi", ".config/rofi/launcher.rasi",
    ".config/rofi/powermenu.rasi", ".config/kitty/kitty.conf",
    ".config/kitty/colors.conf", ".config/mako/config",
    ".config/gtk-3.0/settings.ini", ".config/gtk-4.0/settings.ini",
    ".config/starship.toml", ".zshrc", ".local/bin/powermenu",
    ".local/share/wallpapers/crimson/crimson-left.png",
    ".local/share/wallpapers/crimson/crimson-right.png",
}
APPROVED_SYSTEM = {
    "/etc/greetd/config.toml", "/etc/nwg-hello/hyprland.lua",
    "/etc/nwg-hello/nwg-hello.json", "/etc/nwg-hello/nwg-hello.css",
    "/etc/systemd/zram-generator.conf",
    "/etc/systemd/system/snapper-timeline.timer.d/override.conf",
    "/etc/ssh/sshd_config.d/10-gaming-pc.conf", "/etc/pacman.conf",
    "/etc/mkinitcpio.conf", "/etc/ufw/ufw.conf",
    "/usr/local/share/backgrounds/crimson-greeter/crimson-shared.png",
}
# Approved deployed PNGs only. A changed asset requires a new review/hash approval.
IMAGE_HASHES = {
    "crimson-left.png": "b25dcb496b78f0f8ce283ed2a550e59381254ebec79fa55e5b40ddfe30e32aa4",
    "crimson-right.png": "111186ee08f0d9f38491a47a34f883e381dcb32c0303bf12184a6e4779456f7c",
    "crimson-shared.png": "c74579c525cf56ad255fb6724775514b922857b1958e1787ae64e76ab2aeaca7",
}
# Optional, individually reviewed prior hashes for repository/index/rollback copies.
# Live sources must STILL match IMAGE_HASHES. Never refreshed by a command.
IMAGE_HISTORY = {}
GALLERY_PATHS = {
    "assets/screenshots/desktop.png", "assets/screenshots/lockscreen.png",
    "assets/screenshots/greeter.png",
}
TOOLS = ("sync-from-system", "audit-repo", "verify-manifest",
         "rollback-sync", "propose-inventories", "dotfiles.py",
         "inspect-recovery-policy", "recovery_policy.py")
INFRA = {
    "README.md", ".gitignore", ".gitattributes", "manifest/configs.json",
    "docs/setup-notes.md", "docs/recovery-notes.md", "docs/bootstrap-roadmap.md",
    "docs/security.md", "docs/verification.md", "tests/test_workflow.py",
    "manifest/packages-native-explicit.txt", "manifest/packages-foreign.txt",
    "manifest/services.json", "manifest/appearance.json", "manifest/screenshots.json",
    "docs/screenshots.md",
    "docs/system-recovery-inventory.md", "docs/service-recovery-map.md",
    "docs/config-change-review.md", "tests/test_recovery.py",
} | {"scripts/" + n for n in TOOLS}
LLM = re.compile(r"llm|ollama|llama|vllm|open.?webui|litellm|kobold|cuda|rocm|pytorch|tensorflow", re.I)
SAFE_SERVICES = {
    "getty@.service", "greetd.service", "grub-btrfsd.service",
    "NetworkManager-dispatcher.service", "NetworkManager-wait-online.service",
    "NetworkManager.service", "sshd.service", "swayosd-libinput-backend.service",
    "systemd-timesyncd.service", "ufw.service", "systemd-userdbd.socket",
    "remote-fs.target", "snapper-cleanup.timer", "snapper-timeline.timer",
    "wireplumber.service", "xdg-user-dirs.service", "gnome-keyring-daemon.socket",
    "p11-kit-server.socket", "pipewire-pulse.socket", "pipewire.socket",
}


class Refused(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise Refused(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def relative(name):
    require(isinstance(name, str) and bool(name), "Empty/non-string path")
    p = PurePosixPath(name)
    require(not p.is_absolute() and ".." not in p.parts and str(p) == name
            and "\\" not in name, f"Unsafe relative path: {name}")
    return p


def safe(path):
    require(path.is_absolute(), "Expected absolute path")
    for part in [*reversed(path.parents), path]:
        require(not part.is_symlink(), f"Symlink refused: {part}")


def read_file(path, limit=TEXT_LIMIT):
    safe(path)
    # NONBLOCK avoids waiting on a FIFO before the regular-file check.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode), f"Not a regular file: {path}")
        require(before.st_size <= limit, f"Oversized file: {path}")
        data = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    safe(path)
    current = path.stat()
    fields = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_mode)
    require(fields(before) == fields(after) == fields(current)
            and len(data) <= limit, f"File changed while reading: {path}")
    return data, stat.S_IMODE(before.st_mode)


def record(data, mode):
    return {"sha256": digest(data), "mode": mode}


def existing(path, limit=IMAGE_LIMIT):
    safe(path)
    if not path.exists():
        return None
    data, mode = read_file(path, limit)
    return record(data, mode)


def scan_text(data, name):
    require(len(data) <= TEXT_LIMIT, f"Oversized text: {name}")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise Refused(f"Unexpected binary/non-UTF8 file: {name}") from None
    require(not any(ord(c) < 32 and c not in "\t\n\r" for c in text),
            f"Unexpected binary/control characters: {name}")
    patterns = [
        r"-----BEGIN (?:OPENSSH |RSA |EC |DSA |ENCRYPTED )?PRIVATE KEY-----",
        r"\bgh[pousr]_[A-Za-z0-9]{20,}",
        r"\bgithub_pat_[A-Za-z0-9_]{20,}",
        r"\bsk-[A-Za-z0-9_-]{24,}",
        r"\bAKIA[A-Z0-9]{16}\b",
        r"-----BEGIN PGP " r"PRIVATE KEY BLOCK-----",
        r"://[^\s/:]+:[^\s/@]+@",
        r"(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|"
        r"passphrase|token|secret|aws_secret_access_key)"
        r"[\"']?\s*[=:]\s*[\"']?[A-Za-z0-9_./+-]+",
        r"(?i)\bauthorization\s*[:=]\s*[\"']?(?:bearer|basic)\s+\S+",
    ]
    require(not any(re.search(p, text) for p in patterns),
            f"Suspected credential in {name}; value withheld. Review manually.")
    return text


def scan_image(data, name, approved_hash=None):
    require(len(data) <= IMAGE_LIMIT and data.startswith(b"\x89PNG\r\n\x1a\n"),
            f"Unexpected/oversized image: {name}")
    pos, chunks = 8, []
    while pos < len(data):
        require(pos + 12 <= len(data), f"Truncated PNG: {name}")
        size = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        end = pos + 12 + size
        require(end <= len(data) and kind in (b"IHDR", b"IDAT", b"IEND"),
                f"Unapproved PNG chunk/metadata: {name}")
        content = data[pos + 4:end - 4]
        require(zlib.crc32(content) == struct.unpack(">I", data[end - 4:end])[0],
                f"PNG checksum mismatch: {name}")
        chunks.append(kind)
        pos = end
    require(chunks and chunks[0] == b"IHDR" and chunks[-1] == b"IEND",
            f"Incomplete PNG: {name}")
    require(digest(data) == (approved_hash or IMAGE_HASHES.get(Path(name).name)),
            f"Image changed/unapproved; review its new hash: {name}")


def scan_snapshot_image(data, name):
    """Only explicit current/prior pins; never extends live-source approval."""
    basename = Path(name).name
    approved = {IMAGE_HASHES.get(basename)} | set(IMAGE_HISTORY.get(basename, []))
    require(basename in IMAGE_HASHES and digest(data) in approved,
            f"Snapshot image is not individually approved: {name}")
    scan_image(data, name, digest(data))


def validate_entry(e, seen):
    require(isinstance(e, dict), "Mapping must be an object")
    required = {"source", "destination", "kind", "format", "mode", "elevated_read", "restore"}
    require(required <= e.keys() and e.keys() <= required | {"reason"},
            "Missing/unknown mapping fields")
    source, destination = e["source"], e["destination"]
    require(isinstance(source, str), "Source must be a string")
    relative(destination)
    if source.startswith("$HOME/"):
        rel = source[len("$HOME/"):]
        require(rel in APPROVED_HOME, f"Source outside approved home scope: {source}")
        expected, policy = "home/" + rel, "user-review"
    else:
        require(source in APPROVED_SYSTEM, f"Unapproved system source: {source}")
        expected, policy = "system" + source, "manual-only"
    require(destination == expected and destination not in seen,
            f"Duplicate/mismatched destination: {destination}")
    require(e["kind"] == "file" and e["elevated_read"] is False,
            "Only nonprivileged regular-file snapshots are supported")
    require(e["format"] in ("text", "png") and e["mode"] in ("0644", "0755"),
            "Unexpected format/mode")
    require((e["format"] == "png") == source.endswith(".png"),
            "Image/text category does not match the approved source")
    require(e["restore"] == policy, "Restore policy does not match source scope")
    if "reason" in e:
        require(isinstance(e["reason"], str) and 0 < len(e["reason"].strip()) <= 500,
                "Reason must be a nonempty, bounded review description")
        scan_text(e["reason"].encode(), "mapping reason")
    seen.add(destination)


def git(root, *args, binary=False):
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    result = subprocess.run(["git", "-C", str(root), *args], env=env,
                            capture_output=True, timeout=30)
    require(result.returncode == 0, f"Git command failed: {args[0]}")
    return result.stdout if binary else result.stdout.decode()


def atomic(path, data, mode=0o600):
    safe(path)
    fd, name = tempfile.mkstemp(prefix=".dotfiles-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fchmod(stream.fileno(), mode)
            os.fsync(stream.fileno())
        safe(path)
        os.replace(temporary, path)
        sync_dir(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


class Snapshot:
    def __init__(self, root, home=None, recovering=False):
        self.root = Path(root).absolute()
        self.home = Path(home or Path.home()).absolute()
        safe(self.root)
        require(git(self.root, "rev-parse", "--show-toplevel").strip() == str(self.root),
                "Run in the repository root")
        self.gitdir = self.root / ".git"
        safe(self.gitdir)
        require(self.gitdir.is_dir(), "Only ordinary .git-directory checkouts supported")
        self.internal = self.gitdir / "dotfiles-sync"
        safe(self.internal)
        self.state_path = self.internal / "state.json"
        raw, _ = read_file(self.root / "manifest/configs.json")
        self.manifest_hash = digest(raw)
        manifest = json.loads(raw)
        require(manifest["schema_version"] == 1, "Unsupported manifest schema")
        self.entries = manifest["files"]
        require(isinstance(self.entries, list) and self.entries, "Empty manifest")
        seen = set()
        for e in self.entries:
            validate_entry(e, seen)
        require(set(IMAGE_HISTORY) <= IMAGE_HASHES.keys(), "Unknown historical image path")
        for hashes in IMAGE_HISTORY.values():
            require(isinstance(hashes, list)
                    and all(isinstance(h, str) and re.fullmatch(r"[0-9a-f]{64}", h)
                            for h in hashes)
                    and len(hashes) == len(set(hashes)),
                    "Invalid/duplicate historical image pin")
        self.gallery = {}
        gallery_path = self.root / "manifest/screenshots.json"
        safe(gallery_path)
        if gallery_path.exists():
            gallery = json.loads(read_file(gallery_path)[0])
            require(gallery["schema_version"] == 1, "Unknown screenshot registry schema")
            require(len(gallery["files"]) == len(GALLERY_PATHS), "Unexpected screenshot count")
            for image in gallery["files"]:
                name = image["path"]
                require(name in GALLERY_PATHS and name not in self.gallery,
                        "Unapproved/duplicate screenshot path")
                require(re.fullmatch(r"[0-9a-f]{64}", image["sha256"]), "Invalid image hash")
                require(type(image["width"]) is int and type(image["height"]) is int
                        and 0 < image["width"] <= 2560 and 0 < image["height"] <= 1600,
                        "Unexpected screenshot dimensions")
                self.gallery[name] = image
        self.allowed = INFRA | seen | set(self.gallery)
        self.state = self.load_state()
        if self.internal.exists():
            for transaction in self.internal.glob("transaction-*"):
                safe(transaction)
                journal = transaction / "journal.json"
                require(journal.is_file(), f"Incomplete backup needs inspection: {transaction}")
                status = json.loads(read_file(journal, 2 * TEXT_LIMIT)[0])["status"]
                require(status in ("preparing", "installing", "committed", "rolled-back"),
                        f"Unknown transaction status: {transaction}")
                require(recovering or status in ("committed", "rolled-back"),
                        f"Interrupted transaction: {transaction}; run rollback-sync")

    def load_state(self):
        if not self.state_path.exists():
            return {"files": {}, "last_transaction": None}
        return json.loads(read_file(self.state_path, 2 * TEXT_LIMIT)[0])

    def source(self, entry):
        s = entry["source"]
        return self.home / s[len("$HOME/"):] if s.startswith("$HOME/") else Path(s)

    def content(self, entry, path):
        data, mode = read_file(path, IMAGE_LIMIT if entry["format"] == "png" else TEXT_LIMIT)
        require(mode == int(entry["mode"], 8), f"Source/file mode drift: {path}")
        if entry["format"] == "png":
            scan_image(data, entry["destination"])
        else:
            scan_text(data, entry["destination"])
        return data, mode

    def audit(self):
        by_name = {e["destination"]: e for e in self.entries}

        def check(name, data, mode):
            require(name in self.allowed, f"Unallowlisted repository file: {name}")
            require(mode in (0o644, 0o755), f"Unexpected repository mode: {name}")
            if name in self.gallery:
                image = self.gallery[name]
                require(mode == 0o644, "Screenshots must not be executable")
                scan_image(data, name, image["sha256"])
                require(struct.unpack(">II", data[16:24]) ==
                        (image["width"], image["height"]), "Screenshot dimensions changed")
                return
            if name in by_name:
                e = by_name[name]
                require(mode == int(e["mode"], 8), f"Snapshot mode drift: {name}")
                if e["format"] == "png":
                    scan_snapshot_image(data, name)
                    return
            scan_text(data, name)

        for name in self.gallery:
            require((self.root / name).is_file(), f"Missing reviewed screenshot: {name}")
        # Includes ignored/untracked files; ignore rules are not a security boundary.
        for folder, dirs, files in os.walk(self.root, followlinks=False):
            base = Path(folder)
            if base == self.root:
                dirs[:] = [d for d in dirs if d != ".git"]
            for name in dirs:
                safe(base / name)
            for name in files:
                p = base / name
                rel = p.relative_to(self.root).as_posix()
                require(rel in self.allowed, f"Unallowlisted repository file: {rel}")
                data, mode = read_file(p, IMAGE_LIMIT if rel.endswith(".png") else TEXT_LIMIT)
                check(rel, data, mode)
        # Inspect staged content, not only the working tree. No index modifications.
        raw = git(self.root, "ls-files", "--stage", "-z", binary=True)
        for item in raw.split(b"\0"):
            if not item:
                continue
            header, name_bytes = item.split(b"\t", 1)
            mode_string, oid, stage = header.decode().split()
            name = name_bytes.decode()
            relative(name)
            require(stage == "0" and mode_string in ("100644", "100755"),
                    f"Symlink/submodule/unmerged index entry: {name}")
            require(name in self.allowed, f"Unallowlisted indexed file: {name}")
            size = int(git(self.root, "cat-file", "-s", oid).strip())
            require(size <= (IMAGE_LIMIT if name.endswith(".png") else TEXT_LIMIT),
                    f"Oversized indexed file: {name}")
            check(name, git(self.root, "cat-file", "blob", oid, binary=True),
                  int(mode_string, 8) & 0o777)

    def plan(self):
        self.audit()
        staged = set(git(self.root, "diff", "--cached", "--name-only", "-z").split("\0"))
        plan = []
        for e in self.entries:
            try:
                data, mode = self.content(e, self.source(e))
            except FileNotFoundError:
                raise Refused(f"Missing source: {e['source']}; no repository deletion performed. "
                              "Preserve its copy; review any rename/removal using "
                              "docs/config-change-review.md (no automatic prune).") from None
            name = e["destination"]
            target = self.root / name
            current = existing(target)
            new = record(data, mode)
            previous = self.state["files"].get(name)
            if previous is not None:
                require(current in (previous, new), f"Repository edit/deletion protected: {name}")
            if current is not None and current != new:
                require(current == previous, f"Repository edit/unmanaged copy protected: {name}")
            if current != new:
                require(name not in staged, f"Staged repository edit protected: {name}")
            action = "ADD" if current is None else "UPDATE" if current != new else "UNCHANGED"
            plan.append({"entry": e, "data": data, "mode": mode, "before": current,
                         "after": new, "action": action})
        return plan

    @contextmanager
    def lock(self):
        require(os.geteuid() != 0, "Never run snapshot tools as root")
        safe(self.internal)
        self.internal.mkdir(mode=0o700, exist_ok=True)
        info = self.internal.stat()
        require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700,
                "Snapshot metadata directory must be user-owned mode 0700")
        fd = os.open(self.internal / "lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(fd)
            require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                    and not info.st_mode & 0o022, "Unsafe snapshot lock")
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        finally:
            os.close(fd)

    def apply(self):
        with self.lock():
            self.state = self.load_state()
            plan = self.plan()
            updates = [p for p in plan if p["action"] != "UNCHANGED"]
            new_files = {p["entry"]["destination"]: p["after"] for p in plan}
            if not updates and new_files == self.state["files"]:
                print("No changes (idempotent); no transaction/state rewrite.")
                return
            backup = self.internal / ("transaction-" + uuid.uuid4().hex)
            backup.mkdir(mode=0o700)
            journal = {"status": "preparing", "previous_state": self.state,
                       "manifest_sha256": self.manifest_hash, "files": [], "created_dirs": []}
            atomic(backup / "journal.json", json_bytes(journal))
            for i, p in enumerate(updates):
                name = p["entry"]["destination"]
                if p["before"] is not None:
                    old, mode = read_file(self.root / name, IMAGE_LIMIT)
                    require(record(old, mode) == p["before"], f"Repository changed: {name}")
                    atomic(backup / f"{i}.original", old, mode)
                journal["files"].append({"destination": name, "before": p["before"],
                                         "after": p["after"], "backup": f"{i}.original"})
            created = set()
            for p in updates:
                parent = (self.root / p["entry"]["destination"]).parent
                while parent != self.root and not parent.exists():
                    safe(parent)
                    created.add(parent.relative_to(self.root).as_posix())
                    parent = parent.parent
            journal["created_dirs"] = sorted(created, key=lambda n: (n.count("/"), n))
            journal["status"] = "installing"
            atomic(backup / "journal.json", json_bytes(journal))
            sync_dir(self.internal)
            try:
                for name in journal["created_dirs"]:
                    safe(self.root / name)
                    (self.root / name).mkdir(mode=0o755)
                    sync_dir((self.root / name).parent)
                for p in updates:
                    name = p["entry"]["destination"]
                    require(existing(self.root / name) == p["before"], f"Repository changed: {name}")
                    data, mode = self.content(p["entry"], self.source(p["entry"]))
                    require(record(data, mode) == p["after"], f"Source changed: {name}")
                    atomic(self.root / name, data, mode)
                for p in plan:
                    require(existing(self.root / p["entry"]["destination"]) == p["after"],
                            "Post-copy verification mismatch")
                self.audit()
                atomic(self.state_path, json_bytes({"files": new_files,
                                                    "last_transaction": backup.name}))
                journal["status"] = "committed"
                atomic(backup / "journal.json", json_bytes(journal))
            except BaseException as install_error:
                print(f"SNAPSHOT FAILED: {install_error}", file=sys.stderr)
                try:
                    self.restore(backup, apply=True)
                except BaseException as rollback_error:
                    print(f"ROLLBACK ALSO FAILED: {rollback_error}\nInspect {backup}", file=sys.stderr)
                    raise Refused("Snapshot and rollback both failed; backup retained") from install_error
                raise
            print(f"Copied {len(updates)} files; originals/state retained in {backup}")

    def restore(self, backup, apply=False):
        safe(backup)
        require(backup.parent == self.internal and
                re.fullmatch(r"transaction-[0-9a-f]{32}", backup.name),
                "Invalid repository backup path")
        journal = json.loads(read_file(backup / "journal.json", 2 * TEXT_LIMIT)[0])
        current_state = self.load_state()
        require(current_state == journal["previous_state"]
                or current_state.get("last_transaction") == backup.name,
                "Not the latest transaction; refusing to overwrite newer sync state")
        if journal["status"] == "committed":
            require(current_state.get("last_transaction") == backup.name,
                    "Only the latest committed sync can be rolled back")
        if journal["status"] == "rolled-back":
            require(current_state == journal["previous_state"], "Recovery state changed")
        scope = {e["destination"] for e in self.entries}
        for f in journal["files"]:
            name = f["destination"]
            relative(name)
            require(name in scope, f"Recovery scope not in current manifest: {name}")
            require(re.fullmatch(r"[0-9]+\.original", f["backup"]), "Unsafe backup name")
            current = existing(self.root / name)
            require(current in (f["before"], f["after"]), f"Later edit blocks rollback: {name}")
            if f["before"] is not None:
                require(existing(backup / f["backup"]) == f["before"], "Corrupted backup")
        created = journal["created_dirs"]
        for name in created:
            relative(name)
            require(any(n.startswith(name + "/") for n in scope), "Unsafe recovery directory")
            safe(self.root / name)
            directory = self.root / name
            if directory.exists():
                require(directory.is_dir(), "Recovery directory replaced")
                allowed_children = set(created) | {f["destination"] for f in journal["files"]}
                require(all(p.relative_to(self.root).as_posix() in allowed_children
                            for p in directory.iterdir()),
                        f"Unexpected content in recovery directory: {name}")
        print(f"{'Restore' if apply else 'Would restore'} {len(journal['files'])} repository files: {backup.name}")
        if not apply:
            return
        for f in reversed(journal["files"]):
            path = self.root / f["destination"]
            if existing(path) == f["before"]:
                continue
            if f["before"] is None:
                path.unlink()
                sync_dir(path.parent)
            else:
                data, mode = read_file(backup / f["backup"], IMAGE_LIMIT)
                atomic(path, data, mode)
            require(existing(path) == f["before"], "Restore verification mismatch")
        for name in reversed(created):
            path = self.root / name
            if path.exists():
                path.rmdir()  # Empty-only; never recursive deletion.
        atomic(self.state_path, json_bytes(journal["previous_state"]))
        journal["status"] = "rolled-back"
        atomic(backup / "journal.json", json_bytes(journal))


def show_plan(plan, diff=False, root=None):
    for p in plan:
        e = p["entry"]
        print(f"{p['action']:9} {e['source']} -> {e['destination']} "
              f"mode={p['mode']:04o} sha256={p['after']['sha256']}")
        if diff and p["action"] != "UNCHANGED" and e["format"] == "text":
            target = (Path(root) if root is not None else
                      Path(__file__).absolute().parent.parent) / e["destination"]
            old = scan_text(read_file(target)[0], e["destination"]) if p["before"] else ""
            print("".join(difflib.unified_diff(old.splitlines(True),
                  p["data"].decode().splitlines(True), fromfile="repo/" + e["destination"],
                  tofile="live/" + e["destination"])), end="")
    print(f"{sum(p['action'] != 'UNCHANGED' for p in plan)} proposed copies; "
          f"{sum(len(p['data']) for p in plan)} source bytes. No automatic prune.")


def inventories():
    proposals = {}
    for name, flag in [("packages-native-explicit.txt", "-Qqen"), ("packages-foreign.txt", "-Qqm")]:
        r = subprocess.run(["pacman", flag], capture_output=True, text=True, timeout=30)
        require(r.returncode == 0, "Package inventory command failed")
        names = sorted(set(r.stdout.splitlines()))
        require(all(re.fullmatch(r"[A-Za-z0-9@._+:-]+", n) for n in names), "Unsafe package name")
        require(not any(LLM.search(n) for n in names),
                "LLM/compute-related package detected; curate separately before export")
        proposals[name] = "\n".join(names) + "\n"
    services = {}
    for scope, args in [("system", []), ("user", ["--user"])]:
        r = subprocess.run(["systemctl", *args, "list-unit-files", "--state=enabled",
                            "--no-legend", "--no-pager"], capture_output=True, text=True, timeout=30)
        require(r.returncode == 0, "Service inventory failed")
        names = sorted({line.split()[0] for line in r.stdout.splitlines() if line.strip()})
        require(set(names) <= SAFE_SERVICES, "New/unreviewed service; curate before export")
        services[scope] = names
    proposals["services.json"] = json_bytes(services).decode()
    appearance = {}
    for key in ("color-scheme", "gtk-theme", "icon-theme", "cursor-theme",
                "cursor-size", "font-name", "monospace-font-name"):
        r = subprocess.run(["gsettings", "get", "org.gnome.desktop.interface", key],
                           capture_output=True, text=True, timeout=15)
        require(r.returncode == 0, f"Appearance query failed: {key}")
        appearance[key] = r.stdout.strip()
    proposals["appearance.json"] = json_bytes(appearance).decode()
    for name, text in proposals.items():
        scan_text(text.encode(), name)
    for name, text in proposals.items():
        print(f"--- PROPOSAL manifest/{name} (not saved) ---\n{text}", end="")


def main(command):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true", help="read-only (default)")
    modes.add_argument("--apply", action="store_true", help="explicit repository-only writes")
    parser.add_argument("--diff", action="store_true", help="show scanned text diffs with sync/verify")
    parser.add_argument("--transaction", help="rollback transaction directory basename")
    args = parser.parse_args()
    try:
        require(os.geteuid() != 0, "Do not run these tools with sudo/root")
        require(not args.apply or command in ("sync", "rollback"), "This command is read-only")
        require(not args.diff or command in ("sync", "verify"), "--diff is for sync/verify")
        require(not args.transaction or command == "rollback", "--transaction is for rollback")
        root = Path(__file__).absolute().parent.parent
        if command == "inventories":
            inventories()
            return
        if command == "rollback":
            # Recovery must remain available when an unfinished journal blocks normal sync.
            with_recovery(root, args)
            return
        snapshot = Snapshot(root)
        if command == "audit":
            snapshot.audit()
            print("PASS: working tree (including ignored files) and index passed scoped audit.")
        elif args.apply:
            snapshot.apply()
        else:
            show_plan(snapshot.plan(), args.diff, snapshot.root)
            print("DRY RUN: no files copied, no state/backups created, no Git index changes.")
    except (OSError, ValueError, KeyError, Refused, subprocess.SubprocessError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        sys.exit(1)


def with_recovery(root, args):
    # The same validator, permitting only known unfinished transaction statuses.
    snapshot = Snapshot(root, recovering=True)
    name = args.transaction or snapshot.state.get("last_transaction")
    require(name and re.fullmatch(r"transaction-[0-9a-f]{32}", name),
            "Supply --transaction transaction-HEX from the interrupted-transaction diagnostic")
    backup = snapshot.internal / name
    if args.apply:
        with snapshot.lock():
            snapshot.restore(backup, apply=True)
    else:
        snapshot.restore(backup)
