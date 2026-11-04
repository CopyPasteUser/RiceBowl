# ChromeOS · Native Material You fidelity roadmap

This is an original XFCE/X11 desktop inspired by current ChromeOS. It is a
Linux application, not ChromeOS or a Chromium fork. All controls launch real
Linux applications or act on verified device state; no Google binaries or
pretend connectivity toggles are included.

### Shared Riceware checkpoint — 4 November 2026

- [x] Route Shelf hardware status, Quick Settings output volume/mute and
  hierarchical device pages through a per-shell bounded `riceSpice` worker.
  Only read-back-verified mutations are reported as successful.
- [x] Reuse the native Wi-Fi, Bluetooth, audio, display brightness and power
  controls inside the standalone ChromeOS Settings navigator, retaining
  Material You styles and optional advanced XFCE configuration links.
- [x] Reuse `ricePop` for XFCE-owned notification history, unread status,
  Do Not Disturb and deletion/read actions; keep one notification owner,
  discard private content on close and disconnect the observer at shutdown.
- [x] Preserve earlier Aqua World controls without forcing their renderer to
  migrate in the same change; add hermetic adapter and regression tests.
- [ ] Complete physical XFCE hardware/keyboard/HiDPI/suspend acceptance and
  long-history, no-network, missing-BlueZ and multi-monitor checks.
- [ ] Finish remaining full ChromeOS fidelity gates below, including Shelf
  positioning, Overview/Desks, Tote, Files/RiceExplorer theme and tablet mode.

## Seven acceptance gates

- [x] 1. **Baseline and references:** audit the native ChromeOS shell and
  1600×900 Xvfb screenshots against the modern launcher, shelf, system tray and
  Quick Settings; keep the existing identity distinct from macOS and Windows.
- [x] 2. **Original visual assets:** build a ChromeOS-like *original* Material
  You wallpaper, rounded 3D-aware XFWM button states, coordinated GTK3/Thunar
  controls and material blue/lavender icon surfaces.
- [x] 3. **Shelf:** lightweight 56px shell, consistent circle app icons with
  real running-window indicator, proper launcher mark, stable centered app row,
  truthful network/audio/battery pill and reachable show-desktop command.
- [x] 4. **Launcher:** compact rounded bottom-left panel with actual installed
  Gio applications, icon grid and bounded scroll, search, favorites, keyboard
  focus, real settings action and pin/unpin context menus. No mock apps.
- [x] 5. **Quick Settings:** native bottom-right Material You panel with an
  accessible clock/date header, truthful network/Bluetooth/settings actions,
  verified volume/mute, battery status, disabled missing utilities and Escape.
- [x] 6. **Regression and safety:** ensure popup bounds at 1600×900 and
  1024×768, Xvfb smoke and all-rice test suite, backup-backed upgrade of
  byte-identical historical Chrome assets, no changes to other selected Rices.
- [x] 7. **Release:** current-only real screenshots from the same green CI run,
  English README/design/changelog updates, GitHub PR and merge to `main`.
  Preserve the existing historical `v0.9.1` release tag.

