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
  [CI run 41685514010](https://github.com/CopyPasteUser/RiceBowl/actions/runs/41685514010)
  and replace only the verified Aero workspace image in the current gallery.
- [ ] Inspect a separate real 1024×768 Thunar workspace capture. The CI run
  already verified 1024×768 Start/Control Panel but captures Thunar at 1600×900.
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
