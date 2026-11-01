# Changelog

## 1.0.0rc11 – launcher-only rail, new feature roadmap (01.11.2026)

- Removed the bottom Switch User/Lock and Log Out buttons and their separator.
  Category navigation now has the entire left rail, including short screens.
- Removed duplicate session controls from More; the separate macOS Control
  Center remains the single home for account, lock, logout and power actions.
- Deleted the unused session-command module and its obsolete tests. The native
  GTK smoke test now checks the lean rail and the remaining More menu items.
- Kept the monochrome penguin branding, six themes, favorites, application
  discovery, single-instance Super-key toggle, performance and safe upgrades.
- Expanded the roadmap with stable 1.0 gates and focused 1.1–2.0 milestones.

## 1.0.0rc10 – original monochrome penguin identity (01.11.2026)

- Designed an original white Linux penguin symbol with eyes, beak and chest
  carved out using negative space; no colored mascot or Apple logo copy.
- Added a compact 26 px brand mark to the MacMenu header, with a contrast-safe
  ink-on-light variant and cached SVG rasterization to preserve warm latency.
- Gave the GTK window, XFCE application menu and panel launcher a neutral
  dark application icon featuring the same white penguin.
- Bundled SVG artwork in managed user upgrades, Debian packages and release
  archives. Desktop entries point to the *installed* SVG, not an unavailable
  build-tree file. Added installer, asset and native theme-switch coverage.
- Kept the Control Center style, compact size, menu toggle, user preferences
  and separate Whisker Menu unchanged. MacBar integration is a future task.

## 1.0.0rc9 – native fast-path shortcut activation (01.11.2026)

- Measured the warm toggle bottleneck: each XFCE shortcut previously started
  a fresh Python interpreter and imported GTK simply to contact the resident
  application (~123–130 ms per command in the synthetic XFCE test).
- When already running, `macmenu` and `macmenu --toggle` now activate the
  resident GApplication using the native `gapplication` CLI via D-Bus.
  Measured ~9 ms median in the same environment, with real visible-state checks.
- Gracefully fall back to the existing Python path for first/cold launch,
  missing native tools, and all non-toggle actions.
- Preserve RC8's Super-key focus-race protection and the existing GTK UI.
- Added shell fast-path/fallback tests and a native latency probe.

## 1.0.0rc8 – Super-key toggle race fix (01.11.2026)

- Reproduced the race between XFCE's Super-key focus loss and a remotely
  delivered `--toggle` command: the window could hide before the explicit
  toggle arrived, causing an unintended reopening.
- Deferred focus-out dismissal by a cancellable 350 ms. Explicit toggle,
  reopening and window destruction cancel pending focus dismissals.
- Retained click-away dismissal and verified its delayed behavior.
- Added native IPC regression cases for focus loss directly before an
  independent remote `--toggle` invocation.
- No visual or configuration changes; RC7's CLI forwarding fix remains.

## 1.0.0rc7 – launcher command-line forwarding hotfix (01.11.2026)

- Fixed the installed `macmenu` shell launcher dropping every CLI option:
  `--toggle`, `--show`, `--hide`, `--quit`, `--preferences`, and
  `--version` now reach the GTK application unchanged.
- Restored the installer's graceful old-process shutdown: it now successfully
  sends `--quit` to RC7 launchers instead of inadvertently toggling them.
- Added a native shell-launcher regression test that fails on RC6 and
  passes when `--version` is correctly forwarded without opening a window.
- Kept the single macOS layout and warm-toggle design from RC6.

## 1.0.0rc6 – single macOS mode, recycled tiles and fast toggle (01.11.2026)

- Removed the entire Classic/Whisker UI, layout buttons, `Ctrl+1/2`
  shortcuts, Classic-only settings and duplicate GTK rendering path.
- Kept the Control Center-inspired macOS icon rail, four-column grid,
  session actions, six color themes, favorites and privacy controls.
- Search now reuses a bounded pool of GTK tiles instead of tearing down and
  rebuilding icon widgets on every query; warm reopen updates only what changed.
- Enabled **Instant reopening** by default: a held GApplication receives
  `--toggle` from separate XFCE shortcut processes and alternates
  open/close/open. Turn the setting off to save hidden-process RAM.
- Automatically ignores legacy `view`, `show_descriptions` and
  `keep_running` settings without deleting user themes, history or favorites.
- Added three dedicated native-GTK tests, including real CLI IPC toggle,
  plus updated screenshots, safe-upgrade installer and Debian package.

## 1.0.0rc5 – macOS icon rail and real session actions (01.11.2026)

- Adapted the user-supplied macOS launcher reference: a narrow icon category
  rail in Hybrid, distinct app module and fixed account/logout controls.
- Added `Switch User` via LightDM `dm-tool` where supported; otherwise offered
  `Lock Screen` with `xflock4`. `Log Out` delegates to XFCE's confirmation UI.
- Never handles login credentials or attempts to end sessions itself. Unsupported
  actions are omitted; accessible icon labels and tooltips remain visible.
- Removed Hybrid's obsolete category dropdown and retained the full Classic
  sidebar and List/Grid keyboard shortcuts.
- Increased the default width to 572 px to keep all four grid columns, refined
  row heights to avoid partially clipped icons, and verified native GTK views.
