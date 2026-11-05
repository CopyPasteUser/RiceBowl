# RiceBowl roadmap to 1.0

**New owner feedback (5 November 2026):** [11 open Mint/XFCE QA reports](OWNER_QA_2026-11-05.md),
including the Windows 98 menu autoclose, inert ChromeOS/Frutiger tray icons,
blank Windows 7 pages and safe-updater dirty-tree blocker. Prior automated
completion does **not** override contradictory on-device reports.

## Current engineering checkpoint (5 November 2026) · not a 1.0 release

- [x] Aqua World launcher Settings no longer blocks later menu navigation:
  opening a category dismisses the keep-above app menu even when the Control
  Center is already open. Persistent Apps/Places exits sit **outside** the
  Settings scroll area, with synchronized tab state and scroll reset.
- [x] Frutiger taskbar Wi-Fi, audio/media, Bluetooth and power flyouts now
  prioritize compact, scrollable **real device/action rows** with verified
  backends. Refresh and the optional full Settings shortcut are small header
  icons, not large “More settings” buttons. GTK/pointer regression tests cover
  the experience in [PR #69](https://github.com/CopyPasteUser/RiceBowl/pull/69).
- [ ] Owner to confirm on physical Mint/XFCE that repeated Settings → App
  menu → Apps/Places works; test multiple Wi-Fi SSIDs, Bluetooth devices,
  audio sinks/MPRIS players and small-screen flyout scrolling.
- [x] RiceBowl Hub now surfaces the existing confirmed, pinned fast-forward
  updater in the persistent sidebar, so checking/installing no longer needs a
  terminal; a running Hub still needs restarting after successful installation.
- [x] Shared normal GTK settings-window semantics for XP Luna, Windows 10 and
  Frutiger Aero: draggable themed title strips, taskbar/Alt-Tab integration,
  no always-on-top/auto-hide, and retained user placement. The other
  non-macOS rices already use decorated normal GTK Settings/Control Panels.
  [Cross-rice window and file DnD contract](RICE_WINDOWS_ROADMAP.md).
- [x] Aqua Control Center native Bluetooth detail now offers on-demand
  nine-second discovery and Pair via the registered **system** PIN agent.
- [x] PR #67 native GTK/X11 CI passed for settings window behavior, Aqua
  Bluetooth scan/pair flow and existing screenshot regression captures.
- [x] Shared geometry preferences for all six non-macOS Settings windows:
  atomic per-user save, debounce and off-screen recovery when monitors change.
- [x] Restricted ricePlate GTK file/URI copy targets on XP, Win7 and Aqua
  Places and the Windows 98 inspector: local regular files only, confirmation,
  no overwrite, background copy and unchanged-file undo.
- [x] Frutiger Aqua X11 mode/position **trial** using a detached, unprivileged
  18-second guard which reverts unconfirmed changes after the GUI closes.
- [x] [PR #68](https://github.com/CopyPasteUser/RiceBowl/pull/68): native
  virtual-X11/GTK CI passed for geometry, restricted file-drop bindings and
  temporary display editor. A 1024px screen-switch regression was fixed by
  clamping the **entire** restored Settings window inside its monitor.
- [ ] Real XFWM4/HDMI hardware acceptance for these changes on Linux Mint.
- [ ] Owner Mint/XFCE tests for actual moving, focus, task switching,
  multi-monitor handling and USB file drops.
- [ ] File-manager-grade folder transfers/moves and riceExplorer renderers
  are deferred until the **separate riceExplorer project reaches 1.0**.
- [ ] Local secure BlueZ PIN agent, transactional multi-monitor layouts,
  crash/HDMI recovery drills and full file-DnD physical testing remain open.

- [x] `macrice doctor` / `--json`: read-only XFCE/X11, managed-install,
  launcher, optional hardware-backend and private shortcut-recovery checks.
- [x] Selected-rice `macrice doctor --style STYLE`: reuse the real read-only
  rice plan for bundled assets/settings and show concise readiness feedback in
  the Hub without changing the running desktop. Hardware sign-off stays open.
- [x] Opt-in official-origin fast-forward update: `macrice update check
  --refresh`, then `macrice update apply --yes`; stage a pinned Git revision,
  preserve user edits, save previous bundle and attempt reinstall on failure.
  GUI equivalents live in the Hub's existing Recovery tab. **Not signed
  release verification or globally atomic rollback**.
- [x] Frutiger native WPA password input via nmcli stdin (not command-line
  arguments), pairing of already-discovered BlueZ devices with system-dialog
  fallback, and a real local GTK date/calendar popover.
- [x] Frutiger media detail in the sound flyout reads bounded session MPRIS
  players and dispatches only supported Play/Pause/Next/Previous methods;
  no player daemon or persistent listening loop. Gio VolumeMonitor powers
  a second native mounted-location popup with open and user-confirmed,
  asynchronous unmount; pending/failed requests are visible.
- [x] Native Frutiger Bluetooth discovery via BlueZ `StartDiscovery` with
  bounded wait and guaranteed `StopDiscovery` on cancel/close; Pair uses the
  default BlueZ system agent for passkey workflows (when available).
- [x] Display Control Center reads real RandR output geometry, primary screen
  and modes. The new opt-in single-active-output editor makes a reversible
  trial only; automatic rollback is owned by a separate timed user process.
- [x] Sequential seven-profile recovery simulations across non-macOS shells,
  including a failed mid-transition handoff; regression coverage in CI.
- [x] On-demand repeated CPU/PSS/thread measurement with per-PID medians and
  machine-readable JSON. No new resident monitor or unmeasured RAM claims.
- [x] PR #65's Xvfb/native GTK smoke passed on GitHub, including calendar,
  secret-entry and mounted-location popup constructors.
- [x] PR #66 native X11 CI passed for the new Bluetooth scan-button lifecycle
  and X11 display-readout changes, including existing screenshot regressions.
- [ ] Physical hardware acceptance and 1.0 security/fidelity gates still pending.
- [ ] Validate the new USB/media/date/credentials GTK surfaces in virtual X11
  and on the physical laptop; complete safe writable Frutiger monitor layout,
  local BlueZ PIN-agent wizard and separate riceExplorer Aqua renderer integration.

Owner-facing [1.0 acceptance sheet](ACCEPTANCE_1_0.md) defines the exact
session-switch, Wi-Fi/Bluetooth, external HDMI, suspend and PSS measurements.
macOS Aurora visuals remain unchanged.

> **Riceware ecosystem plan:** [riceExplorer, riceSpice, ricePop, ricePlate and riceWine](RICE_ECOSYSTEM_ROADMAP.md). Defines shared backends, distinct renderers, ownership, conditional independent programs and acceptance gates. Planning only; no new service is deployed.

## 1.0 hardening pass — session, resource visibility and Aqua flyouts (4 November 2026)

- [x] Skip unnecessary Python/GTK `--quit` launches for absent RiceBowl
  taskbars using exact session-D-Bus ownership and an in-flight `/proc`
  fallback; preserve conservative shutdown if the bus is unavailable.
- [x] Add a read-only XFCE + RiceBowl process inventory in CLI and Hub,
  with measured PSS/CPU/threads and duplicate-panel/dock warnings. Document
  essential XFCE service boundaries in [XFCE_RESOURCE_BOUNDARIES.md](XFCE_RESOURCE_BOUNDARIES.md).
- [ ] Measure the **real** idle/settled XFCE resource savings and verify
  logout/login and standby recovery on the owner's Mint XFCE laptop; only then
  consider additional optional session-service changes.
- [x] Restore the stock XFCE panel and saved shortcuts when switching away
  from a RiceBowl theme; recover on shell startup, shutdown or session-control
  handoff failures. Regression tests cover these failure paths.
- [x] Extend the **on-demand** `/proc` performance report to all six non-macOS
  RiceBowl shells, including proportional memory (PSS), sampled CPU and thread
  counts. No new idle polling or background daemon.
- [x] Add compact Frutiger Aqua flyouts with verified Wi-Fi radio and visible
  networks, paired Bluetooth links, audio sink selection and available power
  profiles; missing providers are reported honestly. A second click is needed
  before disabling Wi-Fi or Bluetooth.
- [x] Reuse Frutiger's existing bounded Riceware runner, discard stale popup
  callbacks, and add deterministic unit tests plus native GTK smoke assertions.
- [ ] Verify real settled PSS/CPU, device behavior, suspended-session recovery,
  repeated rice switching and multi-monitor layouts on Linux Mint XFCE/X11.
- [ ] Finish Frutiger's remaining feature/fidelity backlog (full Bluetooth
  discovery/PIN wizard, monitor layouts, USB/media and Aqua riceExplorer).

**Scope:** The macOS Aurora UI and its existing startup path remain unchanged.

## Post-0.9.1 — Cross-rice visual QA and real-window coverage (3 November 2026)

**5 November screenshot refresh:** the current [34-image gallery](screenshots/current/README.md)
and the six RiceBowl Hub thumbnail images were rebuilt from a single passing
GitHub Actions native-X11 run. The gallery now covers 18 full-size shell /
control / genuine Thunar views, XP Luna's additional dialogs and tray, the
ChromeOS notification-history fallback and Settings app, Windows 10's new
Settings Home/Sound windows, and a standalone
MacMenu dark window. CI retains 1024×768 screenshots. Source hashes and
the capture revision are recorded in [the manifest](screenshots/current/manifest.json).
This **does not** close the integrated MacBar/Plank screenshot or physical
Mint XFCE acceptance milestones below.

- [x] Correct XP Luna and Classic Control Panel initial heights, keeping their
  volume/mute controls reachable and retaining scroll on compact desktops.
- [x] Make Classic's Control Panel a three-column icon view rather than an
  XP-style category list; add Win7 category search and legible inactive links.
- [x] Replace Windows 10's oversized duplicate taskbar search box with a compact
  button opening Start search; clarify ChromeOS settings-navigation chevrons.
- [x] Implement isolated XFWM4 + actual Thunar screenshot automation for all six
  non-macOS identities, with per-rice icon, GTK and Thunar palettes.
- [x] Use those authentic screenshots to detect Thunar's collapsed menu-item
  spacing, repair only affected rices and preserve installed managed CSS.
- [x] Green CI and visual review of 1600x900 and 1024x768 layouts; refresh the
  checked-in screenshots from the verified run, including six real workspaces.
- [ ] Add same-revision, genuine macOS Aurora MacBar + dock + file-window
  captures; do not reuse historical composite mockups.
- [ ] Owner run: repeated seven-rice switch/restore on Mint XFCE with Plank
  autostart, shortcuts, battery, suspend and external HDMI.
- [ ] Measure actual startup latency, CPU and proportional RAM on the owner's
  ThinkPad before calling this a stable 1.0 release.

**Next visual-fidelity milestone:** [Windows 7 Aero fidelity and acceptance](WIN7_AERO_ROADMAP.md)
— a native icon-first Superbar, actual Aero Start menu, original custom-drawn
XFWM4/GTK artwork, safe upgrade and real-X11 verification. The [XP Luna fidelity](XP_LUNA_ROADMAP.md)
work is already on main; neither improvement changes the published v0.9.1 package.

The Windows 7 follow-up adds WM_CLASS application grouping, native GTK preview
popovers, local-document Jump Lists and hover Peek. Its review branch also
replaced an early set of historical gallery images with authentic virtual-X11 captures;
the later 4 November refresh supersedes those screenshots with one-run evidence.
real Mint XFCE multi-monitor, resume and session switching remain owner tests.

**RiceBowl is the umbrella application.** The 0.6.0 milestone introduced installable XP Luna, Windows 98/2000, ChromeOS and Frutiger Aero styles alongside macOS, Windows 7 and Windows 10. The new desktops share the tested session/recovery engine; physical Mint XFCE validation is still required for the 1.0 hardware-stability milestone. The original read-only design previews remain available. Unfinished Liquid Glass presets and Windows 11 are not planned. See the [new-rice acceptance checklist](CONCEPTS.md) and [historical project roadmap](RICEHUB.md#product-roadmap).

MacRice is deliberately a thin integration layer. MacMenu, Control Center and MacBar keep their own tested lifecycles; Plank remains an external system dock.

## 0.9.1 — Owner acceptance follow-up (3 November 2026)

- [x] Record owner acceptance of the seven-rice experience except one observed XP Luna Start menu/taskbar overlap.
- [x] Anchor XP Luna to its allocated GTK height, with a shrinkable app list and automated popup-bound checks.
- [x] Gate the XFCE Panel handoff on a mapped replacement taskbar; add bounded recovery and regression tests.
- [x] Keep the RiceBowl Hub responsive during readiness verification; prepare 0.9.1 CI and release artifacts.
- [ ] Confirm XP Luna's fixed Start menu on the owner's Mint XFCE session, including external monitor and lower resolutions.
- [ ] Run the remaining real-hardware multi-monitor, login/relogin and measured PSS/CPU checks before 1.0.

## 0.9 — Faithful XP, Classic, ChromeOS and Frutiger refinement (3 November 2026)

- [x] Give XP its own actual two-column Start menu, account header, favorites list, places, power footer and vivid Luna taskbar.
- [x] Build an authentic Classic Programs flyout from installed .desktop categories, with working Find and OS-style controls.
- [x] Give ChromeOS a 12-app grid, live search, centered shelf and separate status capsule.
- [x] Give Frutiger Aero working Apps / Places / Settings tabs, organic glass controls and real system shortcuts.
- [x] Restyle actual GTK3/Thunar widgets, preserving file access and reversible desktop state (not a fake file manager).
- [x] Draw 36 additional profile-unique folder/device icons and prevent the asset generator from replacing them.
- [x] Add real, verified volume and mute controls, plus battery/network details; all hardware probes remain bounded.
- [x] Preserve legacy 0.8 theme and Thunar CSS formats in safe migration logic.
- [x] Validate all 12 actual GTK/X11 captures and six settings popups (visible-area regression check) with 193 passing Python tests; publish 0.9.0 as pre-release.
- [x] Owner acceptance of overall appearance and functionality (except XP menu overlap, targeted by 0.9.1).
- [ ] Complete device-specific checks for external displays, login/relogin and battery/charging behavior.

## 0.8 — Visual identity, status tray and repair (3 November 2026)

[Detailed 0.8.0 engineering and acceptance roadmap](RELEASE_0_8_0_ROADMAP.md).

- [x] Trust only exact known 0.6 / 0.7 asset hashes for automatic, backed-up theme upgrades.
- [x] Expose an explicit, user-confirmed backup-and-repair action for modified themes.
- [x] Add battery percentage/charging, active Wi-Fi/LAN, audio and clock with real system probes and bounded background refresh.
- [x] Replace cloned placeholder graphics with 42 distinct, original profile-specific app/places icons; add 66 status icons.
- [x] Give ChromeOS a dedicated centered apps launcher and Frutiger Aero an independent, organic dashboard.
- [x] Polish tray controls and control surfaces for Aero, Windows 10, XP Luna, Classic 98/2000, ChromeOS, Frutiger.
- [x] Add pure-Python migration/status regressions and virtual-X11 capture coverage for all six non-macOS shells.
- [ ] Physical Linux Mint acceptance: repeated switching, Wi-Fi/VPN, real battery/charging, Plank autostart and multi-monitor.
- [ ] Multi-monitor visual signoff and optional latency/performance profiling on physical hardware.

## 0.7 — RiceBowl naming and integration

- [x] RiceBowl application icon, desktop entry, native GUI title and public CLI.
- [x] Individual control layouts and enhanced Thunar chrome for non-macOS rices.
- [x] Align packaging metadata, documentation, screenshots provenance and project names.
- [x] Keep historical RiceHub theme IDs, D-Bus names and installed state for backwards compatibility.
- [x] Recognize old managed session launchers without overwriting customized entries.
- [x] Rename the GitHub repository to `CopyPasteUser/RiceBowl`, preserving the former URL as a GitHub redirect.
- [ ] Perform the physical Mint/XFCE switching, Plank and multi-monitor acceptance suite.

## 0.1 — Unified source and safe setup

- [x] Bring the three source projects together without importing private Git histories.
- [x] Add one user-local installer and a no-write dry run.
- [x] Add a compact GTK3 manager with app launchers and status.
- [x] Detect the user's existing XFCE themes and icons without accessing private network data.
- [x] Add matching app-only theme presets with recoverable settings backups.
- [x] Preserve the three standalone installers and their existing component tests.
- [x] Integrate existing Plank: read effective dock1 preferences, start its process and open native settings without taking ownership of its files (0.1.1).
- [x] Add original dark/light Aurora wallpapers and an on-demand illustrative full-desktop preview (0.2.0 RC1).
- [x] Add explicit XFCE/Plank/full-rice preflight, backup, apply and restore, without auto-changing settings during install.
- [x] Coordinate MacBar live color reload, reversible Thunar styling and opposite-color Plank presets (0.2.0 RC2).
- [x] Recover from Day/Night restore conflicts without overwriting later user changes; introduce safely versioned translucent Plank themes (0.2.0 RC3).
- [x] Coordinate live MacMenu and Control Center theme updates with MacBar's existing file monitor (0.3.0 RC1).
- [x] Historically added glass-day, glass-night and Aqua (0.3.0 RC1); the unfinished Liquid Glass presets were subsequently retired and are no longer available.
- [x] Add explicit Light/Balanced/Visual Control Center resource profiles and an on-demand PSS/CPU report (0.3.0 RC1).

## 0.2 — First real ThinkPad acceptance pass

- [ ] Confirm all three install or update cleanly on the owner's Linux Mint XFCE system.
- [ ] Verify Super-key open/close/open cycles and Control Center's fast D-Bus path.
- [ ] Confirm the actual selected WhiteSur or other GTK/icon themes are detected correctly.
- [ ] Validate Aurora Night/Day apply and rollback on the owner's real XFCE desktop.
- [ ] Check effective Plank theme, hide mode, pinned apps and autostart on the owner's Mint 22.1 / 1920×1080 session.
- [ ] Check keyboard focus, small displays, touch input and HiDPI.
- [ ] Compare settled PSS and CPU usage with and without XFCE Panel.
- [ ] Measure actual PSS, idle CPU and open/close latency on the owner's ThinkPad under each profile; do not claim unmeasured savings.
- [ ] Test the panel coexistence, login startup and an explicit rollback on the real machine.

## 0.5 — Coordinated update and recovery (historical objectives)

- [x] Add a revision-aware **fast-forward Git updater** with a checked official
  origin and archived rollback. Signed release checksums remain a separate gate.
- [ ] Give the manager a single backup/restore view across all three components.
- [x] Add concise, read-only health checks for missing GTK, NetworkManager,
  managed launchers and unsafe shortcut recovery state. Live xfconf conflicts
  still require owner testing.
- [ ] Add an opt-in migration path from older installations; never replace unrelated apps.

## 0.8 — Integration polish

- [x] Tie MacBar's theme/height/launcher configuration to event-based runtime reloads, with no polling.
- [ ] Test multi-monitor, work-area placement and suspend/resume on different XFCE setups.
- [ ] Improve accessible names and focus states based on real keyboard-only testing.
- [ ] Add a guided optional XFCE Panel replacement with verified rollback.
- [ ] Publish current screenshots from several real hardware setups.

## 1.0 — Stable rice distribution

- [ ] Fresh-clone installation succeeds on supported XFCE/X11 distributions.
- [ ] A guided upgrade from the standalone apps preserves all user settings and notes.
- [ ] Recovery is verified after a failed update and after a session restart.
- [ ] No unattended appearance changes: installer preserves the system, and opt-in full-rice changes can always be restored.
- [ ] No background services beyond the components the user enables.
- [ ] CI, packaging, documentation and a real-hardware acceptance checklist are green.
