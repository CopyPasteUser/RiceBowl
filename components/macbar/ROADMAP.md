# MacBar roadmap — toward 1.0

The 1.0 scope is a dependable, low-overhead **XFCE/X11 top bar** that cooperates
with MacMenu, Control Center and Plank. It deliberately does not implement a
task list, arbitrary tray protocol, global app menu, or second Control Center.

## 0.1 — Foundation (complete)

- [x] Native GTK3/X11 dock window with top screen reservation
- [x] MacMenu on the left, network/audio/battery/Control Center/clock on the right
- [x] English descriptions, theme configuration, no task list
- [x] Wi-Fi vs Ethernet primary link identification

## 0.3 — Interaction and stability (complete)

- [x] Remove secondary status popovers and unintended click actions
- [x] Eliminate GTK hover tooltips that escaped the top screen edge
- [x] Keep accessible descriptions for read-only status elements
- [x] Show launcher errors without a floating dialog

## 0.6 — Laptop and connectivity (complete)

- [x] Compact clock and battery text on small displays
- [x] Follow primary monitor geometry changes
- [x] Detect underlying Wi-Fi/Ethernet when a VPN is primary
- [x] Fall back from unavailable `wpctl` to `pactl`, without blocking GTK

## 0.8 — Integration and recovery (complete)

- [x] Install and autostart as an unprivileged user
- [x] Replace XFCE Panel only after MacBar is visible
- [x] Preserve existing configuration on reinstall
- [x] Add safe removal and explicit XFCE Panel recovery instructions

## 1.0 — Release baseline (code complete)

- [x] Version reporting, configurable dark/light themes
- [x] Headless tests for status, responsive layout and installer/rollback
- [x] CI and tag-triggered GitHub ZIP release workflow
- [x] README, CHANGELOG, license and contributor/security notes
- [ ] **On-device acceptance:** live X11 visual check at native and narrow
  resolutions, reliable MacMenu/Control Center toggles, resume from suspend,
  XFCE session behavior after login, and measured PSS vs XFCE Panel.

The last checkbox requires the target Linux Mint/XFCE desktop; headless tests
cannot honestly prove appearance, compositor behavior, or RAM savings.

## After 1.0 (not 1.0 requirements)

- Optional desktop setting to choose which status indicators are visible
- Event-driven audio updates if measurements show periodic polling matters
- Opt-in System Tray protocol support if tray-only applications require it
- Multi-monitor placement mode without incorrect EWMH struts
