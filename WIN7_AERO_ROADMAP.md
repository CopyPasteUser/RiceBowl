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

### P0 progress — Aero notification flyouts and Control Panel depth

- [x] Add five independently styled Windows 7 tray flyouts (volume, network,
  battery, Bluetooth, date/calendar) to the actual 48px Superbar.
- [x] Reuse bounded asynchronous, read-back-verified PipeWire/PulseAudio,
  NetworkManager, power-profile, brightness and BlueZ operations. Missing
  hardware and unsupported actions show unavailable states.
- [x] Provide an upright volume slider/mute/output drawer, Wi-Fi scan and
  connect/disconnect, battery/profile/backlight, Bluetooth adapter status,
  and a clickable calendar.
- [x] Add Category/Large icons/Small icons modes, Back/Forward navigation,
  third-level applet task pages and explicit missing-tool messages to the
  Windows 7 Control Panel.
- [x] Add an optional Start launch into Rust RiceExplorer `--theme win7` only
  when installed; keep Thunar and system file associations unchanged until
  RiceExplorer's transfer/mount/recovery acceptance passes.
- [x] Add focused regression assertions and native GTK/X11 smoke coverage.
- [ ] Review fresh real-X11 flyout and deep Control Panel captures, then update
  checked-in screenshots only from a passing revision.
- [ ] Verify sound, device switching, network, brightness, Bluetooth, DPI and
  popup placement on the owner's physical Mint XFCE ThinkPad.

**Still open:** SNI personalization, genuine Windows 7 balloon
events, deeper native applets, all physical acceptance, compositor limits and
the independent RiceExplorer file-job/network-mount roadmap. The umbrella
P0/P1/Sollkatalog checkboxes below stay open until fully accepted.

### P1 progress — authentic tray overflow and real desktop links

- [x] Hide application SNI icons after the first three inside a Windows 7
  Superbar chevron; prioritize `NeedsAttention` while keeping `Passive` hidden.
  A real GTK menu provides icon, title and actual application activation.
- [x] Preserve optional SNI behavior and unlimited layout in the other rice
  profiles; no new watcher, daemon, or global XFCE configuration.
- [x] Add opt-in Computer, Documents, Network and Recycle Bin desktop entries
  with genuine GIO locations and original active-theme icons. Only exact,
  unmodified RiceBowl Windows 7 entries can be removed. Existing user files,
  XP shortcuts and symlinks are preserved.
- [x] Wire the blank Superbar context menu to Show Desktop, reversible
  install/remove prompts and the actual XFDesktop personalization tool.
- [x] Add pure SNI ordering/overflow tests and filesystem rollback tests.
- [ ] Capture the opened chevron with populated test icons under X11; test real
  SNI activation/context and recovery when a process disappears.
- [ ] Physically validate XFDesktop launcher placement, permissions, GIO
  `computer:///`, `network:///`, `trash:///`, theme icons and multi-monitor.

### P1 progress — persistent per-app notification preferences

- [x] Implement a native Windows 7 dialog to choose maximum displayed SNI
  app icons and Automatic/Show/Hide placement for each running application.
- [x] Persist only stable StatusNotifier protocol IDs in a bounded, versioned
  JSON file with atomic writes, user-only permissions and explicit corruption/
  symlink rejection. Ephemeral DBus names never become saved identities.
- [x] Provide Restore defaults and apply preference changes immediately,
  preserving `NeedsAttention` priority for automatic apps and excluding passive
  entries. No other rice reads or writes this configuration.
- [x] Add targeted preference validation, migration-format, symlink,
  broken-file-preservation and icon-priority tests.
- [ ] Perform real GTK/X11 dialog and multi-SNI application interaction
  capture, including keyboard/focus, narrow-monitor placement and app restarts.

**Still open:** native Win7 balloon notifications, Snap/Shake fidelity,
deep applets and physical hardware acceptance.

### P1 progress — native window attention and reversible context-menu Snap

- [x] Read real X11 `needs_attention()` from Wnck state notifications and render
  an amber Aero Superbar state for inactive groups, including hidden members.
  The highlight is cleared when the native attention request clears or the
  requesting window gains foreground focus.
- [x] Add live per-window context-menu left/right half-tiling, maximize and
  restore (including previously maximized state). Group menus expose actions
  for each actual member without storing native Wnck window objects.
