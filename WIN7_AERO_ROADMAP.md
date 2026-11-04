# Windows 7 Aero fidelity — implementation and acceptance

Status: Windows 7 cosmetic fidelity shipped to `main` via PR #14. The additional
Superbar milestone (grouping, previews, Jump Lists, Peek and latest gallery) passed
native Xvfb CI in pull request #15. Physical Mint/XFCE acceptance remains open. The published
`v0.9.1` package is unchanged. The second fidelity pass passed the complete
native Xvfb/GTK/XFWM4 CI matrix in PR #22 and received fresh gallery images;
physical Linux Mint acceptance remains open.

## Explorer fidelity refinement (implemented; native XFWM4 CI green)

- [x] Check original Microsoft Windows 7 Explorer behavior and Xfce's documented
  Thunar layout, toolbar, breadcrumb and configuration capabilities.
- [x] Hide Thunar's real menu bar under Seven and restore it when another rice
  is applied. Journal the setting, create it as xfconf Boolean and test the
  transition and restore path.
- [x] Flatten native toolbar buttons; join the breadcrumb/address field; remove
  boxed shortcuts-pane rows; style hover/selection, white file canvas, detailed
  list headers, statusbar and scrollbars.
- [x] Add 18 original scalable Explorer-era icons for folders, drives, network
  and actual MIME files, preserving exact old managed theme index fingerprints.
- [x] Migrate the 0.9.1 scoped Thunar CSS block without changing unrelated
  GTK CSS or overwriting personalized managed rules.
