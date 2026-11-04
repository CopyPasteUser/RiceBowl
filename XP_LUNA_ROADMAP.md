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
  category / classic switch and real Linux settings tasks. The blue
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

## Completion backlog — convincing everyday XP Luna (4 November 2026)

**Goal:** The desktop should still feel like Windows XP after the *second and third click*, while every visible operation remains a genuine, reversible Linux action. This is the **open acceptance backlog**, not a list of shipped features. It complements the completed stages above.

### P0 — Close the most visible interaction gaps

- [x] **Control Panel icon fidelity:** replace washed-out/generic or missing category and applet glyphs with one original, coherent, vivid XP-style set. Validate each category, task page and Classic View at actual 16/24/32/48 px sizes; preserve readable focus, disabled, hover and high-contrast states. Keep the existing working category → task → Linux utility navigation and search. (Automated SVG/GTK sizing covered; owner visual signoff remains.)
- [ ] **Native-feeling notification-area flyouts:** provide small Luna-styled, focus-safe popups anchored to the clicked tray icon — not a modern combined Control Center. Audio needs a verified volume slider, mute and output selection; network needs real connection information and Wi-Fi discovery/connect/disconnect through NetworkManager; power needs battery/charge information, supported brightness and power-profile controls; clock needs date/calendar; Bluetooth needs an actual adapter/device view when available. Missing hardware or permissions must produce honest disabled/error states. Never optimistically claim a system change succeeded.
- [ ] **RiceExplorer handoff and integration:** adopt riceExplorer for `winxp` only once its real file operations, trash, removable media, SMB/SFTP/network locations, mounts, errors and recovery are accepted. Its XP skin must change **structure**, not only colors: My Computer device/volume view, Explorer command/address/navigation bars, context-sensitive File and Folder Tasks sidebar, details, icons, property sheets, copy/move/progress dialogs, views/groups/thumbnails/filmstrip and actual context menus. Keep a functioning Thunar fallback, with no silent changes to file associations.
- [ ] **ThinkPad hardware validation:** verify all P0 popups with real Wi-Fi, audio, battery/charging and brightness; also test external HDMI, wake from suspend, login/relogin, Plank autostart and repeated switching/restoring across all seven rices.

### P1 — Make every interaction consistently XP

- [ ] **Desktop surface:** authentic My Computer, My Documents, My Network Places and Recycle Bin launchers with correct destinations; independently configurable grid, icon size, label shadow, selection/drag behavior, context menu (Arrange Icons, Refresh, New, Properties) and a real trash backend. Reuse XFDesktop where sufficient; isolate additional desktop-shell behavior if it cannot represent the layout.
- [ ] **Taskbar completeness:** Quick Launch behavior, pinned/running distinction, grouping and overflow, XP-like active/inactive/window-button states, notification-area overflow/chevron, taskbar and Start properties, right-click menus, optional auto-hide/lock, clock tooltip/calendar and predictable show-desktop handling. Preserve keyboard navigation and real window activation.
- [ ] **Dialogs and menus:** apply consistent Luna styling to RiceBowl-owned confirmations, context menus, progress/errors, tooltips, search, property views, nested flyouts, tabs, scrollbars, checkboxes and focus rings. Keep sensible geometry at 800×600, 1024×768, 1600×900 and with external-monitor placement. Clearly document any limitation in third-party GTK4/Qt/Electron apps.
- [ ] **Notification balloons:** classic taskbar-anchored, dismissible informational balloons for real events (network, removable devices, low battery, transfer completion) with timeouts, nonintrusive behavior and no invented status.
- [ ] **Start-menu details:** usage-based recent programs, user-editable favorites and pin ordering, context actions, complete keyboard traversal, correct submenu ownership on focus shifts, real search/run targets, and a configurable layout that retains XP's two-column structure.
- [ ] **Icon and typography consistency:** consistent icon families across taskbar, app menu, Control Panel, Explorer, file types and dialogs; suitable original XP-inspired cursor/typographic treatment and restrained era-appropriate hover/pressed/disabled styling rather than modern generic stock widgets.

### P2 — Optional finishing touches without compromising XFCE

- [ ] **Session visuals:** optional Luna-inspired lock/login/logout/shutdown dialogs and user switching only through supported LightDM/XFCE integration with backup, opt-in enablement and rollback. Never replace the login manager unprompted.
- [ ] **Soundscape and motion:** optional original or appropriately licensed login/logout, notification and error sounds; short animations with reduced-motion support and minimal CPU overhead.
- [ ] **Expanded XP-era utilities:** coherent Help and Support, system information, display/network properties and accessibility entry points, each backed by a real Linux utility or marked unavailable; XP SP2-style Security Center is optional.

### Shared architecture and acceptance contract

- **RiceBowl owns** the launcher, taskbar, tray flyouts, session integration, system dialogs, desktop integration and reversible theme/preset configuration. **riceExplorer owns** filesystem operations and the structurally distinct XP Explorer presentation. Avoid duplicating its file-operation code in RiceBowl.
- Every rice may supply its own **layout, toolbar hierarchy, navigation, sidebar, context menus, controls, icon mappings, spacing and interaction rules** over a shared functional backend. XP must not accidentally inherit Windows 7/10/macOS components or CSS.
- Every visible action is **functional, explicitly unavailable with a useful explanation, or absent**. Test success, loading, empty, disconnected, permission-denied and backend-failure paths; never render decorative toggles as if they worked.
- Automated acceptance: native XFWM4/X11 screenshots of Start, nested All Programs, Control Panel category/detail/Classic/search, system-tray flyouts, actual Explorer and desktop; keyboard/focus and popup-bounds tests at multiple resolutions. Update the committed screenshot gallery from the same passing revision; do not reuse obsolete mockups.
- Final owner acceptance: install/update on Linux Mint XFCE, seven-rice switch/restore, rollback after failure, suspend/resume, dual monitors, real network/mount/file operations and idle CPU/PSS/startup measurements on the ThinkPad. No claim of XP Luna 1.0 completeness before these pass.

**Scope:** these are XP-specific product goals. Do not redesign the other rice identities or replace working XFCE services as a side effect.
## Notification-area and original icon pass — November 2026

- [x] Replace missing GTK symbolic icon fallback with nine original, recognizable
  3D Luna Control Panel category devices and individually badged applet SVGs.
- [x] Keep artwork reproducible through `scripts/build_luna_control_icons.py`;
  install it only into XP's icon theme, preserving all other rices.
- [x] Audio icon: small native GTK flyout with verified volume slider, mute,
  selection among real PulseAudio/PipeWire output devices, and settings link;
  Control Panel uses the same output backend.
- [x] WLAN icon: real NetworkManager radio state, sorted nearby SSIDs, refresh,
  join/disconnect actions and connection editor, with asynchronous error/empty states.
- [x] Battery icon: accurate battery state, optional verified brightness slider,
  supported power profiles and settings; desktops show an honest no-battery message.
- [x] Bluetooth icon: live BlueZ adapter state and connected devices, verified
  power action and Blueman settings; unavailable adapters reported as such.
- [x] Clock: clickable calendar popup with date/time settings.
- [x] Start favorites/context actions are independent of taskbar pins, have
  reversible ordering, and successful launches populate a bounded recent list.
- [ ] Validate screenshot regression captures for five popovers and original
  icons at 1600×900 and 1024×768 in native GTK CI (coverage implemented).
- [x] Add focused backend and SVG contract tests for the tray and Control Panel.
- [ ] Hardware acceptance on the owner's physical Mint XFCE laptop: real audio,
  NetworkManager connection changes, backlight permissions, focus, external monitor.
