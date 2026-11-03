# RiceBowl 0.7.1 — Brand and upgrade compatibility

RiceHub has evolved into RiceBowl, a native GTK3 manager for seven opt-in XFCE/X11 desktop styles.

### Highlights

- RiceBowl application identity and original scalable bowl logo.
- New `ricebowl` executable and desktop launcher, with backwards-compatible `ricehub` and `macrice` aliases.
- Distinct, native system-control layouts for Windows XP Luna, Classic 98/2000, ChromeOS and Frutiger Aero, integrated with available XFCE system tools.
- Expanded, profile-specific Thunar styling for all six non-macOS rices; safe migration from old managed CSS blocks and preservation of unrelated custom GTK CSS.
- No changes to macOS rice implementation, settings, Plank integration or existing user backups.

### Compatibility

Existing D-Bus shell identifiers, internal theme names and startup entries remain compatible. The GitHub repository URL is still `CopyPasteUser/RiceHub` until its owner renames the repository through GitHub Settings; the new RiceBowl brand is independent of that GitHub administrative change.

### Acceptance

The release workflow requires the repository's Python and native GTK/X11 tests to pass before publishing. Physical Linux Mint XFCE panel switching, Plank autostart coexistence, HiDPI and multi-monitor validation remain outstanding; previous screenshots are retained as version-labeled historical captures.

See [README](README.md) and [CHANGELOG](CHANGELOG.md) for setup and migration notes.

### Branding maintenance

This 0.7.1 maintenance release aligns the application sidebar icon, window and prototype titles, packaging metadata, desktop autostarts and README with RiceBowl. Exact former managed autostart entries remain recognized for restoring pre-upgrade sessions. The 0.7.0 release tag remains an immutable historical snapshot.
