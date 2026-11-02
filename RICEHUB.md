# RiceHub · Desktop styles for XFCE

RiceHub is the beginning of a bigger idea: one lightweight home for complete XFCE rices inspired by operating systems we know and love. The project is built around **a working system first, an honest roadmap second**. The macOS implementation comes from the existing MacRice projects. Version 0.3 RC2 adds a feature-rich Windows 7 Aero shell on the same reversible engine, with virtual-GTK CI; physical Mint/XFCE acceptance is still open.

## First launch

The main installer installs both the old MacRice CLI and the new RiceHub desktop entry. It does not change GTK, icons, Plank or your XFCE Panel unless you explicitly apply a rice later.

```bash
bash install.sh --dry-run   # Preview without changing anything
bash install.sh             # Install as your normal user, never with sudo
ricehub                     # Open the new hub
```

If you prefer the existing command, `macrice hub` opens the same app; `macrice gui` still opens the older MacRice settings manager.

### Where to start

1. **Discover rices:** Pick macOS and one of Aurora Night, Aurora Day, Liquid Glass Night, Liquid Glass Day or Classic Aqua. Look at the preview and click **Check requirements** before applying. Missing WhiteSur, Bibata or Inter assets are reported as requirements; they are never silently downloaded.
2. **Apply rice:** Review and confirm the changes. The engine saves a private recovery snapshot first, then styles XFCE GTK and window decorations, Thunar, MacMenu, Control Center, MacBar, the wallpaper and Plank.
3. **My desktop:** Check the effective desktop configuration if a theme doesn't look right.
4. **Backups & restore:** Restore the last active snapshot. The restore engine attempts to protect later manual edits. It cannot promise to reverse changes made by unrelated software.
5. **Components:** Toggle the already installed menu and Control Center, start the bar/dock, or explicitly repair bundled apps.
6. **Windows 7:** Select Aero Meadow or Aero Cascade. Check requirements, apply, then use the new GTK taskbar and Start menu. The menu indexes real `.desktop` launchers; the Aero session login entry is managed with the same backup/restore protections. A separate read-only preview is also available.
7. **Performance:** Choose a resource profile and run an on-demand memory/CPU snapshot. There is no extra monitoring service.

The desktop remains usable if your XFCE configuration is different, but **the full macOS rice currently targets XFCE/X11**. Try it on a non-critical account before replacing your panel.

## What is available?

| Rice family | Status | Planned identity |
| --- | --- | --- |
| macOS / Aurora collection | **Available (preview)** | MacBar, MacMenu, Control Center, Plank, five full desktop palettes and Thunar styling |
| Windows 10 | Coming soon | Left-aligned taskbar, Start menu, action area and clean productivity styling |
| Windows 11 | Coming soon | Centered taskbar, rounded launcher, quick settings, light/dark modes |
| Windows 7 | **Experimental, installable** | Aero Meadow / Cascade wallpaper, Aero Penguin, original GTK/XFWM icons and chrome, Thunar, Plank glass theme, event-driven taskbar and searchable Start menu |

Windows 10 and 11 are **read-only descriptions**. Windows 7 can be applied only after a read-only preflight and explicit confirmation. The *separate Windows 7 preview dialog* is still a harmless demo. An Aero apply installs only original assets in the user's home, saves a restore snapshot, and changes the selected XFCE, Plank and session appearance. It does not install packages or overwrite third-party themes.

The Aero taskbar includes persistent right-click pins, a two-line clock, bounded/paged searchable Start menu, Show Desktop, native settings shortcuts and **optional live window switching**. Install `gir1.2-wnck-3.0` on Linux Mint XFCE to enable event-driven Wnck window buttons (activate, minimize, restore and overflow); without it, pinned launchers still work. An **experimental StatusNotifier (SNI) tray** is available by default, using an existing watcher when present or a session-local fallback when none exists. Legacy XEmbed tray icons remain unsupported. Set `RICEHUB_AERO_TRAY=0` to disable the host. Optional `RICEHUB_AERO_GLASS=1` enables a more translucent gradient; it does **not** provide background blur and depends on the compositor for its visual result. The Aero shell can reserve the bottom X11 workarea using EWMH, opt-out with `RICEHUB_AERO_RESERVE=0`; existing XFCE panels and MacBar are never force-killed. For all individual components and assets, see [WINDOWS7.md](WINDOWS7.md).

### Genuine interface screenshots

![RiceHub Aero selection in the native XFCE/X11 gallery](screenshots/ricehub-aero-gallery-0.2.0rc1.png)

![Actual GTK3 Aero Start menu](screenshots/ricehub-aero-start-0.2.0rc1.png)

These are real GTK3 application captures from XFCE/X11. The [macOS + Plank overview](screenshots/macos-rice-with-plank-0.2.0rc1.png) is explicitly an **illustrative** full-desktop composition, not a live Plank capture.

