# RiceBowl 0.9.0 — Four native desktop identities

This pre-release translates four user-supplied desktop concept screenshots into **actual RiceBowl Python/GTK3 and XFCE theme code**. It does not present image mockups as implemented features. macOS rice and the working session switching/restore engine are intentionally untouched.

## XP Luna
- Independent two-column Start menu with account header, real installed applications, Places folders and Log off / Turn off session dialogs.
- Saturated blue taskbar, green Start button, raised active tasks, classic blue system status and an XP-style categorized Control Panel.
- Warm file-menu colors, glossy file-manager toolbar, blue sidebar and period-inspired path buttons.

## Windows 98 / 2000 Classic
- Compact, sharp-edged Start menu with navy vertical rail and **real cascading Programs categories** built from installed desktop applications.
- Functional Find search, settings, home/computer shortcuts and session dialog. Square gray beveled taskbar, recessed status controls and classic column/list styling in Thunar.

## ChromeOS
- Searchable **12 real installed apps** launcher grid (no fake app tiles).
- Separate launcher button, centered dock shelf with pinned/running apps, and grouped right-side status indicators.
- Soft lilac/white UI, rounded controls and a pill-shaped file-manager path/toolbar.

## Y2K / Frutiger Aero
- Aqua dashboard with working **Apps / Places / Settings** tabs and real folders and XFCE tools, glossy cyan taskbar and green selection accents.
- Luminous native GTK3 file manager chrome, cyan/glass toolbar, lime selected rows and aqua status controls.

## Better hardware controls
- Battery percentage and charging state are read from Linux power_supply; machines with no battery do not display a fabricated battery.
- Actual Wi-Fi/Ethernet/VPN-underlay detection and read-only network state.
- Real sound volume slider and mute button, using bounded PipeWire/WirePlumber or PulseAudio calls with read-back verification. Unsupported backends remain disabled; errors are displayed, not simulated.

## Upgrade safety and icons
- 36 new illustrated folder, media, device, and network SVGs across the four profiles, protected against regeneration.
- Trust exact official 0.8 theme hashes during upgrades and transparently migrate unchanged old 0.8 Thunar CSS blocks while preserving unrelated personal CSS.
- Existing system settings, Plank preferences, RiceHub legacy aliases and backing up/restoring desktop state are preserved.

## Verification and limitations
GitHub Actions must pass Python/GTK regression suites, native XFCE/X11 smoke and window-lifecycle tests, and produce 12 non-identical valid GTK screenshots before publication. This is a **pre-release** pending acceptance on a physical Linux Mint XFCE machine (battery, Plank, displays, repeated switching).

**Stock Thunar limitation:** Thunar's GTK3 widgets are styled natively. The screenshot references show some custom-designed file-manager dashboards (e.g. Recent/download content sections) which cannot be reproduced by GTK CSS alone; no separate fake file-manager UI is shipped. This release retains the real file manager and its capabilities.

## Update
Clone or pull the canonical repository, run bash install.sh --dry-run, then bash install.sh --no-start; launch with ~/.local/bin/ricebowl. Do not run the installer as root. Use the built-in **Repair local theme assets…** action only if a customized local theme blocks normal updating.

Repository: https://github.com/CopyPasteUser/RiceBowl
