# RiceHub changelog

## 0.6.0 — Seven installable rices (2 November 2026)

### New desktop families

- **Windows XP Luna:** blue taskbar, green Penguin Start, original grassland wallpaper, searchable applications and a native control panel.
- **Windows 98 / 2000 Classic:** square GTK/WM chrome, compact gray taskbar, narrow branded Start menu and original teal landscape.
- **ChromeOS:** pastel wallpaper, centered native shelf and launcher, pinned applications and XFCE-backed quick settings.
- **Y2K / Frutiger Aero:** original eco-futurist wallpaper, aqua GTK/window theme, translucent-looking taskbar and searchable application menu.
- All four ship original installable GTK3 and XFWM4 themes, icons, wallpaper artwork, themed Thunar styles and persistent pin files. The existing concept dialogs remain read-only.

### Session, safety and compatibility

- Apply, restore and switch among **seven** families using the single RiceHub session coordinator.
- Backups use schema 5 for additional autostart entries; supported older schema 1–4 snapshots remain readable.
- `Super_L` toggles the active rice's menu, `Control_R` its settings surface. The previous XFCE shortcuts remain recoverable.
- Inactive RiceHub taskbars are closed during handoff; Plank is reserved for the macOS rice. Third-party panel processes are not killed by unverified PID.
- Independent taskbar pin files prevent preferences from leaking between rices.
- Preserved the native Wnck window-lifecycle fix that prevents shell crashes after applications close.

### Verification

- 146 Python tests pass (one hardware-only test skipped in a non-X11 local run).
- GitHub Actions executes native GTK startup, search, menu/action toggles, real Wnck disposal and screenshot capture under isolated X11.
- Eight real GTK menu/controls screenshots are in [`screenshots/`](screenshots/), and the [README](README.md) shows each new style.

### Known limitations

- The 0.6 release has CI/virtual-X11 acceptance, not a completed physical Linux Mint XFCE hardware matrix. Before calling the project 1.0, verify login/relogin, multi-monitor, accessibility, compositor differences, rapid switching and repeat CADCraft close/reopen on physical hardware.
- No true compositor blur; native tray icons depend on host services. Legacy XEmbed tray is not supported.
- Windows 11 and Liquid Glass presets are not planned.