## Product roadmap

**0.1 preview — foundation**

- [x] Native GTK3 gallery with search, filters, working availability badges and a responsive wallpaper preview.
- [x] All five existing macOS rices via the shared MacRice engine.
- [x] Desktop status, components, performance and backup/recovery pages.
- [x] Owned user-local RiceHub launcher, desktop entry, icon and compatibility with existing MacRice.
- [x] Explicit confirmation, read-only preflight and honest Coming soon states.
- [x] Interactive Windows 7 design prototype with sample search and no XFCE writes.
- [x] Publish genuine RiceHub and Windows 7 preview screenshots.
- [x] No new long-running process when the hub is closed.

**0.2 — original Aero rice — experimental now**

- [x] Two original Aero wallpapers and Linux penguin Start symbol.
- [x] Bundled user-local GTK3, XFWM4 and icon artwork; matching Thunar and glass Plank palette.
- [x] Actual searchable Start menu for installed applications and bottom taskbar with event-driven app catalog updates.
- [x] Optional live window task buttons, active-window highlights, minimize/restore and a compact overflow menu using event-driven X11 Wnck signals.
- [x] Reversible Aero apply/restore, managed session autostart and non-overlapping Plank configuration.
- [x] Updated RiceHub and Start menu screenshots; illustrative macOS + Plank desktop overview.
- [ ] Physical Mint XFCE / X11 hardware tests of window decorations and compositor variations.

**0.3 RC2 — Windows 7 Aero feature-complete candidate**

- [x] Persistent user-configurable taskbar pins with atomic, validated preference storage.
- [x] Responsive Start placement, paged all-program catalog, keyboard search and safe XFCE actions.
- [x] Show Desktop, date and time, native sound/network shortcuts, task overflow and X11 bottom workarea reservation.
- [x] Experimental SNI tray with bounded icon processing, hover tooltips and correctly positioned context menu calls.
- [x] GTK/X11 real-launch smoke test in GitHub CI, plus pure-logic regression coverage for pins, layout and D-Bus values.
- [x] Full Windows 7 component/asset inventory and release acceptance checklist.
- [ ] Physical X11 hardware validation, current screenshots of every feature, SNI interoperability and measured resource budgets.

**0.3 — dependable switching and onboarding**

- [ ] System compatibility score with package/theme installation instructions.
- [ ] More resilient migration and a recovery wizard with individual settings selection.
- [ ] Full keyboard-only, touch, HiDPI and small-screen testing on physical XFCE laptops.
- [ ] Additional desktop screenshots from physical supported XFCE hardware, with measured startup and memory budgets.

**0.4 — Windows 10 preview**

- [ ] Separate, reversible XFCE panel and Start-style application menu configuration.
- [ ] Taskbar styling, icon set, window theme and wallpapers, with regression tests.
- [ ] Shared preset contract so each rice uses the same plan, apply and restore pipeline.

**0.6 — Windows 11 and mature Windows 7**

- [ ] Centered Windows 11-inspired taskbar and quick settings.
- [x] Add experimental StatusNotifier tray support, with bounded icon decoding and safe coexistence with other tray hosts.
- [x] Add opt-in translucent Aero styling (`RICEHUB_AERO_GLASS=1`), without claiming compositor blur.
- [ ] Add legacy XEmbed compatibility if needed, and validate SNI compatibility and visual behavior on physical XFCE/X11 hardware.
- [ ] Theme import/export and optional community-authored presets with transparent provenance.

**0.8 — hub polish**

- [ ] Guided install/update of optional required themes from trusted package sources.
- [ ] Reliable upgrades, independent profile switching and conflict diagnostics.
- [ ] Validated per-rice screenshots, accessibility pass and performance regression suite.

**1.0 — stable rice hub**

- [ ] All available rices tested on supported XFCE/X11 releases.
- [ ] Crash-safe backups and restore from interrupted or outdated installations.
- [ ] Clear privacy, theme-asset licensing, release checksums and one-command updates.

## Why the existing repos are still here

The current suite keeps MacMenu, Control Center and MacBar as self-contained components within this source tree. Their existing standalone repositories remain available; we haven't deleted them or rewritten their histories. As the hub grows, the shared catalog and install/rollback logic can move into a single core without creating a separate GitHub repository for every Windows-like theme.

## Contribution and originality

These interfaces are *inspired by* familiar desktops; RiceHub is not affiliated with Apple or Microsoft and does not include their proprietary assets. The original Aurora wallpapers and monochrome RiceHub mark are included. The project is vibe-coded and human-directed with assistance from ChatGPT / OpenAI Codex; see [CONTRIBUTORS.md](CONTRIBUTORS.md).
