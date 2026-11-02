# MacRice engine roadmap to 1.0

**RiceHub is now the umbrella application.** Release 0.6.0 introduces installable XP Luna, Windows 98/2000, ChromeOS and Frutiger Aero styles alongside macOS, Windows 7 and Windows 10. The new desktops share the tested session/recovery engine; physical Mint XFCE validation is still required for the 1.0 hardware-stability milestone. The original read-only design previews remain available. Unfinished Liquid Glass presets and Windows 11 are not planned. See the [new-rice acceptance checklist](CONCEPTS.md) and [RiceHub roadmap](RICEHUB.md#product-roadmap).

MacRice is deliberately a thin integration layer. MacMenu, Control Center and MacBar keep their own tested lifecycles; Plank remains an external system dock.

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

## 0.5 — Coordinated update and recovery

- [ ] Add a revision-aware updater that can verify signed release checksums.
- [ ] Give the manager a single backup/restore view across all three components.
- [ ] Add concise health checks for missing GTK, NetworkManager, icons and shortcut conflicts.
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
