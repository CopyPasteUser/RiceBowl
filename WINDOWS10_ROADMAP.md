# Windows 10 · Native fidelity roadmap

The Windows 10 rice is an original Linux/XFCE interpretation of the **Windows
10 22H2 desktop**, not Windows 7 Aero, Windows 11, or a cosmetic preview.
It must remain recognizably Windows 10 even with the wallpaper hidden.

## Seven acceptance gates

- [x] 1. **Reference and baseline:** audit the live GTK shell, dark/light GTK,
  XFWM, icons, taskbar, real system hooks and 1600×900 screenshot against
  period-appropriate Windows 10 Start, taskbar, Action Center and Explorer.
- [x] 2. **Art and window surfaces:** replace the oversized mascot wallpaper
  with an original Windows-10-inspired blue four-pane light composition; refine
  the square XFWM titlebar buttons and complementary GTK/Thunar dark/light styles.
- [x] 3. **Taskbar:** 40px flat charcoal bar, compact four-pane Linux Start mark,
  usable search, tight pinned/running app states, correctly labelled live tray,
  two-line date/time and right-edge desktop reveal.
- [x] 4. **Start:** genuine three-zone rail / alphabetical real-app list / pinned
  tile groups, realistic Windows 10 proportions, productive default tiles from
  installed apps, search, context pinning, user paths, settings and logout.
- [x] 5. **Action Center:** right-anchored tall panel with truthful notifications
  scope, real settings launchers, disabled missing tools, status from Linux,
  verified volume/mute controls and accessible focus/keyboard dismissal.
- [x] 6. **Regression:** native GTK/Xvfb smoke, 1600×900 plus 1024×768 layout,
  focused unit tests, all seven rices' regression and safe upgrade/restore of
  existing user-local Ten assets.
- [x] 7. **Documentation and GitHub:** update `DESIGN.md`, `README.md`,
  `CHANGELOG.md`, publish only the newest real X11 screenshots, CI green and
  merge implementation into `main` without moving the existing v0.9.1 tag.

## Design boundaries

- Use original RiceBowl artwork, not copyrighted Microsoft binaries/icons.
- Shell is GTK3/X11; menus discover genuine `Gio.AppInfo` applications and
  system actions use installed XFCE tools. Do not paint fake toggled states.
- The existing `macrice/aero_shell.py` owns native task/window/session behavior.
  Windows 10 rendering is isolated in `macrice/ten_shell.py` and scoped CSS.
- Retain independent identities for Windows 7, XP, Classic, Frutiger, ChromeOS
  and macOS. Preserve the backed-up, conflict-checked asset upgrade workflow.

## Visual references