- [x] Choose the correct monitor's *available workarea* for half-tiling,
  excluding taskbar/dock struts; preserve odd widths and negative monitor
  coordinates; discard saved geometry when the window is closed.
- [x] Add pure geometry, maximization, missing/fullscreen-window and attention
  state tests, plus native GTK smoke assertions for attention and arrange menus.
- [ ] Validate actual XFWM4 geometry requests, focus/restore, cross-monitor
  behavior, minimize/maximize races and high-DPI rendering on Mint hardware.
- [ ] Implement and accept edge-drag Snap, reversible system keyboard shortcuts,
  Shake and optional visual tile preview without hijacking existing XFWM4
  window-management bindings.

The complete Superbar/Snap umbrella tasks below remain open. The available
right-click arrangement is **not** a substitute for edge-drag/keyboard Snap.

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


---

## Windows 7 SP1 Aero — vollständiger Sollkatalog und Abnahmeplan (2026-11-04)

> **Zielbild:** Ein Benutzer soll nach dem Login, nach fünf Klicks und nach einer
> Stunde echter Arbeit eine Windows-7-SP1-Aero-Desktop-Sitzung wiedererkennen.
> Nicht nur ein passendes Hintergrundbild: Informationsarchitektur, Größen,
> Beschriftungen, Popup-Geometrie, Interaktionsmodelle und Zustandswechsel müssen
> als zusammenhängende Shell stimmig sein. Der Linux-Unterbau bleibt echt,
> sicher und bedienbar.
>
> **Statusregel:** Alle Kästchen dieses Sollkatalogs sind offene
> Abnahmepunkte, sofern nicht ausdrücklich auf eine bereits bestandene
> historische Prüfung weiter oben verwiesen wird. Bestehende [x]-Milestones
> sind Implementierungsbelege für frühere Teilziele und **keine**
> Freigabe für die nachfolgenden Detailkriterien.

### 0. Historische Referenz und Abgrenzung (P0)

- [ ] **Version eindeutig fixieren:** Windows 7 SP1 mit aktivem Aero Glass,
  Standard-DPI 100 %, Standardtaskleiste unten; Windows 7 Basic und Classic
  als explizite Varianten, falls überhaupt implementiert. Keine Komponenten
  aus Windows 8, 10, 11 oder dem separaten Frutiger-Aero-Rice hineinmischen.
- [ ] **Referenzsatz anlegen:** Lizenzrechtlich zulässige Referenzbilder von
  Desktop, geöffnetem Startmenü, All Programs, Taskleistenvorschau, Jump List,
  Rechtsklick-Taskbar, Infobereich, Uhr, Explorer, Eigenschaften,
  Kopierdialog, Systemsteuerung, Personalisierung, Netzwerk/Batterie und
  Aero-Snap; Messwerte für Abstände, Radien, Farbverläufe, Icons und
  Schrifthierarchie hinterlegen.
- [ ] **Zustandsvergleich:** Für jedes Element Idle / Hover / Pressed / Focus /
  Open / Disabled / Busy / Error / Empty / Overflow / Keyboard definieren;
  nicht nur die schöne geschlossene Ausgangsansicht beurteilen.
- [ ] **Stimmigkeit:** Das Windows-7-typische blaue Licht-/Reflexionsbild
  mit Linux-Eigenständigkeit statt des frutiger-aero-eigenen Naturmotivs;
  keine Linux-Mint-Fremdfenster im Hauptfluss außer bewusst weitergeleitete
  Anwendungen.

### 1. Aero-Designsystem und Fensterdekor (P0–P1)

- [ ] **Farb- und Metrik-Tokens:** Blue-Glass, Border, Highlight, Shadow,
  Active/Inactive, Taskbar-Tint, Menü-Selektion, Status-Grün,
  Warnungs-Gelb, Fehler-Rot, Radius, Abstand und Animation definieren.
- [ ] **Aero-Glass-Material:** Transparenz, Hintergrundunschärfe sofern
  technisch zuverlässig verfügbar, mehrstufiger Glasrand/Reflexion,
  Textglow, richtiges Fensterschattenverhalten und maximierter Randzustand;
  klaren performanten Fallback ohne behaupteten Blur.
- [ ] **Fensterrahmen:** Titelleiste, App-Icon links, aktiver/inaktiver Titel,
  Minimize, Maximize/Restore, Close in Windows-7-artiger Größe/Position,
  Hover- und Press-Grafiken; maximiert vs. normal vs. Dialog.
