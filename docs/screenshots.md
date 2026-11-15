# Gallery provenance and privacy

The user requested attractive documentation screenshots and explicitly prohibited
capturing the current workspace. **No live screen capture command was used.**
No workspaces were switched, windows moved, session locked or service restarted.

Only three existing captures were selected, visually inspected, downsampled,
framed in graphite/crimson and re-encoded as metadata-free PNGs. The frames/titles
are documentation presentation, not additional elements of the running desktop.

| Repository image | Existing local verification capture | Context |
|---|---|---|
| `assets/screenshots/desktop.png` | `wallpaper/combined-desktop.png` | Clean dual-output panorama and Waybar, no application windows |
| `assets/screenshots/lockscreen.png` | `lock-notify-borders/hyprlock-DP-1-empty.png` | Prior primary-display lock styling check, empty password field |
| `assets/screenshots/greeter.png` | `greeter-single-form/after-preview-DP-1.png` | Test-mode primary-display greeter, empty password field |

Original paths above are relative to the existing local verification directory,
not files that must be imported or exposed in the repository. Only the rendered
gallery exports are included. Captures containing browser conversations or
terminal history were **not** imported.

These are historical visual references, not recordings of a current session,
authentication attempt or reboot. The current Lenovo-only form behavior is
represented by the actual snapshot configs and was separately confirmed by the
user in live tests. The greeter account selector displays the nonsecret local
account name already present in selected configuration; no password was entered.

Exact hashes, dimensions and source descriptions are in
`manifest/screenshots.json`. The audit accepts only these three registered paths,
validates PNG chunks/dimensions and refuses any changed hash. This is an integrity
guard, not automated visual secret detection. Future screenshots need manual
privacy review and an explicit registry update; routine sync never captures or
refreshes them. No whole-tree image-folder exception was introduced.

The gallery totals approximately 2.52 MiB. Documentation exports deliberately use
smaller dimensions than the original captures. No original wallpaper or live
configuration was changed. Wallpaper redistribution provenance still needs
resolution before public sharing; a private remote is recommended initially.
