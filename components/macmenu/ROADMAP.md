# MacMenu roadmap to stable 1.0

Updated 2026-11-01. Current code: **1.0.0rc11**, a release candidate.
Checked items are implemented or supported by stated tests; they do **not**
imply that every hardware configuration has been validated.

## Completed: functionality and integration (0.1–0.9)

- [x] One independent GTK3 app; the historic Classic/Hybrid layouts were consolidated in rc6.
- [x] Native GIO desktop app discovery, hidden-entry handling and launch.
- [x] Search by app names, generic names, descriptions, categories and keywords;
      multiword and accent/umlaut normalization.
- [x] Favorite-aware result ordering, favorite reordering, local recent apps.
- [x] App `.desktop` actions, context menus by mouse and keyboard.
- [x] Native keyboard search, category and layout shortcuts; app index refresh.
- [x] Auto, Midnight, Light, Graphite, Ocean and Violet themes; icon sizes and menu positioning.
- [x] Atomic, permission-restricted config; bounded error logs without queries.
- [x] History opt-out and clear; private JSON backup export/import and reset.
- [x] Guardrails for backup format, length and replacement confirmation.
- [x] GApplication single-instance activation and complete CLI controls.
- [x] XFCE panel launcher and non-root user installation without removing Whisker.
- [x] Debian package build with deterministic timestamps and root-permission check.
- [x] Debounced GIO app catalog refresh and incremental large-list rendering.
- [x] Keyboard focus states and separate empty results states.

## Completed: rc1 baseline

- [x] 515-app synthetic native GTK smoke test.
- [x] Genuine XFCE screenshots of grid, list, light theme and settings.
- [x] Real XFCE launch/search/favorite smoke tests including Mousepad.
- [x] Two reproducible `.deb` builds verified using `SOURCE_DATE_EPOCH`.
- [x] Documentation for installation, shortcuts, diagnostics and rollback.

## Completed: rc2 compactness and memory

- [x] Window reduced from 784×630 to 624×508 (36% smaller surface).
- [x] Hybrid sidebar removed; category dropdown introduced.
- [x] Classic category sidebar narrowed; permanent app action buttons removed.
- [x] One native search field and two prominent layout choices.
- [x] System quick actions collapsed to one menu.
- [x] On-demand widgets: 30 initial entries instead of 64 on large catalogs.
- [x] Optional warm background mode; process exits by default on dismissal.
- [x] Real GTK review of both modes and settings.

## Completed: rc3 Control Center visual redesign

### 1 — Question every control

- [x] Inspect the user's **actual Control Center v1.3.1 source** and extract
      its midnight surface, blue accent, elevated modules and rounded shapes.
- [x] Write a decision audit for every visible control and each preference.
- [x] Remove the duplicate View preference; keep the direct List/Grid switch.
- [x] Remove redundant launcher title and persistent footer; show only search,
      segmented layout control, More menu, category and app count.
- [x] Rename misleading "Near panel" preference to "Near pointer".
- [x] Move Preferences into the More menu; keep `Ctrl+,` for fast access.

### 2 — Improve visual rhythm

- [x] Unify with Control Center colors: `#0e1118`, `#0a84ff`, soft card borders.
- [x] Use a 20 px outer radius and compact native controls, not fake blur.
- [x] Shrink the default menu from 624×508 to **552×466** (19% less area).
- [x] Four-column app grid with tighter tile spacing and readable labels.
- [x] Compact Classic rail at 138 px, with one app action per activation.
- [x] Group Appearance and Privacy & Data into clean segmented settings pages.
- [x] Translate all MacMenu-controlled UI labels, tooltips and messages to English.
- [x] Make the README, design contract and current roadmap English.

### 3 — Keep it usable and lean

- [x] Render small catalogs (up to 48 matches) fully to avoid an unnecessary
      sticky Load More button; preserve 30-widget initial cap for large sets.
- [x] Keep favorites, `.desktop` actions, Xfce shortcuts, app search and backups.
- [x] Maintain backwards-compatible config keys and backup format.
- [x] Background process stays **off** by default, with an honest speed/RAM
      setting; no new daemon, network calls, startup service or app indexer.
- [x] Keep true source screenshot capture tooling for GTK/Xfce.

### 4 — Verify rc3

