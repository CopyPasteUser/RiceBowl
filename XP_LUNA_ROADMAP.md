# XP Luna fidelity roadmap

Scope: the live `winxp` GTK/XFWM/X11 rice, not the read-only preview or other desktop families. The target is **the 2001 Windows XP Luna Blue layout language**, recreated with original RiceBowl artwork and functional Linux equivalents. Microsoft icons, the Windows wordmark and Bliss photograph are not bundled.

## Visual reference and non-negotiable behavior

- Windows XP Visual Guidelines: [Start menu](https://www.retrospace.net/download/WebApplications/WindowsXPDesignGuidelines/whatsnew.htm), [controls](https://www.retrospace.net/download/WebApplications/WindowsXPDesignGuidelines/controls.htm), [colors](https://www.retrospace.net/download/WebApplications/WindowsXPDesignGuidelines/colors.htm).
- 2001 structure: cobalt account/header band, two-column ivory/soft-blue menu, pinned Internet/e-mail and recent programs, All Programs flyout, common folders plus Control Panel/Help/Search/Run, separate yellow Log Off and red power actions.
- Compact molded cobalt taskbar with green Start button, darker active tasks and one brighter blue notification area; rounded blue title bar, individually colored minimize/maximize/close controls, readable classic file-manager controls.
- Every enabled menu entry launches a real installed application, folder or XFCE utility; missing backends are disabled with an explanation. Preserve app search, keyboard access, pinning, Wnck tasks, volume/battery/network reporting, session restore and the verified 0.9.1 handoff.

## Implementation stages

### P0 — Reference and safety

- [x] Inventory existing XP-specific widgets, CSS, generated XFWM/GTK assets and the historical-asset migration guard.
- [x] Use historical layout/color guidelines as a fidelity baseline; record original-art constraint.
- [ ] Measure initial vs final real GTK captures side by side at 1600×900 and 1024×768.

### P1 — Start menu anatomy

- [x] Replace generic search-first menu with a period-appropriate split program list and system navigation.
- [x] Add functional All Programs cascade, in-menu Search/Run, recent documents and category separators.
- [x] Align avatar, columns, footer buttons, hover/focus states and popup geometry, with scrollable right links.

### P2 — Taskbar and status area

- [x] Profile-specific compact panel height, green Start geometry, blue task buttons and active/hover states.
- [x] One bright cyan notification area, single-line clock and original status icons; preserve live state.
- [ ] Verify Wnck window buttons, launcher pins, overflow, keyboard shortcuts and workarea struts.

### P3 — Desktop chrome and assets

- [x] Handcraft original Luna-inspired blue XFWM4 titlebar/corner/button states, with reproducible sources.
- [x] Layer era-appropriate GTK buttons, tabs, selected rows and menus over preserved Thunar toolbar/sidebar chrome.
- [x] Add six original Luna app/system glyphs and a separate original user avatar.
- [x] Extend exact v0.9.1 asset-hash migration trust only for replaced assets; never overwrite user edits.

### P4 — Release gate

- [x] Extend pure-Python Luna layout, app discovery, icon and migration unit tests.
- [ ] Run all six-profile virtual-X11 smoke/gallery checks on GitHub Actions.
- [ ] Validate no collisions at 1600×900 and 1024×768, inspect real captures, and audit focus/empty/error states.
- [ ] Re-test on the owner's Mint XFCE laptop: external monitor, login/relogin, rapid rice switching, Plank autostart, volume/network/battery.
- [ ] After acceptance, publish as the next RiceBowl pre-release with updated readme, evidence and checksum.

## Fidelity ceiling

XFWM4/GTK3 cannot reproduce proprietary Windows Explorer internals or the exact original `msstyles` theme engine. Windows XP visuals here are reimplemented over Linux rather than copied bitmaps or a Windows session. The target is a convincingly faithful daily-driver rice, not a claim of binary/pixel identity with Windows XP.