- [ ] **Fensterinhalt:** Menüleisten, Toolbar, Breadcrumb, Treeview, Listen,
  Reiter, Buttons, Linklabels, Auswahlmarkierung, Scrollbar, Tooltip,
  Kontextmenü, Modalfenster, Dateidialog in konsistentem Windows-7-Look.
- [ ] **Typografie/Iconografie:** Segoe-UI-artige rechtmäßig verfügbare
  Schrift mit passenden Fallbacks, Textgrößen und Zeilenhöhen;
  Windows-7-Farbtiefe, Glanz und Perspektive für Icons; eigene/rechtlich
  sichere Assets, scharfe 16/24/32/48/256px-Varianten, keine Platzhalter.
- [ ] **Cursor/Sounds/Feedback:** originalnahe Mauszeiger, Busy/Working,
  Resize, Auswahlrahmen, Hover-Klangoption und kontextuelle Systemklänge;
  vollständig abschaltbar und ohne fremde Systemdateien zu übernehmen.

### 2. Superbar — ausnahmslos alle sichtbaren Zustände (P0)

- [ ] **Grundlayout:** Start-Orb links, große zusammengeführte Pin-/Running-
  Buttons, optische Glastrennlinien, rechter Systembereich, Show-Desktop-
  Streifen; Höhen und Icon-Baselines bei 100/125/150 % Skalierung prüfen.
- [ ] **Fensteridentität:** Laufende Apps anhand stabiler Desktop-ID/WM_CLASS
  gruppieren; mehrere Fenster mit Count/Stack erkennen; getrennte
  Fenster als Gruppe wie Win7 öffnen, minimieren, aktivieren.
- [ ] **Pins:** pin/unpin, Reihenfolge per Drag & Drop, Positionspersistenz,
  Start aus Pin, unterschiedliche Idle-/Running-/Attention-Zustände,
  fehlende Apps robust behandeln.
- [ ] **Hover-Vorschauen:** Fenstergruppen-Thumbnails in Live/Static-
  Fallbacks, App-Namen, Fenster-Close-Button, Klick zum Aktivieren,
  Hover auf Thumbnail für Peek, bei Mausabgang sauber schließen;
  null Fenster, ein Fenster und vier Fenster abnehmen.
- [ ] **Aero Peek:** rechter Show-Desktop-Schlitz als Hover-Vorschau,
  Klick minimiert/zeigt Fenster wieder; kein irreversibles Verstecken,
  keine Flackerschleife bei Autohide, korrekt auf mehreren Monitoren.
- [ ] **Jump Lists:** Rechtsklick auf Pin/aktive App für echte zuletzt
  verwendete Dokumente, häufige Ziele und app-spezifische Aktionen;
  'Pin to this list', Remove, Close Window, Unpin; keine toten Einträge.
- [ ] **Aufmerksamkeitszustände:** Fenster meldet Bedarf -> Button pulsiert/
  farbig markiert, Fokuswechsel löscht Zustand; optional App-Fortschritt
  und Overlay-Badge aus realen Ereignissen.
- [ ] **Taskbar-Kontext:** Toolbars soweit sinnvoll, Lock the taskbar,
  Task Manager starten, Properties/Preferences, Show Desktop, Cascade /
  Stacked / Side by side (technisch vorhandene Aktionen oder transparent
  begrenzte Optionen); Autohide/Höhenoptionen mit Restore.
- [ ] **Bildschirmkanten:** Taskbar unten/links/rechts/oben oder
  dokumentierte Win7-nahe Untermenge; Exklusivzonen respektieren,
  XFCE-Panel-/Plank-Doppelleisten vermeiden, Hotplug & Reconnect.

### 3. Startmenü — jede Ebene bis zur Zielaktion (P0)

- [ ] **Zwei-Spalten-Geometrie:** gläserner äußerer Frame,
  linke Favoriten-/Recent-Seite, rechte Systemziele, Benutzerbild oben,
  Search-Box unten, Power-Button mit Pfeil und korrektes Focus-Handling.
- [ ] **Linke Spalte:** pinned/recent Programme nach echten Nutzungsdaten,
  Trennlinien, Hover-States, 'All Programs' und Zurück;
  konfigurierbare Eintragszahl und ohne Duplikate.