- [x] Unit tests and Python compilation.
- [x] Native GTK 515-app smoke: both modes, search, categories and paging.
- [x] Real XFCE captures: Hybrid, Classic, Light and both Preferences pages.
- [x] Debian package checks and two-build reproducibility comparison.
- [ ] Repeat launch-time and RSS measurements on the user's Linux Mint machine.

## Completed: rc4 macOS-inspired visual reset and reliable upgrades

### 1 — Make the launcher more useful with less clutter

- [x] Examine real rc3 GTK screenshots and reassess every visible area.
- [x] Use a single rounded, recessed app module instead of separate per-app cards.
- [x] Fit four complete icon rows without clipping at the new **536×486** size.
- [x] Set category rail to 132 px; keep app names visible in Classic list.
- [x] Hide the redundant total-app count while browsing; show count when searching.
- [x] Maintain one search field, one mode switch and one overflow menu.

### 2 — Make appearance discoverable without extra settings

- [x] Six live theme previews in one Appearance row: Auto, Midnight, Light,
      Graphite, Ocean, Violet.
- [x] Apply theme instantly, persist it, and re-theme existing dialogs.
- [x] Reuse a single palette owner for UI CSS and preview swatches.
- [x] Keep contrast, legibility, and keyboard accessibility visible in all modes.

### 3 — Make the new version actually replace the old one

- [x] Executable `./install.sh` plus read-only `--dry-run`.
- [x] Stop only a verified, current-user older `python3 -m macmenu` process.
- [x] Detect and explicitly prompt before removing old `xfce-macmenu` system package.
- [x] Back up a managed user installation, atomically replace source and launcher,
      and remove old modules/caches from the active installation.
- [x] Preserve personal preferences and do not change Whisker or Control Center.
- [x] Reject unknown/unmanaged install paths; test rollback on staging failure.

### 4 — Release verification

- [x] Unit tests for theme migration and installation safety.
- [x] Native GTK 515-app smoke: Classic, Hybrid, search, categories and paging.
- [x] Native XFCE screenshots of both layouts, appearance variants and settings.
- [x] `.deb` package layout checks and reproducible release build.
- [ ] Verify upgraded user installation and process replacement on the user's
      Linux Mint computer, including their existing panel shortcut.

## Completed: rc5 screenshot-inspired macOS mode and session controls

- [x] Inspect the supplied screenshot and extract its useful visual structure:
      a symbolic navigation rail, clearly framed apps and fixed session area.
- [x] Add a 53 px icon rail to Hybrid without replacing the four-column grid.
- [x] Keep the full Classic/Whisker text category rail and its app list unchanged.
- [x] Align every category with a system icon and an accessible name/tooltip;
      keep favorites, recent and keyboard shortcuts.
- [x] Add bottom account control: LightDM `Switch User` when available,
      otherwise XFCE `Lock Screen`. No password handling inside MacMenu.
- [x] Add bottom `Log Out` that opens XFCE's system-owned logout confirmation.
- [x] Detect missing session tools and omit unsupported actions from menus.
- [x] Remove the now-obsolete Hybrid dropdown and its GTK widget.
- [x] Rebalance the window to 572×486; verify four complete grid columns and
      rows, with no partly exposed fifth row in the default screenshot.
- [x] Add command-selection unit tests and native GTK session-button smoke test
      without actually logging out of the test desktop.
- [x] Capture new true GTK screenshots for Classic, Hybrid and themes.
- [x] Keep the safe RC4 upgrade logic and version it as a separate RC5 release.
- [ ] Confirm LightDM switch-to-greeter and XFCE logout dialog on the user's
      Linux Mint desktop without disrupting active work.

## Completed: rc6 single-mode, responsive toggle

- [x] Remove the Whisker/Classic renderer, category sidebar, CSS, mode selector,
      shortcut and obsolete List descriptions preference.
- [x] Consolidate into one macOS-style navigation rail and app grid.
- [x] Preserve themes, favorites, privacy controls and app history while
      ignoring obsolete `view` settings from earlier installs and backups.
- [x] Recycle GTK FlowBox tiles during search and warm reopen; reload icons
      only when an app or its icon size changes.
- [x] Keep the GApplication ready by default for near-instant repeated
      shortcuts; **Instant reopening** can be disabled to reduce hidden RAM.
- [x] Test independent `--toggle` CLI invocations against one GApplication:
      invocation 1 opens, 2 closes, 3 opens the same window.
