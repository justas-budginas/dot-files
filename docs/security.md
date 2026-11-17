# Security boundary

The reviewed source→destination manifest is the primary boundary, backed by a
fixed approved source scope in `scripts/dotfiles.py`. No glob/directory import
is accepted. Source paths and destination correspondence are validated, including
path traversal, symlink parents, regular-file type, size, mode and content.

Text is UTF-8, limited to 128 KiB per file. Approved images are limited to 8 MiB
each, require PNG signature/checksummed IHDR/IDAT/IEND chunks and exact reviewed
hashes. Arbitrary binary files and PNG metadata are not imported.

Documentation additionally permits exactly three visually reviewed gallery PNGs
registered in `manifest/screenshots.json`. Their paths, hashes, dimensions, PNG
chunks and non-executable modes are checked. No image directory is recursively
trusted; see `docs/screenshots.md`. A content hash cannot detect private pixels:
visual privacy review is mandatory before registering any replacement screenshot.

`audit-repo` scans all working-tree files, including ignored/untracked files,
and every blob in the current Git index. Symlinks, submodules, unmerged entries
and unallowlisted filenames fail. A staged secret cannot hide behind a cleaned
working copy. `.gitignore` is defense in depth, not permission to store secrets
locally in this checkout. Do not create a `local-only/` secret stash here.

Credential-pattern checks include recognizable private-key blocks, common token
formats, credential-bearing URLs and suspicious credential assignments. Errors
name files without printing matched secrets. This is **not** a complete secret
detector, encryption tool or defense against hostile concurrent filesystem edits.
Manual review remains mandatory. Do not run tools while another program edits
the manifest/snapshots or while performing another Git operation.

## Never imported

- SSH client configuration, private/public keys, known_hosts, authorized_keys.
- GNOME Keyring/password-store databases, authentication cookies or credentials.
- Browser/Discord profiles, tokens, `.env` files, histories, logs and caches.
- NetworkManager connection profiles, WireGuard keys/configuration.
- `/etc/shadow`, machine-id, SSH host keys, PAM configuration.
- OpenCode settings/tokens/data, personal repositories, datasets, LLM files.
- Raw firewall rules, full fstab/GRUB machine identifiers, disk/snapshot content.
  The explicitly approved SATA-only UUID exception is described below.
- Existing phase backups, test screenshots, runtime sockets, package defaults.

Inventories contain reviewed package/service names and selected appearance
values only. LLM/compute-related package names or new unreviewed service names
stop inventory proposals for separate curation; no LLM project is traversed.

Phase A added three explicitly allowed documentation paths and a dedicated
read-only policy inspector with fixture tests. It retained 32 mappings; no raw
firewall, Snapper, GRUB, fstab or network profile was added.
The inspector is not called by sync and has no write/apply mode. Its optional
privileged invocation requires exact approval and the system authorization dialog.
It exports only selected root-policy keys and sanitized summaries, never raw
command stderr, addresses, connection identities or SecureOn values.

Live wallpaper pins remain strict. Explicit, individually reviewed prior pins
can apply to repo/index/rollback copies only; default history is empty and no
tool edits either approval list. Mapping/image changes follow the paired-diff
procedure in `config-change-review.md`.

## Narrow storage recovery exception, 2026-11-17

The user explicitly approved publishing the Crucial and Apacer filesystem UUIDs,
mountpoints and storage configuration. The 33rd exact mapping is
`$HOME/.config/storage/sata-fstab.conf`, a reviewed SATA-only recovery fragment.
It is not the full live fstab and is not consumed by mount/systemd automatically.
Its paired code/manifest allowlist remains one regular file, not a directory.
The source is checked by the same size/mode/symlink/credential guards and the
repository copy is created only by the normal sync transaction.
`docs/storage.md` is the one new documentation allowlist entry; `fstrim.timer`
is the one new service-inventory approval.

No NVMe/EFI identifiers, disk serials, personal relative paths, checksum
inventories, backups, access-test output or migration logs are published.
Private recovery evidence stays outside the checkout. Do not widen this
exception to raw fstab, arbitrary storage files or device discovery exports.

## Git/GitHub

No tool stages, commits, pushes, changes Git identity/remotes or invokes SSH.
Existing GitHub SSH authentication is left intact. Check remote visibility
yourself; private is recommended. The existing snapshot has already been committed
and its GitHub branch was verified. Review configured author identity locally,
then obtain approval for each new commit and push after inspecting staged content.
No history rewriting or force-push behavior is implemented.

Audit covers current tree/index, **not every historical Git object**. Current
history includes the published snapshot and earlier commits; the README-only
initial-commit observation belongs to the archived foundation phase. Accidentally committed
credentials require revocation and a separately planned cleanup, not merely
adding an ignore rule.

Local transaction originals live inside `.git/dotfiles-sync/`; normal Git staging
does not include them. They are not independent backups and do not travel with
a clone. Never upload/archive the whole `.git` directory as a public artifact.