- [x] Add unit/integration checks, icon XML and GdkPixbuf decoding validation.
- [x] Inspect the real 1600×900 XFWM4/Thunar capture from green
  [CI run 41686544328](https://github.com/CopyPasteUser/RiceBowl/actions/runs/41686544328)
  and replace only the verified Aero workspace image in the current gallery.
- [x] Capture and visually inspect a real 1024×768 Thunar workspace (same CI
  run, separate artifact image). The complete window, controls and statusbar
  fit without screen-edge clipping; retain the full-sized image in the gallery.
- [ ] Confirm on the owner's Mint XFCE desktop that the toolbar's native menu
  or Ctrl+M/F10 still opens the hidden menu.

The current development runner cannot bind an X11 socket; the external native
CI supplied the verified workspace capture. Physical laptop QA remains open.
CSS cannot add
the original Explorer Libraries, bottom details/preview pane, or contextual
Organize/New folder toolbar to Thunar. No nonfunctional imitation buttons
are inserted.

Sources: [Microsoft Explorer controls](https://learn.microsoft.com/en-us/windows/win32/shell/developing-with-windows-explorer),
[Windows 7 libraries](https://learn.microsoft.com/en-us/windows/win32/win7devguide/managing-files-and-data),
[Xfce Thunar window and toolbar](https://docs.xfce.org/xfce/thunar/the-file-manager-window).

## Reference and constraints

Microsoft's original Windows 7 taskbar design emphasized an icon-first Superbar, persistent pins, grouped running apps, thumbnail previews, and Aero Peek. The classic Start menu had a searchable white program list, a translucent blue right-hand system-links pane, and a compact shutdown control. See the historical [Windows Experience taskbar design](https://blogs.windows.com/windowsexperience/2008/11/20/happy-anniversary-windows-7/) and [Microsoft Taskbar Extensions](https://learn.microsoft.com/en-us/windows/win32/shell/taskbar-extensions). These are behavior/design references, not distributable assets.

All art here is originally drawn. We do not import Microsoft logos, wallpapers, icons, fonts or binary theme files. The operating system remains XFCE/X11 with genuine Gio applications, Wnck window control, Thunar and XDG directories.

## Aero Seven Blue identity milestone

- [x] Replace both Frutiger-like landscape/water wallpapers with separately generated deep-blue Windows 7-era gradients and original frosted-glass Linux penguin art.
- [x] Keep saved rice keys and backup compatibility while renaming the user-facing variants Aero Seven Blue / Night.
- [x] Recolor only Windows 7's taskbar and Start frame to smoke-blue 2009 Aero glass; Frutiger Aero keeps its own turquoise/green design.
- [x] Make Windows 7 folder and library icons gold/yellow instead of turquoise glass; whitelist only exact previous managed icon blobs for safe upgrades.
- [ ] Complete physical Linux Mint XFCE wallpaper, taskbar, icon and profile-switch acceptance (including relogin and user-edited theme conflict).

## Completed implementation tasks

- [x] Dedicated 42px Windows 7 Superbar; use an icon-only original Aero penguin Start orb.
- [x] Icon-first running task buttons with glass rollover and active-state backplates; preserve per-window Wnck switching, user pins, right-click pin management and window overflow.
- [x] New two-pane actual GTK Start menu: pinned/recent program priority, All Programs, live search, user avatar, native filesystem locations and Control Panel/Printers launchers.
- [x] Disabled, explained actions when the installed tool or directory does not exist, rather than a nonfunctional imitation.
- [x] Orange session-dialog shutdown affordance, not an unconditional poweroff command.
- [x] Repaint original XFWM4 top/corner/side frame assets and window controls (normal, inactive, hover, pressed).
- [x] Draw distinct document, photo, music and download icons in the Aero icon theme; load them in the Start menu even before the theme is installed.
- [x] Tune GTK3 and Thunar palette: white Explorer-style file views, cyan glass toolbars, pale-blue navigator, Windows-era button/scrollbar treatments.
- [x] Workarea-aware menu, 1024x768 screenshots and dedicated tests for compact task capacity, menu ordering, artwork and asset migration.
- [x] Whitelist the exact previous managed Aero assets, while rejecting unexpected user edits; automatic installation remains reversible.

## Superbar fidelity milestone

- [x] Inspect CI's **actual X11** 1600x900 and 1024x768 Aero screenshots; menu and control popup remain within the usable monitor.
- [x] Group running X11 windows by actual WM_CLASS, keeping unidentified windows separate and the active group visible when overflowing.
- [x] Hover/click GTK popover with real titled window choices, bounded best-effort X11 thumbnails and safe icon fallback. Test native popover creation inside Xvfb.
- [x] Right-click a running app to switch or request a window close; allow opening and pinning only when an installed `.desktop` launcher can be identified unambiguously.
- [x] Pinned-app Jump Lists: genuine compatible local recent documents, actual app launch, and validated pin/unpin; never fake file history.
- [x] Show Desktop Peek: delayed hover temporarily reveals desktop, pointer leave restores previous state, click commits; no destructive window minimize sequence.
- [x] Replace old RC screenshots with checked-in captures from the latest green CI run; display only the current six-shell gallery in README and component docs.

## Remaining physical acceptance and deeper fidelity

### Second fidelity pass (native Control Panel and Superbar)

- [x] Replace the four-tile fake Control Panel layout with the eight real
  Windows 7-era category groupings (Microsoft historical reference), backed by
  actual installed Linux settings applications.
- [x] Provide a true decorated, task-switchable Control Panel window with
  category/detail/back navigation, nested search and disabled missing tools.
- [x] Replace inconsistent and missing inherited category icons with eight
  original, distinctive Aero SVGs; validate XML and GdkPixbuf decoding.
- [x] Keep existing verified audio/network/battery controls behind an explicit
  Linux-device expander instead of displaying them as Windows category tiles.
- [x] Make Start's Control Panel link open that window; remove the extra gear
  button from the notification area, keeping `Control_R` as a keyboard route.
- [x] Size Aero's Superbar to the 48px Windows 7 taskbar guideline and prefer
  Wnck's full-resolution icon for live task buttons.
- [x] Add pure category/action tests and a native GTK smoke/navigation check;
  isolate XFWM4 in the virtual-X11 Control Panel capture.
- [x] Confirm fresh 1600×900 and 1024×768 CI captures, inspect the resulting
  Start/Control Panel/Thunar screenshots, then update the current gallery.

- [ ] Physically test on the owner's Mint XFCE laptop at its own DPI and one external monitor: menu anchor, dock struts, Thunar, sound/battery/network widgets, pin/unpin, All Programs, Super_L and Control_R.
- [ ] Run repeated seven-rice switches, Plank autostart reconciliation and login/re-login regression; verify an existing customized theme still blocks automatic overwrite.
- [ ] Full Microsoft DWM-like Peek compositing, occluded-window thumbnails and Windows 7 thumbnail close glyphs remain outside GTK/Wnck parity. X11 previews depend on drawable visibility, and the implemented Peek is temporary Show Desktop, not full compositor transparency.
- [ ] Decide release version after owner's physical acceptance; do **not** label this branch a released 0.9.1 update.

## Rollback

Keep the prior release/tag intact. Switch back via RiceBowl's backed-up rice restore workflow, or use a fresh checkout of the previously shipped release. Never delete user-modified themes automatically.

## Completion backlog — convincing everyday Windows 7 Aero (4 November 2026)

**Goal:** The live Windows 7 rice must remain recognizably **Windows 7**, not Frutiger Aero or a blue-tinted XFCE desktop, through the second and third click. This section is an **open acceptance backlog**, not shipped functionality; all checked historical milestones above remain valid. Keep the original RiceBowl/Linux artwork policy.

### P0 — Close the biggest depth and functionality gaps

- [ ] **Authentic notification area and native-feeling flyouts:** small Aero-style controls anchored to the corresponding Superbar icon. Audio: real volume/mute and output switching; network: actual wired/Wi-Fi status, discovery, connect/disconnect through NetworkManager; power: battery/charge, supported brightness and power profile; clock: date/calendar; Bluetooth: adapter/device view when installed. Display success only after verifying the backend state. Handle absent hardware, offline mode, permission errors, timeouts and unsupported actions honestly. This is Windows 7's notification area, **not Windows 10's Action Center**.
- [ ] **Control Panel interaction and icon polish:** audit category, detail, search, back/forward and Classic-equivalent applet navigation through several clicks; retain the eight already-working Windows 7 category groups and real Linux actions. Ensure distinctive original Aero icons (including fallbacks), Windows 7-style links, breadcrumbs, search, focus/hover/disabled/error states and usable dialog sizes. Remove visual remnants of the earlier fake four-tile view.
- [ ] **RiceExplorer structural Windows 7 skin and safe integration:** do not mistake Thunar CSS for Windows Explorer parity. Implement Explorer-specific navigation hierarchy (Favorites, Libraries, Computer, Network), address breadcrumbs and search box, command bar (Organize/Open/Share with/New folder), views, bottom details pane, optional preview pane, file properties, contextual menus, meaningful progress/conflict dialogs, thumbnails and media previews. Integrate real local files, removable drives, mounts, trash, SMB/SFTP/network shares and genuine copy/move/rename/delete/undo operations through riceExplorer's shared safe backend. Libraries must map to actual indexed locations rather than pretend virtual folders. Keep Thunar fallback until transfer/mount/recovery acceptance passes.
- [ ] **Physical Mint/XFCE acceptance:** validate network/audio/battery/brightness and the UI on the owner's ThinkPad, external HDMI, login/relogin, suspend/resume, Plank autostart, taskbar workarea, switch/restore and recovery across all seven rice families.

### P1 — Make the complete shell coherently Windows 7

- [ ] **Superbar precision:** retain working WM_CLASS grouping, pinned/running separation, native previews, Jump Lists and Peek; refine thumbnail labels and close actions, group counts/overflow, button states, tooltip geometry, pin/unpin context menus, notification-area overflow chevron, Show Desktop hit area and user-adjustable taskbar size/auto-hide/lock. Jump Lists must show only real app actions and available recent documents.
- [ ] **Aero Peek, Snap and window interactions:** improve compositor-compatible translucency and peek previews where X11 supports them; implement/validate Aero Snap (drag to edge and keyboard shortcuts), maximize/restore drag handling and optional Shake without replacing XFWM4 recklessly. When true DWM occluded-window previews or per-window blur are unavailable, use an explicit best-effort fallback, not fake screenshots or destructive minimize sequences.
- [ ] **Desktop surface:** real Computer, Network, Documents and Recycle Bin shortcuts, correct original icon style and labels/shadows, adjustable alignment/grid and selection, drag/drop, sort/refresh/new/properties context menu and genuine trash. Keep the desktop wallpaper unmistakably Windows 7-inspired, with an original Linux visual; never drift back toward Frutiger's water/green palette.
- [ ] **Start menu depth:** preserve two-column translucent layout, real app/file search, pinned and recent programs, All Programs, documents/locations, Control Panel and session power controls. Polish submenus, per-app context actions, keyboard navigation, focus ownership, empty/no-result states, hover timing, scroll behavior and small-screen placement.
- [ ] **Dialogs and systemic surfaces:** coherent Aero-styled RiceBowl-owned file/confirmation/permission/error dialogs, progress bars, tooltips, menus, tabs, checkboxes, radio/scrollbar controls, properties, live taskbar previews and applet windows. Correct colors and glyphs through the entire interaction chain; do not leak Windows XP, Frutiger Aero or generic flat GTK elements into first-party Windows 7 screens. Clearly document third-party GTK4/Qt/Electron theming limits.
- [ ] **Action Center-era notifications:** Windows 7-style white-flag alerts, actionable notification balloons and real device/network/transfer events, respecting quiet behavior and dismissal. Do not transplant a Windows 10 notification panel.
- [ ] **Fine-grained theme consistency:** original Aero-era blue titlebar/buttons/glass, 16/24/32/48px icons, Windows 7-inspired typography and cursor, consistent dialogs, and well-defined keyboard/focus/reduced-motion behavior. Validate readable active and inactive states without fragile global CSS overrides.

### P2 — Optional Windows 7 finishing touches

- [ ] **Session experience:** optional Windows 7-style lock/login/logout/shutdown transitions through supported XFCE/LightDM APIs only, explicitly enabled with backup and rollback; never silently replace the display manager.
- [ ] **Sound and animation:** optional original or properly licensed Windows 7-inspired system sounds, subtle opening/closing/hover animations and optional desktop gadgets (for example a clock), all resource-bounded and disabled for reduced motion or lightweight mode.
- [ ] **Advanced OS-era polish:** real Devices and Printers, personalization, network-sharing, accessibility, file history/backup entry points where a Linux equivalent exists; clearly state when a feature is unavailable rather than displaying fake Windows controls.

### Architecture and definition of done

- **Shared functionality, distinct skins:** RiceBowl owns session management, the Windows 7 shell/Superbar/Start, tray integration, wallpaper and reversible settings. **riceExplorer owns filesystem actions and its structurally unique Windows 7 Explorer view.** Never duplicate file-transfer logic across repositories or reuse the XP/Frutiger layout as a recolor.
- Any visible control must **work, be clearly disabled with a reason, or not appear**. Include loading, empty, offline, backend-failure, permission-denied and successful completion states; verify the actual state after hardware-changing actions.
- Automated regression and visual acceptance: current-revision native GTK/XFWM4/X11 captures of Start and deep menus, Control Panel home/detail/search, grouped Superbar hover thumbnails and Jump Lists, tray flyouts, original-window and riceExplorer content. Check popup bounds, keyboard/focus, 800×600, 1024×768 and 1600×900, and prevent CSS/icon leakage into all other rices.
- Final owner acceptance on Linux Mint XFCE: repeated seven-rice apply/switch/restore with existing Plank autostart, external HDMI, login and resume, real file transfers/mounts, settings launching, keyboard shortcuts, taskbar behavior, upgrade and rollback; measure actual startup, idle CPU and PSS on the ThinkPad. Refresh README screenshots only from the passing revision.
- Do not call Windows 7 **fully finished or 1.0-stable** until the above required checks pass. Original RiceBowl artwork and functional Linux equivalence remain mandatory; binary/pixel identity with proprietary Windows DWM is not promised.

**Scope:** Windows 7 Aero only. Do not compromise the separate Frutiger Aero identity or alter other rices without cross-rice regression tests.