- [x] Native 515-app test exercises widget recycling, incremental paging,
      search and the fixed session rail.
- [x] Capture true GTK screenshots, update docs and ship a separate RC6 package.
- [ ] Verify actual Super/Super+Space XFCE shortcut on the user's laptop.

## Completed: rc7 installed-launcher regression

- [x] Reproduce the installed shell wrapper ignoring `--version` and
      erroneously starting the GTK app.
- [x] Pass the full argument vector through to Python, including `--toggle`
      and the `--quit` used by safe upgrades.
- [x] Prove a native regression test fails before the fix and passes after it.
- [ ] Check the user's installed launcher version, shortcut binding and focus
      behavior on the ThinkPad; the remote hardware is not available here.

## Completed: rc8 Super-key focus-race protection

- [x] Reproduce a focus-loss event arriving immediately before the second
      independent `--toggle` IPC command.
- [x] Prevent the implicit focus-out dismissal from racing the explicit
      launcher shortcut; keep a cancellable 350 ms click-away grace period.
- [x] Cancel pending dismissals on toggle, reopen and window destruction.
- [x] Verify open / close / reopen and simulated Super-key focus loss via
      real GTK/GApplication IPC processes; preserve click-away close behavior.
- [ ] Confirm the single-Super XFCE shortcut works on the user's ThinkPad.

## Completed: rc9 direct native warm activation

- [x] Benchmark the old Python/GIO remote CLI against native GLib/D-Bus
      activation in a real XFCE desktop.
- [x] Use `gapplication launch` for resident `macmenu --toggle` calls,
      avoiding a fresh Python/GTK import on every Super press.
- [x] Keep transparent fallback to Python for cold startup, unavailable
      `gapplication`, and non-toggle commands.
- [x] Test the actual installed shell wrapper with fake native clients:
      success skips Python, failure falls back, other flags bypass the fast path.
- [x] Assert that native remote activation really toggles and reuses the
      same window, not merely that the command exits successfully.
- [x] Measured synthetic XFCE median: ~9 ms with native client vs
      ~123–130 ms with Python/GIO (command round trip, not visible-frame latency).
- [ ] Measure actual Super-key-to-visible-frame latency on the user's ThinkPad.

## Completed: rc10 original monochrome Linux identity

- [x] Design an original white penguin silhouette, independently of the Apple
      logo, readable at both menu-bar and launcher icon sizes.
- [x] Show the mark beside search in the native GTK menu without expanding the
      window or adding a redundant header row.
- [x] Swap to an ink-only silhouette for the Light palette; cache scaled
      image data so repeat toggles do not reread the SVG.
- [x] Use a neutral dark icon tile for XFCE app menus, desktop launchers and
      panel launchers, with correct paths for both non-root and Debian installs.
- [x] Include all artwork in managed upgrades and Debian package verification;
      keep the original Whisker and Control Center untouched.
- [x] Publish screenshot evidence and native-GTK/theme checks.
- [ ] Integrate the white mark into MacBar when its separate codebase is
      available; the bundled SVG is ready for a 16–24 px panel button.

## Completed: rc11 remove duplicate session controls

- [x] Remove the account, lock and logout controls and divider from the left
      rail, leaving only app categories and more usable vertical room.
- [x] Remove the same account/session actions from More. File Manager,
      Terminal, XFCE Settings and Preferences remain reachable.
- [x] Remove the unused session-command module; do not call a power or
      logout command from MacMenu. Control Center remains the sole owner.
- [x] Preserve the white penguin identity, themes, shortcut, app search,
      favorites, safe installer and privacy features.
- [x] Update desktop integration tests and capture the streamlined GTK UI.

## Stable 1.0 release gate — still outstanding

- [ ] Accept full desktop UI on the user's real Linux Mint XFCE machine.
- [ ] Verify panel anchoring, keyboard bindings and Escape/outside-click behavior
      with the user's actual panel configuration and Control Center installed.
- [ ] Verify multi-monitor placement, HiDPI, accessibility/keyboard/screenreader
      behavior, and light/dark/custom GTK themes.
- [ ] Measure cold and warm launch time, CPU and RAM with 500+ **real** apps
      on the user's hardware and confirm the default warm/RAM tradeoff.
- [ ] Install, upgrade, remove and roll back the `.deb` on Linux Mint.
- [ ] Test new user installer against the exact version currently installed on
      the user's laptop, including the prior running process.