- [ ] **All Programs:** verschachtelte echte Anwendungsgruppen,
  aufklappbar wie Windows 7, Tastatur-/Mausauswahl und Scrollposition;
  Fallback für riesige Linux-Anwendungskataloge.
- [ ] **Rechte Spalte:** Documents, Pictures, Music, Games (wenn vorhanden),
  Computer, Control Panel, Devices and Printers, Default Programs,
  Help and Support, User Folder; realen Zielpfad/Programmaufruf prüfen.
- [ ] **Suchen:** Programmnamen, Desktop-Entries, Dateien/Ordner und
  Systemsteuerungsziele per Tastatur; Sofortergebnisse mit
  Icon/Kategorie, Enter öffnet, Escape schließt; keine irreführenden
  globalen Dateitreffer ohne Index/Erreichbarkeit.
- [ ] **Kontextmenüs:** Programmpin, Unpin, Open file location,
  Run as administrator ausschließlich via polkit-konforme Wege,
  Properties, kürzlich benutzt; echte Semantik statt Label-Deko.
- [ ] **Power-Untermenü:** Shut down, Restart, Sleep, Hibernate (nur wenn
  unterstützt), Lock, Log off, Switch user (nur mit funktionierendem
  Backend); bei nicht unterstützten Aktionen sichtbar deaktivieren.
- [ ] **Interaktionsmatrix:** Start-Orb klicken; Win/Super; Tippen;
  Pfeiltasten; Tab; Shift+Tab; Enter; Escape; Rechtsklick; Maus aus
  Menü heraus; Vollbild-App; zweiter Monitor; Start nach Session-Wechsel.

### 4. Windows Explorer — RiceExplorer als eigenständiger Win7-Renderer (P0)

**Architekturvertrag:** File-I/O, Mounts, Kopierjobs, Undo, Papierkorb,
Preview-Backends und Such-Index kommen aus dem gemeinsamen Rust-RiceExplorer.
Der **Win7-Renderer** kontrolliert jedoch eigenständig Aufbau, Navigation,
Toolbar, Aktionsnamen und Zustände; er darf nicht nur Farben/Icons eines
Windows-10-/XP-Layouts überschreiben.

- [ ] **Navigationsbaum:** Favorites/Desktop/Downloads/Recent Places,
  Libraries/Documents/Music/Pictures/Videos, Computer/Volumes,
  Network/SMB/SFTP; HomeGroup nur mit technisch ehrlicher
  Ersatzfunktion oder klar als nicht verfügbar.
- [ ] **Libraries:** virtuelle Aggregation mehrerer Verzeichnisse,
  aufrufbare Standardbibliotheken, Include/Remove Folder,
  Save Location sowie abgrenzbare Such- und Sortierregeln; keine
  unbemerkten Dateidubletten.
- [ ] **Command Bar:** Organize, Include in Library, Share with,
  Burn (nur unterstütztes optisches Backend), New folder;
  kontextabhängige Optionen samt geöffneten Untermenüs.
- [ ] **Adress-/Suchelemente:** Back/Forward, Up sinnvoll,
  Breadcrumb mit aufklappbaren Pfadsegmenten, editierbare Adresszeile,
  Suchfeld mit aktuellem Ordner-Scope und Ergebnis-/Fehlerzuständen.
- [ ] **Ansichten:** Extra large/Large/Medium/Small Icons, List,
  Details, Tiles, Content; Icons richtig skaliert, Column sort, Group by,
  Hidden files, File extensions, Preview/Details pane und Statusleiste.
- [ ] **Filejobs:** Copy/Cut/Paste/Drag/Move, Rename, Recycle Bin,
  permanent delete mit Bestätigung, collision resolution (overwrite/
  keep both/skip), Merge Directory, Undo/Redo falls möglich,
  multi-select, progress, speed, cancel, retry und Fehlermeldungen.
- [ ] **Properties:** General/Details/Permissions/Sharing/Previous versions
  nur mit echten Linux-Funktionen; chmod/chown, Größe, Ziel für Symlinks,
  Dateityp, Datumswerte; ADS/NTFS-spezifische Dinge nicht vortäuschen.