- Added session-command unit tests and a safe GTK click-dispatch smoke test;
  updated the roadmap, design contract and screenshot gallery.
- Preserved the RC4 managed user upgrade, backup, old-instance shutdown and
  the original Whisker Menu/Control Center isolation.

Status: RC; LightDM and logout behavior require confirmation on the user's
actual Linux Mint installation before stable 1.0.

## 1.0.0rc4 – Simpler macOS launcher, additional themes, managed upgrade (01.11.2026)

- Revisited rc3 screenshots and redesigned the launcher around a single calm,
  rounded app surface. Four full icon rows fit in the compact 536×486 default.
- Narrowed Classic's sidebar to 132 px and showed the count only during search.
- Added Graphite, Ocean and Violet alongside Midnight, Light and XFCE Auto.
  Appearance now shows live color preview buttons; choosing one updates and
  saves the theme immediately.
- Rebuilt the user installer as a recoverable managed upgrade: graceful shutdown
  of the old app (with narrow same-user process fallback), backup, staged swap,
  removal of retired program files, and preservation of user preferences.
- Detects an existing Debian `xfce-macmenu` installation, explicitly asks
  permission before removal, and supports a read-only `--dry-run`.
- Rejects unmanaged paths; never modifies Whisker or the separate Control Center.
- Expanded installer and settings regression tests, live GTK smoke tests, design
  review, documentation and original XFCE screenshots.

Status: RC; replacing the user's exact installed build and Mint-specific
acceptance remain to be verified on their hardware.

## 1.0.0rc3 – Control Center visual alignment and English UI (31.10.2026)

- Matched the actual user Control Center v1.3.1 dark palette (`#0e1118`, `#0a84ff`),
  subtle elevated controls, 20 px rounded launcher and compact type scale.
- Reduced default window from 624×508 to 552×466 (about 19% less area).
- Refined Hybrid into a four-column grid; Classic keeps a 138 px category rail.
- Replaced the large heading and footer with a search-first header, segmented
  icon-only List/Grid choice, a small category/count row and one More menu.
- Redesigned Preferences with Appearance and Privacy & Data segmented pages;
  removed duplicate View setting, preserved theme/icon/position/privacy controls.
- English UI labels and error text, with installed app names using host locale.
- Small app catalogs render fully without unnecessary Load More; large catalogs
  retain the 30-widget first page and on-demand paging.
- Added an explicit design-decision audit and updated the design contract,
  roadmap, user documentation and native GTK screenshot capture.
- No new background daemon or dependency; existing config/backups remain compatible.

Status: RC; user-hardware validation remains a stable-1.0 release gate.

## 1.0.0rc2 – Compact-first redesign (31.10.2026)

- Reduced launcher from 784×630 to 624×508 (36% smaller surface).
- Always-visible List/Grid switch, category rail only in Classic, dropdown in Hybrid.
- Removed duplicate search-clear, per-app star/action buttons and four footer icons;
  all actions remain available through context and System menus.
- Compact native settings notebook and corrected dark-mode contrast.
- Smaller initial GTK page of 30 apps instead of 64, with explicit incremental loading.
- No idle GTK process by default; users may opt into warm background launches.
- GTK 515-app smoke test and real XFCE screenshots updated.
- Existing app preferences, favorites, recent apps and backup format remain compatible.

Status: RC only; physical Linux Mint hardware acceptance remains outstanding.

## 1.0.0rc1 – Feature-complete release candidate (31.10.2026)

- Multiword/accent-tolerant app search with favorite-aware ranking and category matching.
- Category shortcuts and manual app-index refresh.
- Opt-out/clearable recent history, private settings backups, validated imports and
  explicit confirmation before destructive resets.
- GApplication CLI control for showing, hiding, toggling, preferences, version and exit.
- Initial rendering bounded to 64 app widgets with explicit load-more controls.
- Debounced GIO catalog refresh; 515-app synthetic GTK smoke coverage.
- Reproducible Debian package build when `SOURCE_DATE_EPOCH` is specified.
- Fixed Debian package staging root permissions (0755) and added package permission checks.
- Closing preferences before `--hide`/`--quit` prevents orphaned modal dialogs.

Status: RC only. Mint hardware, HiDPI/multi-monitor, package upgrade and
long-term performance still require acceptance before a stable 1.0.

## 0.8.0 – Release candidate groundwork (31.10.2026)

- Fixed empty Hybrid grid on first GTK show, verified on a live Xfce desktop.
- Added persisted system theme, icon size, panel-near positioning and description visibility.
- Added app keyword search, Desktop Actions and accessible context menus.
- Added favorite reordering, launch failure diagnostics and bounded logs.
- Added `.deb` package build and expanded regression tests.
- Verified launching Mousepad through search/Enter and favorite/context actions in live Xfce.
- Captured genuine GTK screenshots of Classic, Hybrid (light/dark), and settings.
- Retained a non-root user install and the original Whisker Menu as a fallback.

Release status: not 1.0; full Linux Mint hardware acceptance still pending.

## 0.1.0 – Prototype

- Dual Classic/Hybrid views, GIO application catalog, search, favorites, recent apps.
- Initial GTK3 shell and settings, user installer and quick actions.
