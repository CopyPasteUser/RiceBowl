# Windows 98 / 2000 Classic · implementation roadmap

The goal is a **recognizable, genuinely functional Windows 98-style Linux XFCE
desktop**, not a generic silver recolor, an XP menu or a static illustration.
Original GPL-compatible RiceBowl art only; no proprietary Microsoft icons,
bitmaps, fonts or binaries. Keep Windows XP, 7, 10, ChromeOS, Frutiger and
macOS behavior and artwork unchanged.

## Source references and measured direction

- [GUIdebook: Windows 98](https://guidebookgallery.org/guis/windows/win98/)
  — screenshots of the original Start hierarchy, 3D controls and Explorer.
- [Windows 98 explained: Start menu figure](https://nmetau.edu.ua/file/130.pdf)
  — gray vertical-menu body with a blue side strip; compact hierarchical rows.
- [GUIdebook: Classic UI](https://guidebookgallery.org/screenshots/appearance/)
  — the historical system-control/appearance model. These are observation
  sources only; no pixels are copied into the project.
- Identity: flat `#008080` desktop, raised `#c0c0c0` surfaces, focused
  `#000080` menu and active XFWM title, sharp dark/white two-pixel relief,
  narrow sans-serif type, low-density icon palette and **zero rounded corners**.
  The original CRT/penguin symbol is the explicit Linux adaptation.

## Seven delivery steps

1. **[x] Audit actual renderer against the real Win98 UI.** Examine the
   1600×900 native screenshot, live GTK/XFWM files, Start and Control Panel
   behaviors, reversible presets and prior icon generator. The prior
   watery/glass wallpaper, spacious 430px menu and 53px generic taskbar
   contradicted Win98's 1998 look.
2. **[x] Restore the correct desktop and taskbar silhouette.** Regenerate a
   crisp solid-teal wallpaper, set a 34px panel, downscale the original custom
   Linux Start badge to 19px, compact launcher/task buttons, keep window state
   and real audio/network/battery indicators and use a single-line clock.
3. **[x] Build a real Win98 Start hierarchy.** Side-printed `RiceBowl 98` strip,
   dense item rows with true icons and hover/focus `Gtk.MenuButton` cascades:
   Programs (real Gio categories), Favorites, Documents and Settings. Find
   expands real installed-app search; Help/Run launch available XFCE utilities
   only; Shut Down opens XFCE's confirmation dialog, never executes immediately.
4. **[x] Draw native-era window chrome.** Generate brand-new square 22px XFWM
   minimize/maximize/close/shade buttons in four interaction states, 27px
   active navy/inactive silver title segments and embossed 3D frame borders.
5. **[x] Finish coordinated GTK/Thunar/icons.** Style focus, pressed/disabled,
   menu, notebook, scrollbar, toolbars and actual Thunar controls; use small
   original pixel icons for Start, Settings, Find, Help, Run and Shutdown.
   `--classic-only` regenerates this identity without touching other rices or
   overwriting existing hand-curated 98 icons.
6. **[x] Prove basic functionality and upgrade safety.** Retain event-driven
   Wnck/Gio app launch, right-click pinning, keyboard search, hardware status,
   safe session handoff and restore snapshots. Exact prior git blob hashes
   trust only unmodified managed files for backup-backed asset upgrades;
   custom user changes still block automatic replacement.
7. **[ ] Validate and release real implementation.** Run all Python tests,
   GTK CSS parser, CI native-Xvfb shells and real 1600×900 + 1024×768
   screenshots; inspect the result, refine if needed, update current-only
   README gallery and then merge the tested PR into GitHub `main`.

## Acceptance criteria

- At a glance it unmistakably reads as **Windows 98**, while the included
  artwork makes clear that the host remains Linux.
- The Start menu never overlaps the taskbar, including at 1024×768; cascading
  and keyboard-focused actions work as genuine GTK widgets.
- Control Panel presents usable real XFCE controls and actual device status.
- All original installer backups, theme conflict guards, external tools,
  installed program pinning and six other rice identities remain intact.
- GitHub screenshots are actual GTK/X11 captures of the merged code, not mockups.
- CI virtual desktop does not replace physical Mint/XFCE acceptance, which
  remains an owner-side smoke test.
