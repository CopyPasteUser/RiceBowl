# Roadmap to 1.0

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

## 0.2 — First real ThinkPad acceptance pass

- [ ] Confirm all three install or update cleanly on the owner's Linux Mint XFCE system.
- [ ] Verify Super-key open/close/open cycles and Control Center's fast D-Bus path.
- [ ] Confirm the actual selected WhiteSur or other GTK/icon themes are detected correctly.
- [ ] Validate Aurora Night/Day apply and rollback on the owner's real XFCE desktop.
- [ ] Check effective Plank theme, hide mode, pinned apps and autostart on the owner's Mint 22.1 / 1920×1080 session.
- [ ] Check keyboard focus, small displays, touch input and HiDPI.
- [ ] Compare settled PSS and CPU usage with and without XFCE Panel.
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
