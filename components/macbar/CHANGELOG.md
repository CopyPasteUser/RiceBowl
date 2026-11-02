# Changelog

## 1.1.0 — 2026-11-02

- Live theme, height, launcher and battery-label configuration reload using a
  lightweight GLib file monitor; no periodic config polling or restart.
- Update the existing CSS provider in place instead of accumulating providers.
- Coordinate inverted Aurora Night/Day bar themes with the MacRice 0.2.0 RC2 suite.

## 1.0.0 — 2026-11-01

- Adaptive clock formatting and battery percentage on narrow displays.
- Safer network status behind VPNs, with asynchronous active-link inspection.
- Audio timeout handling and `pactl` fallback when `wpctl` is unavailable.
- No off-screen GTK hover tooltips or redundant indicator popovers; accessible
  descriptions remain available.
- Validation of configuration types, visible launcher-error state, version flag.
- Installer/autostart/rollback integration tests and removal script.
- Continuous integration, GitHub tag-release packaging, and full documentation.

Note: a native Linux Mint XFCE/X11 visual and PSS acceptance run is outstanding.

## 0.1.2 — 2026-11-01

- English UI, read-only network/audio/battery/clock indicators and actual
  Wi-Fi/Ethernet status through NetworkManager.
- Removed window-title text and popup menus; left space remains blank.
- Safe opt-in XFCE replacement after the new dock becomes visible.