- [ ] **Systemzugriff:** USB-Mount/Eject, verschlüsselte Datenträger,
  Netzwerkfreigaben SMB/SFTP/NFS über systemtaugliche Wege,
  Zugangsfehler, Offline/Timeout, Mount-Verlust und Wiederverbindung.
- [ ] **Performance:** Lazy Virtualization großer Ordner, thumbnails async
  und limitiert, watcher debounced, Thumbnail-Cache begrenzt,
  Abbruch bei Navigation, 100k-Dateien-Fall.
- [ ] **Dialogintegration:** Öffnen/Speichern nur dort ersetzen, wo
  Toolkits/Portale es sicher unterstützen; keine globale Shell-Hooks,
  die andere Anwendungen beschädigen.

### 5. Klassische Systemsteuerung / Windows-7-Dialoge (P0)

- [ ] **Startseite:** Category View mit System and Security; Network
  and Internet; Hardware and Sound; Programs; User Accounts and Family
  Safety; Appearance and Personalization; Clock, Language and Region;
  Ease of Access. Große/kleine Icons als alternative Ansicht.
- [ ] **Navigation:** Kategorie -> Aufgabe -> Unterseite -> echte
  Aktion, Breadcrumb/Back/Forward, Suchfunktion, Icon/Label-Konsistenz,
  ungeöffnete Seiten nicht als implementiert markieren.
- [ ] **System & Security:** Systeminfo, Power Options, Backups/
  Firewall-Schnittstellen sofern installiert; sudo/polkit bei Bedarf
  und klare Unavailable-States.
- [ ] **Network & Internet:** Active network, Wi-Fi-Liste, Adapterstatus,
  Connect/Disconnect, Sharing settings; NetworkManager als Quelle.
- [ ] **Hardware & Sound:** Sound-Devices, Default Output/Mic,
  Mixer, Bluetooth, Devices/Printers, Mouse/Touchpad, Display,
  Energieverwaltung; echte Linux-Backends.
- [ ] **Programs:** Default programs/File associations, installierte
  Apps/Deinstallieren nur über sichere reale Paketverwaltung,
  keine gefälschte Windows-Programmliste.
- [ ] **Personalization:** Windows Color, Window Appearance,
  Desktop Background, Sounds, Screen Saver (falls Backend), Mouse
  Pointers; Live Preview, Apply/Cancel/Rollback, per-Rice persistieren.
- [ ] **User/Locale/Accessibility:** Benutzerbild/Account-Infos,
  Datum/Uhrzeit/Zeitzone, Tastaturlayout, Kontrast, Skalierung,
  Barrierefreiheitsfunktionen; Grenzen klar benennen.
- [ ] **Dialogqualität:** Win7-formgetreue Sliders, Tabs,
  Dropdowns, Radio/Checkbox, Progressbars, Dateipicker,
  Lizenz-/Permissions-Dialoge; kein abrupter generischer GTK-
  Pop-up an jeder zweiten Ebene.

### 6. Notification Area — ausdrücklich *kein* Windows-10-Info-Center (P0)

- [ ] **Icons & Overflow:** Signal, Battery/Charging, Speaker/Mute,
  Bluetooth, Network, Clock, Safely Remove Hardware, Action Center
  flag; Chevron mit Hidden-Icons-Flyout und Konfigurierbarkeit.
- [ ] **Sound:** kompakter Win7-Volume-Flyout mit Slider/Mute,
  real-time sink/source, Gerätewechsel und Mixer-Link; Hardware-
  Lautstärketasten und externe Veränderungen bidirektional spiegeln.
- [ ] **Netzwerk:** Win7-Netzwerkflyout für verfügbare WLANs,
  Verbindungsstatus, Signalstärke, LAN, VPN, Connect/Disconnect,
  passwortgeschützte SSIDs, Flugmodus nur wenn Backend.
- [ ] **Energie:** Akku-Prozent, Ladezustand, Remaining-time nur
  bei seriöser Quelle, Power-Plan-Selector/Power Options,
  AC-only-/Kein-Akku-/Wachzustände.
- [ ] **Uhr & Datum:** Win7-Monatskalender, Uhrzeit,
  Datumsformat/12h-24h, erster Wochentag/Locale, Settings-Link;
  korrekter Bildschirmrand und Hotplug.
- [ ] **Weitere Popups:** Hardware sicher entfernen, Druckaufträge,
  Update-/Wartungshinweise als echte Ereignisse, klassischer
  Action-Center-Flag-Flyout mit Wartungs-/Sicherheitsstatus
  (nicht die Windows-10-Benachrichtigungsseitenleiste).
