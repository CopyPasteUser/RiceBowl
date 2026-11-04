# XP Luna fidelity roadmap

Scope: the live `winxp` GTK/XFWM/X11 rice, not the read-only preview or other desktop families. The target is **the 2001 Windows XP Luna Blue layout language**, recreated with original RiceBowl artwork and functional Linux equivalents. Microsoft icons, the Windows wordmark and Bliss photograph are not bundled.

## Visual reference and non-negotiable behavior

- Windows XP Visual Guidelines: [Start menu](https://www.retrospace.net/download/WebApplications/WindowsXPDesignGuidelines/whatsnew.htm), [controls](https://www.retrospace.net/download/WebApplications/WindowsXPDesignGuidelines/controls.htm), [colors](https://www.retrospace.net/download/WebApplications/WindowsXPDesignGuidelines/colors.htm).
- Microsoft's [Control Panel category registry](https://learn.microsoft.com/en-us/windows/win32/shell/assigning-control-panel-categories) confirms the nine XP-era categories, including Accessibility Options.
- 2001 structure: cobalt account/header band, two-column ivory/soft-blue menu, pinned Internet/e-mail and recent programs, All Programs flyout, common folders plus Control Panel/Help/Search/Run, separate yellow Log Off and red power actions.
- Compact molded cobalt taskbar with green Start button, darker active tasks and one brighter blue notification area; rounded blue title bar, individually colored minimize/maximize/close controls, readable classic file-manager controls.
- Every enabled menu entry launches a real installed application, folder or XFCE utility; missing backends are disabled with an explanation. Preserve app search, keyboard access, pinning, Wnck tasks, volume/battery/network reporting, session restore and the verified 0.9.1 handoff.

## Implementation stages

### P0 — Reference and safety

- [x] Inventory existing XP-specific widgets, CSS, generated XFWM/GTK assets and the historical-asset migration guard.
- [x] Use historical layout/color guidelines as a fidelity baseline; record original-art constraint.
- [x] Compare initial vs final real GTK captures at 1600×900 and 1024×768,
  including the XP Control Panel and a genuine XFWM/Thunar workspace.

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
- [x] Run all six-profile virtual-X11 smoke/gallery checks on GitHub Actions
  (`41691336596` green, 3 November 2026).
- [x] Validate the new XP Control Panel, Start and Thunar at 1600×900 and
  1024×768 using native X11 captures; unit and smoke tests cover keyboard,
  category/classic transitions, disabled actions and menu geometry.
- [ ] Re-test on the owner's Mint XFCE laptop: external monitor, login/relogin, rapid rice switching, Plank autostart, volume/network/battery.
- [ ] After acceptance, publish as the next RiceBowl pre-release with updated readme, evidence and checksum.

## Fidelity ceiling

XFWM4/GTK3 cannot reproduce proprietary Windows Explorer internals or the exact original `msstyles` theme engine. Windows XP visuals here are reimplemented over Linux rather than copied bitmaps or a Windows session. The target is a convincingly faithful daily-driver rice, not a claim of binary/pixel identity with Windows XP.

## Follow-up fidelity pass — November 2026

The 2001-era Start/taskbar artwork from the first pass remains. The screenshot
review revealed that the **file-manager interior** was still too glossy/modern,
the **Control Panel** resembled a narrow notification popup, and missing XDG
folders produced unexpectedly inert Start links. These improvements are scoped
to `winxp` only:

- [x] Build a centered XP-like category Control Panel window with an actual
  category / classic switch and eight real settings launch targets. The blue
  sidebar retains accurate network/battery information and verifiable output
  volume/mute controls, even when an external sound backend is unavailable.
- [x] Make Start > Control Panel open that same native panel, eliminating two
  conflicting Windows settings destinations.
- [x] Resolve My Documents / My Pictures / My Music via real XDG user dirs;
  if one does not exist, offer to create it **only after explicit confirmation**.
- [x] Align the recent-documents link and order its real file submenu by date.
- [x] Add an isolated `LUNA_EXPLORER_CSS` layer over the exact previous managed
  Thunar CSS so user overrides are preserved and old installed blocks migrate.
- [x] Update screenshot position validation for the centered XP Control Panel.
- [x] Unit-test applet discovery, directory permission prompts, CSS migrations
  and absence of cross-profile styling.
- [x] Inspect passing native 1600×900 and 1024×768 screenshots and republish
  the current gallery from that precise passing CI commit.
- [ ] Verify on the owner's physical Mint XFCE laptop (multimonitor, autostart,
  volume, actual applet availability and quick profile switching).

Remaining fidelity limit: Thunar's functional GTK shortcuts pane cannot be
turned into Windows Explorer's proprietary context-sensitive *File and Folder
Tasks* pane with CSS alone. The current UI styles real Thunar actions, never
adds fake filesystem operations or replaces its file-management engine.

## Deep interaction pass — November 2026

- [x] Style the actual detached GTK flyout windows, nested program categories,
  recent files and app pin contexts consistently in Luna blue/ivory.
- [x] Keep Start open while a nested menu owns focus; reset stale program search
  results on next open and expose all Gio programs, including uncategorized apps.
- [x] Restore XP's ninth Accessibility Options category and replace direct-launch cards with category/task navigation,
  Classic applet view, searchable tasks, back navigation and visible unavailable states.
- [x] Extend the central approved utility launch set so installed XP applets
  cannot silently fail after their first click.
- [x] Cover the deeper interaction states in the native GTK smoke and virtual-X11
  capture workflow; retain 1024×768 coverage and all six non-macOS profiles.
- [ ] Physically verify nested flyout placement, keyboard/mouse focus and applet
  launch paths on the owner's Mint XFCE laptop after the CI build passes.

### Gaps that require a separate component

- **riceExplorer integration**: true XP Explorer navigation/task pane, file copy
  dialogs, multi-drive *My Computer*, property sheets, shared folder context menus,
  thumbnails and real file-management operations cannot be delivered reliably by
  changing Thunar's GTK stylesheet. Keep Thunar as a fallback until riceExplorer
  has passed real transfer, mount and recovery acceptance.
- **Optional desktop integrations**: a fully authentic XP notification balloon,
  logon/logoff experience or Windows-style desktop icon grid would need a
  dedicated session/desktop component. Do not hijack XFCE's existing session
  controls or fabricate state for appearance's sake.
- **Normal RiceBowl work, no side project needed**: usage-based recently launched
  programs, better pinned Start favorites and context actions, fuller keyboard
  traversal, date/time settings discovery and user-configurable Start menu layout.