- [Microsoft Support — Customize the Windows Start menu](https://support.microsoft.com/en-us/windows/experience/personalization/customize-the-windows-start-menu)
- [Microsoft Support — Customize the taskbar](https://support.microsoft.com/en-us/windows/experience/personalization/customize-the-taskbar-in-windows)
- [Microsoft Support — Personalize colors](https://support.microsoft.com/en-us/windows/experience/personalization/personalize-your-colors-in-windows)

These references inform the interaction and silhouette; the bundled assets
are independently drawn, Linux-specific, and do not imply Microsoft branding.

## Verification record

- GitHub Actions workflow `41626102066` (`Tests`, 3 November 2026): passed.
- 235 local Python tests passed, one environment-dependent skip; GTK3 CSS
  providers parsed without errors.
- Native Xvfb Start and Action Center captures inspected at **1600×900** and
  **1024×768**: both popups remain within the usable area above the taskbar.
- The twelve latest 1600×900 virtual-X11 captures are the only files displayed
  in the current README gallery. This does **not** constitute acceptance on a
  physical Linux Mint desktop, which remains a separate user-side check.

## Riceware migration checkpoint — 4 November 2026

- [x] Taskbar network/battery/audio status uses bounded `riceSpice` reads;
  verified volume and mute writes no longer start ad-hoc Win10 threads.
- [x] Own Win10 Action Center reads real `ricePop` XFCE history, with loading,
  empty, unavailable, mark-read and per-notification dismiss states. Only the
  user can dismiss; third-party actions are never replayed.
- [x] Real Wi-Fi, Bluetooth and Focus Assist toggles use their actual providers,
  disable themselves when unavailable, reconcile readback after mutation and
  refresh while the drawer stays open; in-flight switches stay disabled.
- [x] Stale notification callbacks are discarded on close and all workers/
  XFCE notification observers are released on shell shutdown.
- [x] Hermetic adapter tests and existing seven-rice Python regression suite.
- [ ] Native-X11 CI smoke/screenshots and physical Mint audio/network/Bluetooth
  + notification acceptance; these are not implied by Python unit tests.
- [ ] Full 22H2 fidelity gates below, including separate Win10 network flyout,
  richer Settings, app grouping/clear-all with confirmation, projection,
  battery saver, VPN, Airplane mode, Task View and riceExplorer integration.

The completed checkpoints are distinct from the broader uncompleted 22H2
criteria below. XFCE Notifyd remains the only notification service.

## Native Settings, Network and Task View checkpoint — 4 November 2026

- [x] Start and Action Center link to an independent dark Windows 10 Settings
  window, with home-category search, back/breadcrumb navigation and explicit
  System Sound/Display/Notifications/About subpages. Enabled controls use
  verified riceSpice/ricePop results, not fake XFCE toggles.
- [x] Network tray flyout lists at most 12 real SSIDs, signal/security, Wi-Fi
  radio-off/unavailable, manual rescan and explicit NetworkManager
  connect/disconnect with real error/credential handoff to native settings.
- [x] Taskbar Task View button shows Wnck-tracked real windows and XFCE
  workspaces. Switching/activating/moving, new desktop and safe last-empty-
  desktop removal use native X11 APIs. The window list is bounded.
- [x] Optional Windows 10 RiceExplorer launch uses the real `--theme win10`
  CLI only if installed; **does not replace Thunar** or change MIME defaults.
- [x] Hermetic Linux-backend adapter regressions and GTK CSS parse.
- [ ] Native X11 CI smoke and small-screen screenshots for the new surfaces;
  physical Mint/NetworkManager and multi-monitor acceptance remain separate.
- [ ] Complete Settings categories, global Win+Tab/Win+I key binding with
  backed-up XFCE shortcuts, task previews/Snap Assist, interactive network
  credential dialog, notification grouping and full Win10 Explorer acceptance.

The original 22H2 fidelity checklist below remains authoritative: new
entry points do **not** mean every Windows 10 feature is implemented.


---

## Windows 10 22H2 — vollständige Fidelity-, Funktions- und Abnahmeroadmap (2026-11-04)

> **Verbindliche Referenz:** Windows 10 Version 22H2 mit klassischer
> Desktop-Shell, Links-Startmenü, Live Tiles, Task View, Info-Center und
> Windows-10-Einstellungen. Kein Windows 7 Aero, kein Windows 11 mit
> zentriertem Start, runden Fensterecken oder Quick Settings.
> **Produktziel:** Authentisches Windows-10-Gefühl nicht nur im Screenshot,
> sondern beim Navigieren, Suchen, Kopieren, Verbinden, Konfigurieren,
> Multitasking, bei Fehlern und bei Session-Wechseln.
>
> **Statuskonvention:** Die [x]-Milestones oben dokumentieren bisherige
> Teilimplementierungen. Alle untenstehenden [ ]-Kriterien sind
> **zusätzliche offene Qualitäts- und Funktionsprüfungen**; der alte
> bestanden-Status erfüllt diese nicht automatisch.
>
> **Betriebssystemprinzip:** Das Aussehen imitiert Windows 10; jede Aktion
> steuert ausschließlich reale, sicher autorisierte Linux-Funktionen.
> Windows-exklusive Funktionen werden sinnvoll auf Linux abgebildet oder
> transparent als nicht verfügbar benannt. Kein Fake-Status, kein
> funktionsloses Schalter-Dekor, keine Windows-Binaries/Windows-Assets
> ohne passende Nutzungsrechte.

### 0. Designvertrag: Unverwechselbares Windows 10 (P0)

- [ ] **Baseline einfrieren:** Windows 10 22H2 im Desktop-Modus,
  primär 100% / 96 DPI, anschließend 125% und 150%; Standardscreen
  1600×900 und 1024×768. Keine Stilvermischung mit Win7, XP, macOS,
  ChromeOS oder Fluent-Win11.
- [ ] **Referenz-Capture-Set:** Desktop idle/focused; Taskbar hover,
  pinned, running, overflow; Start compact/full, app-list, tile-group,
  right-click, power, search; Action Center open/expanded/empty;
  Settings root/inner page; File Explorer/ribbon/properties/copy;
  tray: network/sound/battery/clock; Task View, Snap Assist,
  Win10 dialogs and context menus. Erlaubte Quellen/Assets dokumentieren.
- [ ] **Messbares Designsystem:** Farbwerte, Win10-accent, square corners,
  dezent flache Shadows, Typografiestufen, 40px taskbar at 100%,
  Search/Task View widths, Tile dimensions, Icon sizes,
  Margins, Rows, Focus/Pressed/Disabled states und Responsive-Regeln.
- [ ] **Referenzvarianten:** Standard-light, Standard-dark,
  Accent-from-wallpaper, Transparency on/off, High Contrast;
  optionale Tablet Mode Variante mit anderem Layout statt
  nur vergrößerter Desktop-Kacheln.
- [ ] **Assetqualität:** eigenständiges Blau-Fenster-Licht-Wallpaper
  mit Linux-Bezug; originale Windows-10-Gestaltungslogik,
  aber ausschließlich rechtmäßig nutzbare Icons, Logos, Schrift,
  Klang- und Bilddaten. Richtige Größen statt GTK-Placeholders.
- [ ] **Full-depth Review:** Ein Fenster mit drei Klicks Navigation
  muss noch Windows 10 sein. Jedes Flyout hat Idle/Hover/Focus/
  Pressed/Selected/Disabled/Busy/Error/Empty/Overflow/Keyboard.

### 1. Taskbar — echtes Windows-10-Verhalten (P0)

- [ ] **Komposition:** Start-Glyph am linken Rand; Search icon/box;
  Task View; Pins; Running apps; optional People (nur sinnvoll),
  system tray; clock/date; Action-Center glyph; schmaler
  Show-Desktop-Strip rechts. Höhen, Baselines und Hitboxes prüfen.
- [ ] **Konfigurierbarkeit:** Search box/icon/hidden, Task View on/off,
  kleine/große Taskbar-Buttons, Taskbar lock, autohide, location
  bottom/top/left/right soweit unterstützt, combine labels behavior,
  multiple displays (Main only / all displays), per-Rice persistieren.
- [ ] **Pins und Running:** Drag-Reorder, pin/unpin, reale Desktop-ID,
  Window focus/minimize/maximize, grouped multiwindow apps,
  active indicator underline statt Win7-glass stacks; Reopen from pin,
  app launch failure and transient dialogs sauber abbilden.
- [ ] **Thumbnail hover:** Preview nach Delay, mehrere Fenster
  nebeneinander, Close X mit Bestätigung wo sinnvoll,
  aktivieren per Klick, text overflows, richtige Position
  über Taskbar/Monitorgrenze; keine unsichtbaren/duplizierten Apps.
- [ ] **Jump Lists:** Taskbar-Rechtsklick für app tasks, recent files,
  pin/unpin, close window/all windows; dynamische Menüpunkte
  aus echten MRU-Quellen, persistent and removable.
- [ ] **Context menu:** Task Manager, Show Desktop, Toolbars,
  Search/Task View visibility, Taskbar Settings; Fenster-Gruppen
  mit Close/Restore/Minimize. Menüs bewegen sich nicht off-screen.
- [ ] **Anzeigen:** busy/attention/blink badge, Copy progress wenn
  signalisiert, application overlays; keine übertriebene
  Windows-11-Dots-/Centering-Ästhetik.

### 2. Startmenü — drei echte, separat bedienbare Bereiche (P0)

- [ ] **Layout und Größe:** vertikale linke Rail, alphabetische
  App-Liste in der Mitte, rechte angeheftete Live-Tile-Gruppen;
  Startgröße per Drag anpassen, Scroll- und Overscroll-Zustände,
  richtige Screenspace-Faltung und Schatten.
- [ ] **Linke Rail:** Hamburger/Expand, user avatar & account,
  File Explorer, Settings, Power; Hover-Expansion,
  accessible labels, context; links auf echte Programme.
- [ ] **App-Liste:** Recently added, Most used falls auf Wunsch,
  A-Z Groups, #/, alphabetic jump picker, icons/categories,
  scroll position, hide/show apps, app context/uninstall safe;
  Linux .desktop discovery mit stabiler Sortierung und Duplikatfilter.
- [ ] **Live Tiles:** Small/Medium/Wide/Large-Größen, Pin/Unpin,
  Drag-Reorder, Tile Groups benennen/verschieben, folder tiles
  nur falls real vorgesehen; tile preview/selection/context.
- [ ] **Live Content:** Wetter, Kalender, Media oder Status
  ausschließlich bei echtem Datenprovider/permission;
  sonst klar als statisches App-Tile; animierte Änderungen
  leise, stromsparend und deaktivierbar.
- [ ] **Suche:** Super -> Type; Apps, Settings, Documents, Files,
  recent items; Result categories, substring/fuzzy,
  indexed vs. non-indexed transparent, keyboard selection,
  Search icon vs. full box gleiche Search-Engine;
  auch schlechte/offline Netzwerkverbindung darf Start nicht einfrieren.
- [ ] **Kontext-Tiefe:** Right-click Tile / App ->
  pin/unpin Start/Taskbar, resize, more, open file location,
  run as administrator via polkit wenn zulässig, uninstall real app
  (sichere Launcher-Weiterleitung); nicht unterstützte Optionen
  verstecken/deaktivieren statt tote Schaltflächen.
- [ ] **Power und Account:** Lock, Sign out, Switch user (wenn
  Session Manager unterstützt), Sleep, Restart, Shut down,
  Hibernate nur wenn vorhanden; Polkit-/logind-Ergebnis und
  Cancel-Dialog korrekt abbilden.
- [ ] **Keyboard und dismissal:** Super, Tab, arrows, Enter,
  Escape, Shift+F10, Ctrl+Esc (falls gebunden), Click outside,
  fullscreen, typing while open, and open from second monitor.

### 3. Action Center / Benachrichtigungszentrale (P0)

- [ ] **22H2-typischer rechter Drawer:** volle vertikale
  Sidepanel-Geometrie, Notifications oben, Quick Actions unten,
  Collapse/Expand, Notifications heading & Clear all,
  Close by click-outside/Win+A/Escape; niemals Win11-Kalender-
  Benachrichtigungs-Hybrid.
- [ ] **Benachrichtigungen:** Real source (freedesktop
  notifications / D-Bus), App group, icon, title, time,
  body, optional action buttons, dismiss individually,
  Clear all, persistence policy, empty-state, duplicate collapse,
  history/expiration with privacy-safe storage.
- [ ] **Quick Actions:** Wi-Fi, Bluetooth, Airplane mode, VPN,
  Night light (only if backend exists), Location (only supported),
  Battery saver, Focus assist/Do Not Disturb, All settings,
  Connect / Project where technically available,
  Tablet mode when supported. Every tile has real status,
  correct on/off/busy/error/disabled.
- [ ] **Status correctness:** External changes through nmcli,
  blueman, system settings, charger, hotspot and Fn-keys
  refresh both quick action tile and corresponding tray icon.
- [ ] **Focus Assist:** Notification suppression rules,
  priority list and quiet hours using real local policy,
  badges/summary behave coherently; user can disable it.
- [ ] **Notifications Settings:** Configure per app whether
  banner/Center/sound; no confidential notification
  content in world-readable logs.
- [ ] **Screen fit:** Proper width at 1024×768, no clipped
  quick-action grid, scrolling separate from popup anchoring,
  multi-monitor and workarea position.

### 4. System Tray und kleine native Flyouts (P0)

- [ ] **Network flyout:** Windows-10-typisches panel,
  WLAN-Liste, RSSI/SSID, connected/available/no device,
  Connect/Disconnect, password prompt via network manager,
  VPN and Ethernet visibility, airplane; zero devices/offline
  and portal detection where supported.
- [ ] **Volume flyout:** distinct modern Win10 slider,
  mute, volume % option, audio output chooser, Media Transport
  UI only with real MPRIS source; synchronized with
  PipeWire/PulseAudio and hardware keys.
- [ ] **Power flyout:** battery percentage, charging/discharging,
  battery saver/power mode if actual Linux backend,
  energy settings, UPS/no battery/multiple batteries.
- [ ] **Clock/calendar flyout:** time/date, monthly calendar,
  day navigation, locale/timezone, short agenda only if a real
  local calendar integration exists; correct 12/24-hour format.
- [ ] **Overflow:** chevron for hidden status icons,
  context actions, show/hide icon settings, unread badges,
  input language/keyboard, accessibility, Bluetooth,
  safely remove USB and quiet-hour indicators if active.
- [ ] **Toast banners:** Windows-10 lower-right notifications,
  duration/stack/order, click action, close, Focus Assist,
  critical/error semantics, multi-monitor and app fullscreen.

### 5. Windows 10 Settings — vollständiges eigenes Shell-Frontend (P0)

**Nicht ausreichend:** Ein Startmenü-Button mit Ziel 'xfce4-settings-manager'.
Eine echte Windows-10-Settings-Shell verwendet Windows-10-Informationsarchitektur
und verbindet ihre Seiten mit dem realen Linux-Backend; alte klassische
Systemsteuerung ist ein eigener Fallback, keine Designbasis.

- [ ] **Settings Home:** Search a setting, Benutzerkonto /
  device overview nur mit echter Datenquelle, Kategoriekacheln,
  Windows-10-Metadaten. Navigations-Sidebar auf Unterseiten,
  Breadcrumb/Back/Forward, Deeplinks, no 404 page.
- [ ] **System:** Display (brightness, scale, orientation,
  multiple monitors, resolution with rollback), Sound
  (output/input/mixer), Notifications & actions, Focus assist,
  Power & sleep, Storage (volumes/available), Multitasking
  (snap/workspaces), About (actual Linux OS/hardware).
- [ ] **Devices:** Bluetooth & other devices, printers/scanners
  when installed, mouse/touchpad, typing, USB/autoplay; pair/
  unpair with confirmation, permission and error handling.
- [ ] **Network & Internet:** Status, Wi-Fi, Ethernet, VPN,
  proxy, airplane mode, Data usage if measurable; changing
  connections never fakes success; safe credentials handoff.
- [ ] **Personalization:** Background, Colors, Lock screen,
  Themes, Fonts, Start, Taskbar; preview, apply, revert;
  Windows-10-specific design tokens separate from other rices.
- [ ] **Apps:** Apps & features (real package inventory and
  uninstall handoff), Default apps/file associations,
  Startup apps with actual XDG-autostart handling, optional
  features only if a real backend exists.
- [ ] **Accounts:** Current Linux user, avatar, Sign-in options,
  family/other accounts as supported; never expose raw auth data,
  leave Windows-only Microsoft Account concepts clearly unsupported.
- [ ] **Time & Language:** Date/time/timezone, Region, Language,
  keyboard layout and optional speech; reflect changes on
  desktop clock and input indicator.
- [ ] **Ease of Access:** Display scaling, text size,
  magnifier/on-screen keyboard if installed, high contrast,
  narrator/screenreader availability, mouse pointer, keyboard
  accessibility settings; correctly persisted.
- [ ] **Privacy:** Explicit controls for actual app/system
  access if enforceable, notification data retention,
  file preview caches and location access; do not imitate
  platform privacy switches without a security backend.
- [ ] **Update & Security:** Actual distro update source/
  open apt/Mint update manager, Backup/Restore links,
  device encryption status where supported; *never*
  pretend Windows Update or Windows Defender is running.
- [ ] **Common controls:** Originalnahe toggles, dropdowns,
  sliders, progress, side navigation, search suggestions,
  empty/loading/error/offline states, disabled controls with
  reason, focused keyboard state, large text and touch.

### 6. File Explorer — eigener Windows-10-Modus von RiceExplorer (P0)

**Hard requirement:** RiceExplorer stays the shared Rust filesystem
engine. The Windows-10 view is a **separate structural renderer**,
not the Win7 Explorer with dark colors and different icon assets.

- [ ] **Layout:** Quick Access section; This PC with
  grouped folders/drives; Network; optionally OneDrive or
  cloud folders *only if installed*; ribbon header, title,
  search, breadcrumbs, address/history, status bar.
- [ ] **Ribbon:** File, Home, Share, View tabs with Windows-10-
  style command groupings: Pin to Quick Access, Copy/Paste,
  Cut, Copy path, Move to/Copy to, Delete, Rename, New folder,
  Properties; Share options from existing integrations;
  View layout/sort/panes/extensions/hidden; collapse ribbon.
- [ ] **Navigation:** Back/Forward/Up, breadcrumb dropdowns,
  editable address, path completion, recent locations,
  quick access pin/reorder/remove, folder navigation.
- [ ] **Views:** Extra large/Large/Medium/Small Icons, List,
  Details, Tiles, Content; details columns, sort ascending/
  descending, group by, Preview Pane, Details Pane,
  folder-specific persistent view, selection checkboxes.
- [ ] **Real file operations:** CRUD, multi-select, drag/drop,
  clipboard interoperability, trash/restore, rename and
  filename validation, folder merge/collisions, symlinks,
  permissions, hidden/system-like files with honest semantics.
- [ ] **Windows-10-style copy dialog:** Progress graph,
  throughput, files/bytes remaining when known, Pause/Resume,
  Cancel, Details/less details, multiple jobs and queue;
  handle disk full, read-only, interrupt and short-write
  without lost data.
- [ ] **Compressed folders:** zip/unzip, tar/7z via safe
  available backend, preview archive, extraction errors,
  zip-slip/path traversal defense and encrypted archive
  password prompt; Quick Actions as configured.
- [ ] **Previews:** Images, text/code, PDF, media metadata/
  thumbnails where codecs are present; Preview Pane respects
  type and size limits; no hanging on malformed files.
- [ ] **Network and device:** USB hotplug/mount/eject,
  MTP Android (when system support exists),
  SMB/SFTP/NFS/NAS, credentials through secure stores,
  reconnect/offline, write-denied and read-only states.
- [ ] **Search:** Scoped search from ribbon/address current
  folder, filter Date/Kind/Size if supported, indexed vs.
  nonindexed fallback, cancellations, large trees, hidden
  file policy, zero results state.
- [ ] **Context/Properties:** Open/Open with, Share,
  Send to where meaningful, Cut/Copy/Create shortcut,
  trash/delete, Rename, Properties tabs, file association
  choices; exact action result and permission checks.
- [ ] **Clipboard and portal:** Interoperability with Thunar
  and GTK apps through standard clipboard/URI formats;
  dialogs and XDG portals must stay usable in third-party
  applications.
- [ ] **Reliability:** virtualized large folders, bounded
  async thumbs/cache, watcher changes, multiple windows/tabs
  if enabled, safe cancellation and no UI thread blocking.

### 7. Task View, Virtual Desktops, Window Management (P0–P1)

- [ ] **Task View button / Win+Tab:** overview of actual
  open windows, minimize/restore/switch, plus per-workspace
  desktops, New desktop, close desktop, drag window between
  desktops, accessibility and Escape behavior.
- [ ] **Linux bridge:** XFCE/X11 workspaces correctly
  mapped, multi-monitor semantics validated, no fake
  wallpaper-only desktop slots, content survives switching
  to another RiceBowl rice.
- [ ] **Snap:** left/right halves, corner quarter tiling
  if WM supports it, maximize via top-edge drag,
  Win+Arrows and cursor previews, snap to available workarea.
- [ ] **Snap Assist:** after snapping first window, list
  remaining windows for second half; correct active
  window and future focus behavior, animations toggleable.
- [ ] **Alt+Tab / Win+D / Win+E / Win+R / Win+L / Win+I /
  Win+A / Win+X / Win+Number:** real app or shell action,
  conflict detection with XFCE, durable restore of shortcuts
  when another rice is activated.
- [ ] **Titlebar / windows:** squared button geometry,
  thin borders, active/inactive accent, minimize/maximize/
  close animations, resize edges, window shadows,
  right-click system menu, maximized border rules,
  best-effort compositor fallback.

### 8. Desktop, File Associations und Kontextmenüs (P1)

- [ ] **Desktop visual:** Linux-adapted Windows-10 blue beam
  wallpaper and optional stock-like variants;
  Windows-10-style Recycle Bin, This PC, Network, User Files
  shortcut icons; alignment, drag, rename and sorting.
- [ ] **Context:** right-click desktop -> View, Sort by,
  Refresh, Paste, New, Display settings, Personalize;
  actual actions for installed application context
  commands, keyboard context menu and selection state.
- [ ] **Recycle Bin:** XDG/GIO trash full/empty
  visual states, restore original location, Empty
  confirmation, removable volumes, missing paths.
- [ ] **Explorer launch:** Win+E launches RiceExplorer with
  proper Win10 renderer, not unrelated Thunar defaults;
  XDG file-manager integration configurable/restoreable.
- [ ] **Default apps:** Open With, filetype icon handling,
  chooser for PDF, media, images; no Windows-only software
  names advertised unless actually present.

### 9. Native-feeling dialogs and utility surfaces (P1–P2)

- [ ] **Run (Win+R):** originalnahe Win10 dialog with
  path history, shell-style shortcuts, safe command parsing,
  Escape/Enter and error states.
- [ ] **Properties dialogs:** General/Details/Permissions
  as supported; Apply/Cancel, validation, disk/file
  metadata, no false Windows NTFS features.
- [ ] **Task Manager link:** legitimate Linux task manager,
  optional Win10-style adapter only if real metrics/
  process operations, privilege checks and refresh rates.
- [ ] **Connect/Project:** screens and Bluetooth devices
  only if actual support; display-change rollback.
- [ ] **Date/Time/Power Dialogs:** consistent buttons,
  toggles, message sheets, tooltips, keyboard focus
  and confirmation states.
- [ ] **Clipboard history (Win+V):** optional opt-in
  feature only when secure clipboard storage and history
  are actually implemented; never log secrets by default.
- [ ] **Lock screen/sign-in:** Windows-10-like clock/blur
  and wallpaper only if LightDM/desktop integration
  is safe and reversible; never replace auth
  system with a decorative mock.
- [ ] **Tablet mode and touch:** especially for the X1
  Yoga convertible: keyboard/touch hit targets, rotation,
  touch scrolling, responsive Start/fullscreen,
  on-screen keyboard if installed, no forced tablet mode.

### 10. Complete integration / rollback contract (P0)

- [ ] **Backends and truthfulness:** discover D-Bus services
  (NetworkManager, BlueZ, UPower, logind, UDisks2/GVfs,
  audio, notifications, X11 WM) separately; timeout
  and report unavailable/denied/starting/error state.
- [ ] **No duplicate shells:** Windows10 startup/switch
  acquires ownership of taskbar/drawer/tray only once;
  exits and restores previous session cleanly on
  switch to XP/Win7/macOS/Frutiger/ChromeOS.
- [ ] **Safe updates and crash recovery:** installation
  must migrate old macrice/ricehub names safely;
  failed component must not leave locked screen,
  duplicated Plank, broken autostart, dead panels or
  hijacked keybindings. Document emergency XFCE restore.
- [ ] **Data model:** persist apps/pins/tiles/group names,
  last location, settings/panels per rice, schema
  migration with backup, no stale icons or out-of-sync states.
- [ ] **Security:** polkit for privileged operations,
  proper argv escaping, no unvalidated executable paths,
  notification privacy, no credential leak into logs,
  no untrusted archive path traversal, least privilege.
- [ ] **Performance:** profile on ThinkPad X1 Yoga 2nd
  Gen i7-7600U/16 GB; measure startup, idle CPU/PSS,
  input latency, open drawer, redraw rate, network I/O,
  thumbnail/preview caches, battery on/off AC; set
  evidence-based regression budgets.
- [ ] **Accessibility:** keyboard-first, tab order,
  visible focus, screenreader roles, contrast, reduced
  motion, dynamic DPI, accessible error text, touch.
- [ ] **Quality:** frozen screenshots for light/dark,
  1024×768 and 1600×900 at multiple states;
  x11vnc/Xvfb headless tests supplemented by a real
  physical-device acceptance pass.

### 11. Scenarios: no release without end-to-end evidence

| Test | User journey | Pass criteria |
| --- | --- | --- |
| W10-A01 | Login -> Start -> Apps by letter -> launch -> pin -> restart | Win10 appearance and persisted app state |
| W10-A02 | Start tile resize/reorder/rename group -> switch rice -> back | No lost layout or accidental global settings |
| W10-A03 | Super -> type setting -> Settings -> 3 levels -> Apply/Cancel | Real backend, history and Win10 design throughout |
| W10-A04 | Win+A -> Wi-Fi and Bluetooth toggle -> external status change | Tiles and tray reflect actual service states |
| W10-A05 | Receive 3 desktop notifications -> collapse group -> clear all | Real notifications, policy and empty state |
| W10-A06 | Win+Tab -> new desktop -> move window -> close desktop | Correct X11 workspace state, no lost windows |
| W10-A07 | Snap Assist two windows -> Alt+Tab -> Show Desktop -> restore | Window positions/focus remain correct |
| W10-A08 | Win+E -> Quick Access -> ribbon Copy/Move -> ZIP extract | Functional Win10-specific File Explorer UI |
| W10-A09 | Large file copy -> pause/resume -> conflict -> abort | Accurate progress, safe cancellation and integrity |
| W10-A10 | Mount USB -> write file -> safely eject | Real status, errors and no data loss |
| W10-A11 | Offline SMB -> retry reconnect -> mount permission denied | Usable error states, no freeze or credential leak |
| W10-A12 | Tray sound/network/battery/calendar -> navigate inside | All flyouts Win10, real bidirectional state |
| W10-A13 | 1024×768 -> 1600×900 -> 125/150% -> second display | No clipping or wrong popover monitor |
| W10-A14 | Light -> Dark -> High Contrast -> transparent off | Complete consistent theming and readability |
| W10-A15 | Keyboard-only Start/Explorer/Settings/Action Center | Focus visible, labels and dialogs reachable |
| W10-A16 | Plug/unplug headset, Wi-Fi adapter and battery/AC | UI refreshes, no stale offline status |
| W10-A17 | Win10 -> Win7 -> XP -> Mac -> Win10 -> reboot | One shell owner, no Plank/autostart regression |
| W10-A18 | Kill Action Center, recover shell, restore XFCE | No broken login, duplicated bars or lost config |
| W10-A19 | Huge directory + previews + large transfer simultaneously | Responsive input and bounded memory |
| W10-A20 | Touch/pen mode on Yoga, tray/tiles/ribbon | Reliable hit targets and no accidental gestures |

### 12. Priorisierung mit harten Quality Gates

1. **P0 — Funktionsbasis:** Start mit realer App-/Tileverwaltung,
   Taskbar mit echten Fenstern, vollständige Quick-Action-Statuskette,
   Windows-10-spezifisches Settings-Frontend, RiceExplorer Win10
   Renderer, Task View/Window Bridging, recovery/safe ownership.
2. **P1 — Wahrnehmbare Originaltreue:** vollständige Tray-Flyouts,
   Kontextmenüs und Fensterdekor, Snap Assist, Dialoge,
   Desktop/Icons, Theme-Konsistenz bis in die dritte Navigationsebene.
3. **P2 — Besondere Fälle:** Touch/Tablet, Clipboard History
   optional, Lock-Screen-Opt-in, zusätzliche Backends und
   kreative originale, lizenzsaubere Assets.
4. **Release-Gate:** Alle P0-Kriterien und W10-A01–A20 müssen
   mit überprüfbaren Screenshots, Logauszügen und/oder Tests
   grün sein. Offene P1/P2-Fälle nur als transparent dokumentiertes
   Known Issue und niemals pauschal als 'vollständig' ausweisen.

**Win7 bleibt getrennt:** Die dazugehörige ebenfalls
vollständige [Windows-7-Aero-Roadmap](WIN7_AERO_ROADMAP.md) behandelt
Superbar/Glass, klassischen zweispaltigen Start, Libraries und
klassisches Control Panel; diese Elemente gehören nicht in Windows 10.

**Offizielle Microsoft-Gegenchecks:**
[Windows 10 taskbar layout](https://learn.microsoft.com/en-us/windows-hardware/customize/desktop/customize-the-taskbar),
[Windows taskbar customization](https://support.microsoft.com/en-gb/windows/experience/personalization/customize-the-taskbar-in-windows),
[Notifications and Action Center](https://support.microsoft.com/en-us/windows/experience/notifications-and-do-not-disturb-in-windows),
[Multitasking and Task View](https://support.microsoft.com/en-us/windows/experience/how-to-multitask-in-windows),
[Tablet mode](https://support.microsoft.com/en-us/windows/hardware/input-devices/turn-tablet-mode-on-or-off-in-windows).