- [ ] **Balloon-Tips:** win7-artige Benachrichtigungsblasen mit
  Timeout, Klickziel, Suppress/Focus, Mehrfach-Queue und
  begrenztem Overflow; kein leerer Dummy.

### 7. Desktop, Kontexte und Shell-Integration (P1)

- [ ] **Icons:** Computer, Recycle Bin (voll/leer), Network,
  User's Files, Control Panel optional; echte Pfade, korrekte
  Verknüpfungsmarker und Textumbruch, Auswahl, Sort by, Align grid.
- [ ] **Kontextmenüs:** Desktop View/Sort by/Refresh/Paste/New/
  Screen Resolution/Gadgets/Personalize; Datei-/Ordner-Kontext
  entsprechend File-I/O und Standard-App-Assoziationen.
- [ ] **Papierkorb:** GIO/XDG-Trash kompatibel, Restore to original
  location, Empty Trash mit Bestätigung, verschobene Datenträger,
  fehlende Originalpfade und Symlink-Sicherheit.
- [ ] **Anzeige:** Wallpaper span/fit/tile/center, Aero Accent,
  einzelne/mehrere Displays, Auflösungsänderung mit Confirm + Revert,
  sinnvoller Lock-Screen-/Screensaver-Link.
- [ ] **Desktop-Gadgets:** Uhr/Kalender/CPU/Wetter optional in isoliertem
  nicht-privilegiertem Plugin-Sandbox-Modell; keine fremden
  unsignierten Win7-Gadget-Pakete ausführen.

### 8. Fenstermanagement und Tastatur (P1)

- [ ] **Snap:** Drag to edges = 50%-Tile; top=maximize;
  Win+Left/Right/Up/Down, Restore, Schatten-Vorschau, relevante
  Workarea ohne Taskbar-Überdeckung.
- [ ] **Shake & Peek:** Aero Shake minimiert andere Fenster und
  stellt sie wieder her; Peek über Superbar-Thumbnail und
  Show-Desktop, kein Eingriff in Vollbild-Spiele.
- [ ] **Switcher:** Alt+Tab in Windows-7-Anordnung;
  Win+Tab/Flip 3D nur mit realer Implementierung oder expliziter
  Dokumentation der Compositor-Grenze, kein zweckloser Platzhalter.
- [ ] **Weitere Hotkeys:** Win+D, Win+E, Win+R, Win+L,
  Win+Pause, Win+Number, Alt+F4, F2, F5,
  Ctrl+Shift+N, Delete/Shift+Delete, Kontextmenü-Taste;
  Konflikte mit XFCE/WM erkennen und reversibel umbelegen.
- [ ] **Multi-Monitor:** Monitor hinzufügen/entfernen, Monitor-Reihenfolge,
  Popup-Position, Fokus, HiDPI/DPI-Wechsel und Startmenü im rechten Display
  ohne Off-Screen-Bereiche.

### 9. Vollständiges Verhalten unter echten Linux-Bedingungen (P0–P2)

- [ ] NetworkManager mit LAN/WLAN/VPN, PipeWire/PulseAudio fallback,
  upower, UDisks2/GVfs, BlueZ, logind, polkit und X11-WM vor Start
  entdecken; API-Timeouts, Fehler und Zustandswechsel abfangen.
- [ ] **Session-Reconcile:** Beim Wechsel Mac/XP/Win7/Win10 alle
  exklusiven Panel-/Dock-/Toolbar-/Hotkey-Owner korrekt ab- und
  anmelden; Plank-/XFCE-Autostart-Konflikte nachvollziehbar beheben.
- [ ] **Session-Recovery:** Crash eines Panels oder eines Popups
  startet nicht mehrere Kopien, beschädigt keine Autostarts,
  lässt ein funktionierendes Standard-XFCE-Profil und einen
  dokumentierten One-Command-Rollback zurück.
- [ ] **Sicherheit:** Systemaktionen an echte Autorisierung binden,
  keine sudo-Shell via String-Concatenation, kein Ausspähen von
  WLAN-Passwörtern, keine remote untrusted Icons ohne Limits.