- [ ] Confirm no P0/P1 bugs after extended use and restart/login cycles.

## Proposed releases after stable 1.0 (not yet implemented)

Each release should remain a compact native GTK/XFCE application; no web UI,
online indexing service, permanent polling or additional Control Center widgets.
The priorities below reflect daily use on an 8 GB ThinkPad XFCE setup.

### 1.1 — MacBar integration and precise menu positioning (P1)

- [ ] Integrate MacMenu's existing white penguin resource and `macmenu --toggle`
      into the separate MacBar project with a single 16–24 px menu-bar control.
- [ ] Use MacBar's button geometry for reliable placement below the icon,
      clamped to work areas on multiple monitors and at panel edges.
- [ ] Show an active/open state, retain Escape/click-away behavior and make
      successive Super-key and bar clicks share one resident menu instance.
- **Acceptance:** 20 alternating bar and shortcut invocations produce correct
  open/close state; no duplicate process, clipped menu or extra polling loop.

### 1.2 — Faster keyboard navigation and better search (P1)

- [ ] Predictable arrow-key traversal of visible app tiles, first-result
      activation, Home/End behavior and focus restoration to search.
- [ ] Improve fuzzy ranking for small typos and common abbreviations while
      retaining exact and prefix-match precedence; keep queries local/private.
- [ ] Provide keyboard-only access to `.desktop` app actions and favorite
      ordering using the existing context actions, with no new buttons per tile.
- **Acceptance:** search and launch via keyboard without pointer; 500-entry
  synthetic catalog keeps input responsive; regression tests cover matches.

### 1.3 — Measured performance and low-memory mode (P1)

- [ ] Capture cold-start, hidden RSS, wake-to-first-frame and search p50/p95
      on the target i5 / 8 GB laptop with 50 and 500 apps.
- [ ] Profile GTK icon decode, catalog scan, window positioning and module
      imports; optimize measured hotspots without speculative caches.
- [ ] Evaluate whether a strict low-memory profile can release unused tiles
      while hidden without degrading the default warm toggle.
- **Acceptance:** publish baseline and after-measurements, prove no toggle
  regression and disclose RAM/latency tradeoffs in the UI and README.

### 1.4 — App discovery reliability and recovery (P2)

- [ ] Verify `.desktop` changes from APT, Flatpak and user installations across
      common Linux Mint/XFCE setups, including hidden/removed apps.
- [ ] Add a quiet, actionable catalog error state if GIO discovery genuinely
      fails; keep existing `Ctrl+R` refresh and 300 ms event debounce.
- [ ] Test settings import/export, rollback and unusual desktop entry metadata;
      never execute untrusted desktop command text in a shell.
- **Acceptance:** installed/uninstalled apps appear/disappear without restart;
  unexpected metadata cannot crash or block the launcher.

### 2.0 — Durable cross-desktop release (P2, after 1.x stability)

- [ ] Validate X11 and Wayland where the compositor permits positioning,
      multi-monitor/HiDPI, screen readers and keyboard-only workflows.
- [ ] Automate source, `.deb`, changelog, screenshot and checksum release
      checks; install and rollback smoke on supported Mint/XFCE versions.
- [ ] Revisit GTK4/libadwaita or a native alternative only if measurements
      establish a net win in responsiveness, RSS and desktop compatibility.
- **Acceptance:** reproducible packages and documented support matrix; no
  regressions in search, theme, accessibility, shortcut or clean upgrades.

## Safe Mint acceptance procedure

1. Leave Whisker in place and open MacMenu alongside the Control Center.
2. Test the single macOS grid, keyboard search, multiword queries and several app launches.
3. Check favorites, app actions, Escape, search and category changes.
4. Check Appearance and Privacy & Data, including safe export/import and reset.
5. Verify three repeated `--toggle` shortcut presses and
   the optional background-memory saving setting.
6. Verify session and power actions exist only in the Control Center, not
   in MacMenu's left rail or More menu.
7. Capture any problem with `~/.cache/macmenu/macmenu.log` and the version.

## Screenshot evidence

`screenshots/macmenu-rc11-midnight.png` and older screenshots contain directly
captured native GTK windows,
not generative artwork. The Xfce test session exposes 32 app entries; the smoke
test adds 515 simulated entries. That proves a meaningful integration baseline,
**not** stable 1.0 validation on the user's actual hardware.