All seven implementation/virtual-X11 gates were verified in CI run
[`41633490775`](https://github.com/CopyPasteUser/RiceBowl/actions/runs/41633490775):
239 Python tests (one environment-dependent skip), all-rice smoke, genuine
1600×900 and Chrome 1024×768 window captures, screenshot bounds and visible
control-area checks. A small GTK utility-window backdrop remains visible at
the right Quick Settings corners under *uncomposited* Xvfb; the native X11
window bounding region itself is correctly rounded. Physical Mint XFCE
hardware and compositor behavior still require on-device acceptance.

### Progress update — 4 November 2026: hierarchical device settings

- [x] Replace direct-launch Quick Settings tiles with six detail pages,
  accessible Back/Escape navigation, meaningful local device status and deep
  links into the dedicated ChromeOS Settings window.
- [x] Introduce a standalone, searchable, seven-category ChromeOS Settings
  navigator with sidebar, detail routes, working Back/Escape and honest
  disabled/missing-utility states. Opening Settings no longer depends on the
  presence of `xfce4-settings-manager`.
- [x] Reuse the existing read-back-verified asynchronous Linux device controls
  from Aqua World under **Chrome-only** Material You styles: Wi-Fi radio and
  nearby SSIDs, Bluetooth power and connected devices, backlight brightness,
  battery level and supported power profiles. Network radio-off requires an
  explicit confirmation; unavailable hardware is not presented as connected.
- [x] Keep every original rice's controls intact through a backwards-compatible
  style-prefix parameter and add pure Python search/status/availability tests.
- [ ] Validate native navigation and device state on Mint XFCE hardware and
  review updated Quick Settings/Settings screenshots in CI. These are distinct
  from full fidelity completion; pairing, capture, privacy policy, native
  notifications and RiceExplorer integration remain open.

### Progress update — 4 November 2026: shelf calendar

- [x] Open a real GTK monthly calendar by clicking the Shelf clock; the
  date in Quick Settings also opens the same calendar page.
- [x] Keep GTK's native local-date, locale, month navigation, current-day
  highlighting and leap-year behavior, plus an explicit **Today** button.
- [x] Preserve the existing Quick Settings back/Escape behavior and provide
  accessible names; do not synthesize Google Calendar events or account data.
- [ ] Validate clock/date click geometry and keyboard navigation on the
  physical Mint XFCE desktop. At the time of this calendar milestone, native
  notification history and any authenticated events provider remained open;
  the notification-history milestone follows below.

### Progress update — 4 November 2026: XFCE notification history

- [x] Connect the Shelf bell and Quick Settings Notifications page to the real
  `org.xfce.Notifyd.Log` DBus interface (XFCE 4.18 / notifyd 0.9.x API).
  Display at most 40 real historical entries, grouped by source application,
  with their actual timestamps, read status and safe plain-text bodies.
- [x] Include a real unread-status badge via `HasUnread` and log signals,
  individual Mark read and Dismiss, Mark all read and a confirmation before
  destructive Clear all. No second freedesktop notification daemon, no
  local persistent private-history copy and no expired action replay.
- [x] Integrate XFConf Do Not Disturb with a read-back-verified switch;
  unavailable daemon/settings gracefully disable the relevant controls.
  Fetches and mutations are asynchronous to GTK; closing the view discards
  cached notification content. Add pure backend contract tests and a GTK
  navigation smoke test.
- [ ] Validate genuine populated log, DND, large histories, 1024×768 placement
  and focus behavior on the physical Mint XFCE machine. A full desktop-toast
  rendering pipeline, per-app policy, quiet hours and grouped-card expansion
  remain distinct tasks. This does **not** complete section 4 below.

## Reference principles

- Modern ChromeOS uses a Launcher for search/apps and an independently
  configurable, pinnable shelf. See Google Chromebook Help:
  [Launcher](https://support.google.com/chromebook/answer/15470775?hl=en),
  [Shelf](https://support.google.com/chromebook/answer/3113576?hl=en) and
  [Find & organize apps](https://support.google.com/chromebook/answer/6206362?hl=en).
- Materials: muted lavender `#e7e9f8`, warm-white `#f9f9ff`, ink `#262a40`,
  iris accent `#4b66d7`, clear elevated surfaces and gently curved corners.
- The shell remains GTK3; CSS themes live in the existing per-Rice contract.
  Use Pillow only as a **development-time** art generator (no runtime cost).
- Document differences honestly: notifications belong to XFCE, unavailable
  wireless controls are navigation actions, and no Chromebook-only Android or
  Google services are emulated.


---

## Complete ChromeOS Material You fidelity and functional specification (2026-11-04)

> **Product contract.** The target is the recognisable ChromeOS **Material You
> desktop experience of roughly M128–M132 (late 2024 / early 2025)**, with
> modern productivity Launcher, Shelf, Quick Settings, notification/calendar
> surfaces, Overview/Desks and the ChromeOS Files/Settings information
> architecture. Freeze this visual reference set before pixel tuning:
> ChromeOS changes over time; 'the newest ChromeOS' is not a testable baseline.
> Any newer features must be listed as separately versioned options.
>
> **Scope:** This is an original Linux/XFCE/X11 rice, not ChromeOS binaries,
> Google's Chrome browser, Android/Play Store, ChromeOS security architecture
> or an emulator. Reproduce the shell's structure, interaction and system
> behavior as faithfully as Linux permits, with real adapters, honest
> capability detection, safe degradation, and no invented Google services.
>
> **Progress rule:** The seven [x] gates above describe the existing native
> shell, screenshots and CI. Every [ ] below is an **additional open fidelity
> acceptance item**, regardless of prior screenshot-based completion.
> Roadmap items are not claims that code already implements them.

### 0. Evidence, baselines and a visual-fidelity reference kit — P0

- [ ] Capture *licensed reference material* for ChromeOS M128–M132:
  idle desktop light/dark; launcher initially/expanded/search/apps/folder;
  shelf empty/active/pinned/autohidden/side-aligned; status pill;
  Quick Settings first/second level; notification cards/calendar;
  Files application including context/properties/copy progress;
  Settings home and a deep device page; Overview/Desks/Split;
  screen capture; Tote; phone connections; tablet mode.
- [ ] Record exact text labels, hierarchical navigation, icon sizes,
  hit areas, geometry and visual hierarchy for each screenshot. Capture
  a state matrix: default, hover, focused, pressed, selected, expanded,
  disabled, busy, success, error, empty, no network, no device, overflow.
- [ ] Establish the ChromeOS-specific visual tokens: wallpaper-derived
  light/dark tonal palettes; warm/neutral surfaces; accent/primary/
  on-primary; elevations; rounded launcher & cards; large pill controls;
  subtle dividers and typography. Provide high-contrast/reduced-motion
  alternatives without drifting into a generic card dashboard.
- [ ] Adopt measured reference spacing and type; light/dark contrast
  >= WCAG 2.2 AA where feasible, non-text boundaries and keyboard
  focus visible. Use legally distributable font approximations and
  custom icons/illustrations, not ripped Google assets.
- [ ] Audit native screenshots at 1600x900, 1366x768, 1024x768 and
  touch/HiDPI; compare *secondary screens after several clicks*,
  not just a single beautiful shelf screenshot.
- [ ] Fix a terminology and edition chart: ChromeOS native concepts
  (Launcher, Shelf, Status Area, Quick Settings, Files, Tote,
  Overview, Desks, Snap Groups, Phone Hub) are not Windows Start,
  taskbar, File Explorer ribbons, Action Center, or macOS Control Center.
- [ ] **Desktop authenticity:** ChromeOS normally has wallpaper and
  a Shelf, **not arbitrary desktop file shortcuts**. Do not overlay
  Windows-style My Computer/Trash icons; user files appear in Files,
  Tote and the Launcher, and wallpaper customization is in
  Wallpaper & style.

### 1. Shelf — exact ChromeOS task/navigation surface — P0

- [ ] Model a left Launcher button, separate centrally arranged pinned
  and running application icons, ChromeOS-active indicators, and
  a compact right status area. Keep app groups stable as windows
  appear/disappear; no Aero task-button or Win10 live-tile semantics.
- [ ] Real application pin/unpin, reorder by drag, launch via
  Desktop Entry/Gio, switch/minimize/open multiple windows using
  stable Desktop-ID/WM_CLASS matching, and persist per-rice preferences.
- [ ] App right-click menus: Pin/Unpin, Close, recent/file
  tasks only if supported by app data, app info/open with where available;
  no misleading static entries. Overflow when many apps are pinned.
- [ ] Shelf position Bottom/Left/Right, Always show/Autohide,
  pointer activation from screen edge, maximized/fullscreen overlap,
  hotplug-monitor anchoring, correct workarea reservation and
  X11 compositor/uncomposited behavior.
- [ ] Distinguish pinned-but-closed, focused, unfocused-running,
  multiwindow, demanding-attention, launching/busy and failed-app
  visual states; provide tooltips and keyboard focus.
- [ ] Integrate Tote/holding-space entry, capture indicator,
  media or Phone Hub icon *only if those real features exist*.
  Clock/date/battery/wireless/mute sync with external changes.
- [ ] Multi-display policy: one primary shelf vs per-display shelf,
  popup ownership, moving focus between monitors, displaying
  correctly after resolution/rotation changes.
- [ ] Context menu on empty Shelf: Shelf position, Autohide,
  Wallpaper & style, optional personalization; all options persist.
- [ ] Device-specific targets: mouse and X1 Yoga touch/stylus
  should operate without tiny icons, accidental drags or edge trapping.

### 2. Launcher — a productivity app launcher, not a reskinned Start menu — P0

- [ ] Correct compact bottom-corner productivity Launcher with a
  rounded Search field, recent/suggested results, app grid and
  a deliberate expanded state where supported; correct opening origin,
  animation, keyboard focus and viewport bounds.
- [ ] Application discovery from desktop entries with real
  executable status, deterministic grouping, duplicate filtering,
  app names/icons, install/uninstall changes and localized labels.
- [ ] Search across installed apps, local Files, recent downloads,
  Settings and commands; hierarchical result groups, query highlight,
  zero-results/offline states, keyboard up/down/Enter/Escape,
  cancellation of slow queries, no fabricated Google cloud search.
- [ ] Grid app ordering via drag/drop, sort by name or
  available color grouping, folders created by dropping one app
  on another, folder rename/open/close/ungroup and persistence.
- [ ] App context menu: Pin to Shelf, Unpin, App info,
  Open location, Uninstall only through a legitimate package-management
  path; keyboard context/Shift+F10, reasonable fallback for
  uninstalled targets.
- [ ] Suggestions/recent results use verifiable local MRU data;
  allow user to disable/clear history. Google Drive/Web suggestions
  require explicit connected integration and browser.
- [ ] Launcher button, search key remap (Linux Super/Search),
  touch opening gesture and opening while a fullscreen window
  has focus; enter a second/third search without losing navigation.
- [ ] Avoid leaking ChromeOS Play Store/Android apps in the UI
  when no Android runtime is present; no mock icons for Google apps.
- [ ] Visual consistency for inline menus, app-folder surface,
  selection/focus ring, tooltips and touch/keyboard scroll.

### 3. Quick Settings — real status, toggle and subpage behavior — P0

**Observed code baseline:** macrice/chrome_quick_settings.py currently
opens installed XFCE utilities for Network, Bluetooth, Display,
Notifications, Power and Keyboard. The native sound volume/mute widget
and network/battery status are real. These are valid early gates but
*do not yet constitute* a ChromeOS-style hierarchical settings
surface with actual connectivity switches and device menus.

- [ ] Correct Quick Settings overview: system area click -> anchored
  material panel with large tile groups, date/time, connectivity,
  brightness/volume, battery/status, gear/power controls,
  accessible nested pages and back navigation.
- [ ] Network tile: accurate Wi-Fi/Ethernet/VPN/airplane state from
  NetworkManager; Wi-Fi on/off with verification, nearby SSID list
  with signal/security badges, connect/disconnect/forget,
  password prompts delegated securely; no WLAN device, captive
  portal, VPN blocked and offline cases.
- [ ] Bluetooth tile: device/adapter state from BlueZ, scan,
  connected/pairing/available lists, pair/unpair/connect/disconnect,
  rfkill and missing-service errors; no optimistic 'on' labels.
- [ ] Audio: output volume/mute, current output device,
  input/microphone and mic mute, headphone hotplug, Bluetooth
  routing, optional noise cancellation only if supported;
  PipeWire/PulseAudio compatibility and external updates.
- [ ] Brightness: slider backed by display backlight/DPMS/appropriate
  desktop display API, authorization when required,
  inactive state for unsupported external monitors,
  Fn-key and hotplug synchronization.
- [ ] Night Light and dark mode: compositor/gamma/display
  capability checks, manual on/off, schedule only with a real
  scheduler, correct warm/cool feedback and wallpaper-derived
  app palette when switching theme.
- [ ] Do Not Disturb / Focus: real freedesktop notification
  policy with persistable on/off and automatic scheduled expiry,
  Quick Settings and notifications badge synchronized.
- [ ] Power/battery: UPower state (charging, discharging,
  estimating if available, full, no battery, AC-only),
  battery-saver toggle only if an actual backend exists,
  sleep/lock/shutdown via logind, no fake power mode.
- [ ] Accessibility, Keyboard, VPN, Cast/Project,
  Location, Camera/Microphone privacy and Nearby/Quick Share
  buttons appear only when real backend integration is verified;
  otherwise visible explanation/disabled capability as appropriate.
- [ ] Full clickable hierarchy: top-level tile -> nested device
  list/settings -> actual command -> updated state -> back.
  Every chevron means navigates; every switch means changes state.
- [ ] Safe display geometry: bottom-right anchor, short-height
  scrolling, separate focus regions, no utility window remnants
  outside rounded corners on compositor-less Xvfb.
- [ ] Screen capture quick action invokes the real screenshot/
  recording UI, not a dead shortcut. 'Settings' opens the
  ChromeOS-style Settings frontend described below.

### 4. Notifications, calendar and status-area details — P0

- [ ] System notifications from freedesktop.org DBus / XFCE,
  with real app icon, title, body, timestamp, grouping by sender,
  action buttons, individual dismissal and clear-all.
- [ ] ChromeOS-style notification grouping, collapsed/expanded cards,
  count badge in the Shelf, Do Not Disturb suppression, optional
  quiet hours and per-app notification permissions.
- [ ] Empty notifications vs muted vs unavailable daemon
  states: distinct copy/visuals and recoverable action;
  never show expired private content after a session restart.
- [x] Date in Shelf opens monthly calendar surface with navigation,
  locale, first weekday/timezone, today highlighting,
  current day and DST; events appear only through a real
  user-authorized calendar provider, not invented data.
- [ ] Time/notification panels anchored without clipping at
  1024x768 and on the right/left monitor; keyboard open and Escape.
- [ ] Media controls in Quick Settings for actual MPRIS sessions:
  title/artist/art, play/pause/next/previous, device/mute;
  no fake playback for a browser without media signals.
- [ ] Notification toast cards near Shelf with timeout, keyboard
  accessibility, critical-error durability, correct focus behavior
  and multi-notification queue/stack.
- [ ] Status icons: Wi-Fi or Ethernet and VPN distinct,
  battery charging and percentage, Bluetooth when enabled,
  microphone privacy, focus, time/date, USB removal;
  unknown sensors show unknown/unavailable, not a guessed icon.

### 5. ChromeOS Files — dedicated RiceExplorer structural renderer — P0

**Non-negotiable architecture:** RiceExplorer stays a shared Rust
filesystem engine for file jobs, mounts, metadata, thumbnails, search,
undo, security and external volume discovery. Implement a **ChromeOS
Files UI renderer with independently configurable layout, controls,
information architecture and styling**, not merely Windows Explorer
with a pastel palette or Thunar with new icons.

- [ ] ChromeOS Files main layout: left navigation with My files
  (Downloads and configured folders), Recent, Images, Audio,
  Videos, Trash, Linux files as appropriate, USB volumes,
  SMB/NFS/SFTP network shares, and cloud drives **only when
  actually mounted/authenticated**. Android Play files appear
  only if a real Android environment exists.
- [ ] Top toolbar: Back/Forward, location breadcrumbs, search,
  selection-aware action buttons, list/grid view, sort,
  more actions and contextual overflow — not Win7 command bar
  or Win10 Ribbon.
- [ ] Quick local tasks: create folder, Copy/Cut/Paste/Move,
  rename, multi-select, duplicate, compress/extract,
  Copy link/path if meaningful, Trash/Restore/Empty,
  properties/info, open-with/default app, share via installed
  Linux integration, keyboard and drag/drop.
- [ ] File detail layouts: grid/list switch, row density,
  thumbnail size, date/type/size columns, selection checkboxes,
  breadcrumb dropdowns, file preview/metadata and status/usage.
- [ ] Search by location and type (image/audio/video/document),
  recent by timestamps, asynchronous indexing and cancellation,
  no-result/filter-active/offline errors; searchable removable
  volumes without blocking the main UI.
- [ ] Preview and Gallery: images, PDF, text/code, audio/video
  metadata; view/zoom/rotate where supported; isolate untrusted
  parsers and cap memory/CPU for huge/corrupt files.
- [ ] Archive actions: zip/unzip/tar/7z where backends exist,
  AES/encrypted handling only if supported, zip-slip prevention,
  malformed archive errors, progress and cancel.
- [ ] File transfer UI: total bytes/files, source/destination,
  rate/remaining with explicit uncertainty, conflict dialogs,
  keep both/overwrite/skip, pause/retry/cancel,
  disk-full/read-only/case-conflict/symlink loops.
- [ ] Mounts and sharing: UDisks2 USB/SD/eject, MTP,
  SMB with credentials in secure keyring, SFTP/NFS via
  available bridges, GVfs paths, network disconnect/reconnect,
  permissions and unsupported filesystem notices.
- [ ] Connected Drive: opt-in provider (e.g. user-mounted
  GVfs/rclone path) with actual auth/token lifecycle,
  offline availability, sync conflicts, quotas where exposed,
  clear 'not connected' state. Never silently send data
  to Google or imply a ChromeOS account.
- [ ] File property/security UI: MIME, extensions, size,
  timestamps, permissions and owner, link target,
  removable volume metadata, mounted read-only,
  storage usage; no invented Chromebook-only storage API.
- [ ] Strong file safety: correct XDG/GIO trash integration,
  original-location restore, deletion confirmation,
  symlink handling, untrusted filename validation and
  non-root operation.
- [ ] Performance: virtualized 100k-file lists, bounded
  thumbnails and network pagination, async watchers,
  folder job cancellation, bulk-select without frame stalls.
- [ ] URI/XDG portal integration so third-party GTK apps'
  Open/Save remains functional and RiceExplorer can be
  configured as default without hijacking all other rices.

### 6. Tote / Holding Space — a defining ChromeOS feature — P1

- [ ] Dedicated Shelf Tote entry showing recent downloads,
  screenshots, recordings and user-pinned files,
  with actual filesystem/event sources and sensible retention.
- [ ] Context actions: Pin/unpin, open, show in Files,
  drag into apps where supported, remove from Tote
  without deleting the file, distinguish missing/moved file.
- [ ] Small Shelf previews for up to the configured recent
  items, Hide previews action, responsive count and
  no leak of sensitive thumbnails into lock screens.
- [ ] Synchronize with browser downloads via real Downloads
  watcher and screen captures via the screenshot subsystem;
  non-browser files must not be silently fabricated.
- [ ] Privacy: opt-out, clear history, bounded thumbnail cache,
  symlink and removable-drive handling, permissions.

### 7. Overview, Desks, tiling and window choreography — P0/P1

- [ ] **Overview:** show all real visible windows with actual
  thumbnails/titles, Close button, switch and drag between
  Desks; keyboard Show Windows binding and touch gesture.
- [ ] **Virtual Desks:** create, rename, reorder, switch,
  delete/merge without losing windows, drag window to Desk,
  optionally 'all desks'; map to actual XFCE/X11 workspaces.
- [ ] **Split screen:** drag/window menu to half screen,
  other-window picker, keyboard Alt+[ and Alt+] with Linux
  keybinding resolution, correct workareas and multi-display.
- [ ] **Snap Groups:** optional M128+ reference behavior if
  compositor/window manager can support paired groups,
  split ratio resize, group overview entry, replace one
  window, cross-monitor correctness; mark unsupported if
  not implementable without WM redesign.
- [ ] **Window controls:** ChromeOS-style titlebar
  min/max/close, maximize-hover layout menu if target version
  includes it, active/inactive tokens, drag and resize.
  For native GTK apps, theme frame through XFWM/GTK where
  possible, avoid destructive global client-side hacks.
- [ ] **Window switch:** Alt+Tab, Search/Show Windows key,
  overview interactions, keyboard navigation, active focus,
  fullscreen apps and external display; distinguish per-Desk
  and all-Desks windows as ChromeOS does.
- [ ] **Tablet choreography:** swipes into Overview,
  home/launcher gestures, split-screen touch drag,
  virtual keyboard where installed, rotation and
  orientation update; tested on X1 Yoga touchscreen.
- [ ] **Session lifecycle:** switching to Windows/XP/macOS
  must restore their WM keybindings and desktop workspaces
  without orphaned windows or duplicate panels.

### 8. ChromeOS Settings — native information architecture — P0

**Do not count launching xfce4-settings-manager as complete.**
Build a dedicated ChromeOS Settings shell with searchable categories,
ChromeOS visual components, depth navigation and real Linux adapters.

- [x] Shell layout: search bar, left sidebar, category overview,
  selected section and detail page, back/breadcrumb,
  deep links from Quick Settings, no dead settings entries.
- [ ] Network: Ethernet, Wi-Fi, VPN, proxy and hotspot where
  supported; list, connect, disconnect, signal, security,
  limited/offline status, NetworkManager integration.
- [ ] Bluetooth and Connected devices: adapter, pairing,
  device list, headphones/keyboard/mouse, Wi-Fi printer where
  installed, KDE Connect integration when installed and user
  authorized, honest 'not supported' for ChromeOS-only sync.
- [ ] Accounts & People: actual Linux user/avatar/session,
  password and sign-out links via safe system tools,
  no counterfeit Google-account authentication,
  Family Link or enterprise policy screens.
- [ ] Device: display brightness/color/scaling/multi-monitor,
  touchpad/mouse/keyboard, audio input/output, storage,
  power/sleep, stylus/touch settings when available,
  rollback for risky resolution changes.
- [ ] Personalization: Wallpaper & style, curated legally
  usable wallpapers, user image, daily change where scheduled,
  color extraction, accent set, Dark/Light/Auto modes,
  screensaver only with a real backend.
- [ ] Apps: installed app listing, per-app notification
  permissions, defaults/open-with, startup permissions,
  uninstall/package manager handoff, PWA shortcuts if
  compatible browser exists.
- [ ] Privacy & Security: screen lock, media permissions,
  notifications, file search/cache and clipboard policies
  only if enforceable; no fake Verified Boot, sandbox,
  Google Safe Browsing or hardware-backed keys.
- [ ] Accessibility: screen reader, dictation/voice input only
  with installed provider, contrast, cursor size, magnifier,
  on-screen keyboard, captions if available.
- [ ] Advanced / Languages & input / Date & time /
  Printing / About: real distro name/kernel/hardware data,
  updates through Mint Update Manager or apt front end,
  layout/locale/timezone, device inventory and genuine
  maintenance diagnostics. Avoid imitating ChromeOS OS-update
  check without a ChromeOS updater.
- [ ] Common UI controls: Material You switches, sliders,
  segmented controls, settings rows/chevrons, search
  highlight, dialogs, toast confirmation, Apply/Cancel,
  loading/offline/error/unsupported states and
  keyboard focus for every nested page.
- [ ] Persist preferences per rice, keep a restore point
  before changing global XFCE display/power/input settings,
  and reflect externally made changes immediately.

### 9. Screenshot, screen recording and capture controls — P1

- [ ] ChromeOS-style Screen Capture bottom toolbar with
  Screenshot/Record toggle and Full screen/Window/Region modes.
  Use an actual X11/portal/PipeWire tool or write a small
  fit-for-purpose helper if no existing integration can deliver.
- [ ] Support mic/system audio recording only with available,
  permitted backends; explicit active-recording indicator,
  Stop control, output path, permission prompts and errors.
- [ ] Correct selection rectangle, escaped key state,
  multi-monitor coordinates, scale transforms and
  cursor capture option; no unreadable partial screenshots.
- [ ] On success save to user-configured Downloads/capture
  folder, optionally copy screenshot to clipboard, send
  real event to Tote and show accessible notification.
- [ ] Failure/edge: permission denied, recording backend
  missing, out of disk space, screen locked, hotplug,
  cancellation and user-initiated stop.
- [ ] Bounded recording resource usage on i7-7600U iGPU;
  hardware acceleration discovered, not assumed.

### 10. Phone Hub, cross-device experiences and Quick Share — P2 / opt-in

- [ ] Phone Hub only when a real user-authorized integration
  exists (KDE Connect is a practical Linux candidate):
  phone name/battery/connection, notifications where supported,
  ring device/clipboard/send file; clear capabilities per action.
- [ ] Keep phone features off by default until explicit device
  pairing, encryption/permissions and disconnect cleanup are
  verified. No pretense of Google's authenticated phone relay
  or account-backed Instant Tethering.
- [ ] Optional Recent Photos and notifications preview only
  if real provider permissions and privacy policy exist,
  bounded cache and sensitive-data purging.
- [ ] Quick Share/Nearby Share only after a compatible transfer
  backend is identified; otherwise provide explicit standard
  alternatives (Bluetooth, KDE Connect, SMB, SFTP) under
  accurate names, not a fake Quick Share button.
- [ ] Optional Wi-Fi hotspot/tethering with NetworkManager
  only when supported hardware and security policy allow;
  detect the company WLAN environment and avoid disrupting
  it without confirmation.
- [ ] Test paired/offline/locked/permission revoked states,
  different user sessions, device wake and authentication.

### 11. Chrome/browser and web-app integration — P1

- [ ] Open URLs with user-configured system browser or
  installed Chrome/Chromium; never assert that Google Chrome
  is bundled with this rice.
- [ ] Support PWA/window shortcuts via valid desktop entries,
  app icons and Shelf pinning, browser windows grouped by
  actual app ID where available; robust fallback to normal tab.
- [ ] Browser downloads feed Tote via filesystem watchers;
  browser tabs/history sync or Google Workspace account
  data requires separate explicit APIs/consent.
- [ ] Optional 'Open in browser' / shortcut context
  actions work with XDG defaults and browser availability.
- [ ] No attempt to secretly change browser profiles,
  install Chrome extensions or intercept web credentials.

### 12. Session, sign-in, lock and recovery — P0

- [ ] Authenticate through the real installed display manager
  (LightDM on Mint), not a fake login window. Optional
  ChromeOS-inspired lock wallpaper, clock and user tile
  only by safe, reversible greeter theming.
- [ ] Account switching/Sign out/Lock/Sleep/Shut down
  through logind and session manager, with polkit,
  confirmation only where appropriate and supported statuses.
- [ ] Preserve and restore XFCE panel, Plank autostart,
  taskbar owner, tray notification owner and hotkeys on
  Mac/XP/Win7/Win10/ChromeOS switch, logout and reboot.
- [ ] Avoid race conditions when re-opening Launcher and
  Quick Settings rapidly or when screens are reconfigured;
  singleton per-owner process and no stranded popup.
- [ ] Safe rollback if theme, icon, compositor, monitor,
  shortcuts or shell launch fails; return to normal XFCE
  via documented emergency command.
- [ ] Versioned configuration migration, atomic writes,
  backups of overwritten user customizations,
  no deletion of historical MacRice/RiceHub assets
  outside precisely owned install paths.
- [ ] Preserve user wallpaper/style choices and per-rice
  pins without contaminating other RiceBowl styles.

### 13. Architecture and ownership boundaries — P0

- [ ] **Chrome shell renderer:** Own Chrome-specific
  Shelf, Launcher, Quick Settings, Notifications,
  Calendar, Overview, Tote and optional Phone Hub.
  Extract shared Linux services and window enumeration
  instead of inheriting Win7 or Win10 widget hierarchy.
- [ ] **Remove accidental cross-style semantics:** Current
  chrome_shell.py CSS references .aero-taskbar/.aero-pin and
  .ten-tile selectors. Shared implementation is fine;
  ensure ChromeOS has independent structural contracts
  and tokens so Win7/Win10 visual changes cannot silently
  break ChromeOS. Add regression tests for CSS ownership.
- [ ] **RiceExplorer UI adapter:** Define a stable data/action
  contract for file items, mounts, jobs, previews, search,
  trash, error results and theme/layout plugins.
  ChromeOS Files, XP, Win7 and Win10 renderers may differ
  structurally and must not share hardcoded chrome.
- [ ] **System status service:** NetworkManager, BlueZ,
  UPower, audio, display brightness, notifications,
  UDisks2/GVfs and logind use typed read/write commands,
  cancellation, timeouts, backend capability reporting,
  verified post-action state and reasonable polling.
- [ ] **Settings service:** UI separated from privileged
  operations; use polkit and standard Linux APIs,
  no shell-string injection, no global editable config
  without rollback, unit and integration tests.
- [ ] **Extension/plugin capability model:** Apps/tiles
  and optional phone/cloud/recording providers register
  real affordances, labels, icons, permissions and
  disable reasons; broken integrations cannot crash shell.
- [ ] **Small-process performance:** Keep light panel
  resident, defer expensive thumbnails, search index,
  previews, discovery and media decode until opened;
  bound threads, memory and file watchers.

### 14. Accessibility, localization, performance and polish — P0/P1

- [ ] Keyboard navigation and visible focus across Launcher,
  Shelf, Quick Settings, Calendar, Files, Settings and
  Overview; no focus traps, Escape/Back semantics,
  correct ARIA/ATK accessible names.
- [ ] Touch and pen targets on Yoga, tablet gestures
  where X11 reliably supports them, touch-scroll inertia,
  virtual keyboard fallback and pointer/keyboard coexistence.
- [ ] 100/125/150/200% scale and multi-monitor rotation:
  no text truncation without tooltip, no popup off-screen,
  correct workarea, sensible side-aligned Shelf.
- [ ] English UI baseline, locale-aware date/time/RTL
  consideration, 12/24h and first-weekday controls;
  no raw shell command shown as ordinary UI label.
- [ ] Reduced motion, no flashing/faux spinner loops,
  legible shadows, high-contrast colors, contrast
  measurement against light and dark wallpaper palettes.
- [ ] Track real cold start, idle RSS/PSS and CPU,
  Launcher keystroke latency, Quick Settings latency,
  thumbnails/recording memory peaks, battery usage
  on the i7-7600U / 16 GB Yoga. Choose CI budgets
  from measured data instead of invented benchmark figures.
- [ ] Loading/success/error/empty/offline and
  missing-device states are intentionally designed
  for every system tile and level-2 settings panel.
- [ ] Click at least 3 layers deep into Settings and Files;
  ensure each remains recognisably Material You, not
  fallback generic XFCE/GTK appearance, unless explicitly
  opening a native external application.

### 15. Required acceptance test suite — all must be reproducible

| Test | Full user journey | Pass criteria |
| --- | --- | --- |
| CROS-A01 | Login -> idle desktop -> Launcher -> app -> return | Accurate ChromeOS desktop/shelf; real app |
| CROS-A02 | Search apps, files, settings; keyboard navigation | Real filtered results, no freeze or fake search |
| CROS-A03 | Create launcher folder -> rename -> sort -> reboot | Folder/order state persists |
| CROS-A04 | Pin app -> drag shelf position -> unpin -> reboot | Persistent pins and correct running indicators |
| CROS-A05 | Move Shelf bottom -> left -> auto-hide; maximize app | Proper workarea, no clipping/repaint artifacts |
| CROS-A06 | Quick Settings -> Wi-Fi list -> connect/forget -> external change | Verified NM state, UI synchronizes |
| CROS-A07 | Bluetooth scan -> pair audio -> disconnect -> rfkill | Real BlueZ state with errors and authorization |
| CROS-A08 | Headset hotplug -> change output -> mute via Fn key | Bi-directional actual audio updates |
| CROS-A09 | Brightness slider -> Night Light -> AC/battery change | Real backend or honest disabled state |
| CROS-A10 | Receive 3 notifications -> group -> DND -> clear | Correct app status/privacy/empty handling |
| CROS-A11 | Click date -> calendar -> change month/timezone | Correct dates, keyboard and no offscreen popup |
| CROS-A12 | MPRIS media active -> playback in Quick Settings | Real track/player, no placeholder |
| CROS-A13 | Win/Super Show Windows -> new Desk -> move window -> close | Real X11 workspace state, no lost windows |
| CROS-A14 | Snap two apps -> resize split -> Overview | Layout/recovery correct; group if supported |
| CROS-A15 | Open ChromeOS Files -> My files -> Search/Recent -> Preview | Native structural renderer, responsive |
| CROS-A16 | USB mount -> copy with conflict -> eject | Safe file transfer and accurate drive state |
| CROS-A17 | SMB NAS offline -> login -> transfer -> reconnect | Timeouts and no leaked credentials |
| CROS-A18 | Zip/extract malformed archive -> cancel job | Clear error and no path traversal |
| CROS-A19 | Download/screenshot -> Tote -> Pin/Hide -> file removed | Real previews and independent file lifetime |
| CROS-A20 | Capture full/window/region -> screen record -> stop | Correct output, privacy and resource cap |
| CROS-A21 | Settings search -> Network/Device/Personalization 3 levels | True Linux backend and ChromeOS UI throughout |
| CROS-A22 | Change wallpaper -> palette -> Dark/Auto -> restore | Coherent theme; user choice persists |
| CROS-A23 | Pair phone integration -> revoke -> disconnect | No fake status; secrets & cache cleared |
| CROS-A24 | 1024x768 -> 1600x900 -> 150% -> second monitor | Popovers, Shelf and focus in bounds |
| CROS-A25 | Laptop clamshell -> touch/pen -> screen rotate | Safe UI layout/gestures, no lost controls |
| CROS-A26 | Keyboard-only and screenreader all core panels | Focus/labels/action order usable |
| CROS-A27 | ChromeOS -> XP -> Win7 -> Mac -> ChromeOS -> reboot | One shell owner, all styles recover |
| CROS-A28 | Kill chrome panel -> recover -> restore plain XFCE | No duplicate autostart, lock or corruption |
| CROS-A29 | 100k Files, two transfers, thumbnails, notifications | Responsive and memory bounded |
| CROS-A30 | Test without BlueZ, UPower, sound, compositor | Accurate disabled/empty/failure states, no crash |

### 16. Implementation sequence and honest release criteria

1. **P0 / Core truth and fidelity:** frozen target references,
   disentangled ChromeOS renderer, real Shelf/Launcher window
   and pin state, hierarchical Quick Settings, Linux hardware
   adapters, notifications/calendar, real Overview/Desks,
   native Settings frontend, ChromeOS-specific RiceExplorer
   renderer, robust recovery.
2. **P1 / Daily-driver completeness:** Tote, screenshot/
   recording, contextual app actions, Files preview/mounts,
   personalization, browser/PWA integration, split-screen
   polish, light/dark palette, tablet and multi-monitor
   consistency.
3. **P2 / Real opt-in extensions:** Phone Hub via approved
   Linux integration, Quick Share only with compatible
   backend, deeper media/Gallery and optional
   ChromeOS-era features that have a defined baseline.
4. **Gate A — correctness:** No dead controls or fake
   connections. For every state-changing action, test
   success, denied, timeout and external-change paths.
5. **Gate B — visual depth:** screenshots for launcher
   3 levels, Settings 3 levels, Files 3 levels,
   tray/notifications/Overview across light and dark,
   short-height and scaled screens; reviewed against
   the frozen reference kit.
6. **Gate C — resilience:** P0 and CROS-A01–A30
   verified by automated tests where possible and a
   physical Mint XFCE/X1 Yoga acceptance pass for
   audio/Wi-Fi/Bluetooth/battery/screen/gesture behavior.
   Explicit issues document unsupported ChromeOS-exclusive
   APIs; never mark the entire rice complete from a
   mockup or a single Xvfb green run.

### 17. When another project is warranted

| Gap | Best ownership | Rationale |
| --- | --- | --- |
| ChromeOS Files file browsing, mounts, transfer, preview | RiceExplorer core + ChromeOS Files renderer | File-system correctness belongs to Rust backend; structural UI stays rice-specific |
| OS-wide network/audio/UPower/BlueZ controls | Reusable RiceBowl Linux service adapters | One accurate state machine feeds every rice; don't duplicate privileged logic |
| Notifications + Calendar UI | ChromeOS shell module backed by system notifications/calendar provider | Distinct visual hierarchy; backend can be shared |
| Tote and recent Downloads/screenshots | Small dedicated holding-space service or RiceExplorer integration | Watcher/index persistence with bounded resources |
| Overview/Desks/Snap Groups | Window-manager integration module; only replace WM if truly unavoidable | Requires real window ownership, not CSS |
| Capture/recording UI | Dedicated capture helper/plugin if existing tools insufficient | Permissions, recording pipeline and resources isolated |
| Gallery/PDF edit/media apps | Existing mature native apps first; optional sideproject only if needed for deep fidelity | Avoid rebuilding complex codecs/viewers unnecessarily |
| Phone Hub/Quick Share | Optional KDE Connect/verified sharing provider | Google account/private cross-device protocols should not be faked |
| Chrome browser / Android / Play Store | Outside the RiceBowl shell baseline | Require real supported runtime/service and explicit user install |

### Official reference index (research sources, not copied assets)

- [Google: Customize the Chromebook Shelf](https://support.google.com/chromebook/answer/3113576?hl=en)
- [Google: Find and organize apps](https://support.google.com/chromebook/answer/6206362?hl=en)
- [Google: About Launcher](https://support.google.com/chromebook/answer/15470775?hl=en)
- [Google: Manage Chromebook settings](https://support.google.com/chromebook/answer/15470698?hl=en)
- [Google: Open/save/delete files](https://support.google.com/chromebook/answer/1700055?hl=en)
- [Google: Virtual Desks](https://support.google.com/chromebook/answer/9594869?hl=en)
- [Google: Multitask with windows](https://support.google.com/chromebook/answer/177891?hl=en)
- [Google: Quick Settings sound controls](https://support.google.com/chromebook/answer/10045949?hl=en)
- [Google: Background, accent and style](https://support.google.com/chromebook/answer/1251809?hl=en)
- [Google: Screen capture](https://support.google.com/chromebook/answer/10474268?hl=en)
- [Google: Snap Groups](https://support.google.com/chromebook/answer/15400342?hl=en)
- [Google: 2021 Tote/Quick Settings media introduction](https://blog.google/products-and-platforms/devices/chromebooks/chromebook-turns-10-new-features/)