- [ ] **Zugänglichkeit:** Screenreader-Semantik, Beschriftungen,
  Keyboard-only, Fokus-Reihenfolge, hoher Kontrast, 125/150% Zoom,
  Reduced Motion, präzise Hit-Targets und lesbare Fehlermeldungen.
- [ ] **Geschwindigkeit:** Zielwerte für Cold start,
  Idle RSS/CPU, Menü-Latenz, Scroll-Jank und RAM-Spitzen auf dem
  ThinkPad X1 Yoga 2nd Gen messen; regressionsbasierte Budgets
  statt erfundener absoluter Benchmarks.

### 10. Szenario-basierte Acceptance Tests (alle Pflicht)

| Test | Ablauf | Erfolg |
| --- | --- | --- |
| W7-A01 | Login -> Desktop -> Start -> All Programs -> App -> zurück | Jede Ebene Win7-konsistent und bedienbar |
| W7-A02 | Zwei Fenster einer App -> Hover-Gruppe -> Close eines Thumbnails | Korrekte Identität, Vorschau, Fensterzahl |
| W7-A03 | Pin -> Jump List -> Datei öffnen -> Unpin -> Neustart | Reale Aktion und persistenter Pin-Zustand |
| W7-A04 | Win+E -> Libraries -> zwei Ordner aufnehmen -> Datei suchen | Aggregation ohne Dubletten/Dateiverlust |
| W7-A05 | USB einstecken -> Mount -> Kopie -> Konflikt -> Eject | Status, Fortschritt, Kollisionsentscheidung |
| W7-A06 | SMB offline -> Mountfehler -> reconnect -> retry | Kein UI-Freeze, hilfreiche Diagnose |
| W7-A07 | Ton, WLAN, Akku, Uhr öffnen -> Zustand extern ändern | Bidirektional richtige Backends, nichts offscreen |
| W7-A08 | Control Panel -> drei Ebenen tief -> Apply/Cancel | Optische und funktionale Vollständigkeit |
| W7-A09 | Win+Left/Right, Peek, Show Desktop, Alt+Tab | Reversibles Fenstermanagement |
| W7-A10 | 1024×768, 1600×900, 125% Skalierung, zweiter Monitor | Keine abgeschnittenen Menüs, korrekter Fokus |
| W7-A11 | Win7 -> Mac -> Win10 -> Win7, danach Restart | Keine Doppelleiste, verlorenen Hotkeys/Autostarts |
| W7-A12 | Panel hart beenden -> Retry -> Reset to XFCE | Sitzung bleibt reparierbar; echte Logs |
| W7-A13 | Keyboard-only, Screenreader, Reduced Motion | Alle Kernaktionen erreichbar |
| W7-A14 | 100k Dateien -> sort/filter/nav, Dateikopie abbrechen | UI reaktionsfähig, keine Datenkorruption |

### 11. Umsetzungsreihenfolge und Definition of Done

1. **P0: Produktwahrheit.** Design-Referenzsatz, reale Hardware-Backends,
   vollständige Start-/Superbar-/Tray-Interaktion sowie
   Windows-7-spezifische RiceExplorer-Struktur und Filejobs.
2. **P1: Tiefenpolitur.** Control Panel mit echten Unterseiten,
   Aero-Window-Chrome und Snap, Desktop-Kontexte, Dialogdesign,
   Icons und Zustandsübergänge.
3. **P2: Komplettheit.** Optionale Gadgets, Sounds/Cursors,
   erweiterte Power-/Network-/Druckfunktionen,
   Accessibility und Spezialfälle.
4. **Release-Gate:** Alle P0-Checkboxen sowie W7-A01–A14
   durch reproduzierbare Tests/Screenshots nachgewiesen, P1/P2
   entweder getestet oder explizit mit offenem Issue und
   realistischem Fallback dokumentiert. Kein 'fertig' aufgrund
   eines einzelnen Mockups.

**Offizielle historische Gegenchecks:**
[Windows 7 Desktop Experience](https://learn.microsoft.com/en-us/windows/win32/win7devguide/the-desktop-experience),
[Taskbar Extensions](https://learn.microsoft.com/en-us/windows/win32/shell/taskbar-extensions),
[Managing Files and Data](https://learn.microsoft.com/en-us/windows/win32/win7devguide/managing-files-and-data),
[About Libraries](https://learn.microsoft.com/en-us/windows/win32/shell/library-leverage-to-manage-folders).
