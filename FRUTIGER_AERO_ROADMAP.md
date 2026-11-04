# Frutiger Aero · Aqua World fidelity roadmap

Objective: bring the **actual installed Linux/XFCE GTK3 Frutiger Aero rice** close
to the selected Y2K mockup, rather than producing another static illustration.
The original water/sky/grass desktop and every functional Linux integration stay
intact. The Windows 7, XP, Classic, ChromeOS, Ten and macOS styles are outside
this visual change. Original art only; do not bundle third-party assets.

## Reference and design direction

- User-selected mockup: a luminous aqua launcher, nature/water desktop, glossy
  taskbar and coordinated icons; three functional **Apps / Places / Settings**
  views. Prior feedback specifically requested a larger application icon grid.
- [Consumer Aesthetics Research Institute — Frutiger Aero](https://cari.institute/aesthetics/frutiger-aero):
  glossy interface materials, humanist type, translucent surfaces, nature and
  a mid-2000s sense of technological optimism. This is research, not an asset
  source.
- Source of truth: `macrice/heritage_shell.py` for live Frutiger shell styles;
  `macrice/aero_shell.py` for native GTK structure/behavior;
  `scripts/build_heritage_assets.py` for original XFWM/GTK art;
  `macrice/rice.py` and `macrice/shell_session.py` for safe desktop transitions.

## Seven delivery steps

1. **[x] Freeze behavior and identify visual drift.** Preserve actual Gio app
   launching, pin management, Wnck task switching, hardware reporting, keyboard
   shortcuts and seven-style apply/restore. Capture the current Xvfb baseline.
2. **[x] Establish a signature Aqua material.** Distinct deep-water cyan, lime,
   pearlescent white, refraction-like highlights, controlled edge light and
   visible keyboard focus. Avoid Windows 7's dark cobalt steel glass.
3. **[x] Rebuild the native launcher composition.** Refine `Your World` header,
   glossy quick links, segmented Apps/Places/Settings and a two/three-column
   icon-first application grid with honest empty state and Show more. Search,
   context pinning, keyboard navigation and installed-program launching remain
   functional at 1600×900 and 1024×768.
4. **[x] Give the taskbar a dedicated Y2K silhouette.** Aqua lens Start orb,
   refractive task/pin capsules, distinct active/hover treatment and a compact
   notification cluster. No fake status or additional background services.
5. **[x] Complete window and application materials.** Upgrade only Frutiger
   XFWM title/buttons and GTK/Thunar controls. Keep the art generator scoped and
   deterministic, with old managed assets upgradeable and custom user files
   protected by RiceBowl's asset conflict checks.
6. **[x] Audit accessibility, performance and safety.** Keyboard focus,
   disabled tools, readable contrast, click targets, no clipped menu, no
   startup/background process regression, no cross-rice style leakage, safe
   restore and narrowly scoped changes.
7. **[x] Capture and release the implemented result.** Run Python tests,
   syntax and asset checks and native Xvfb screenshots; inspect them visually;
   update only the current screenshots and the English README/Design guide;
   merge into GitHub `main` after green CI. Owner's physical Mint XFCE
   acceptance remains separate.

## Product acceptance criteria

### Follow-up: Pearl Glass and native Thunar refinement (3 November 2026)

- **[x] Launcher relevance:** the initial native Gio grid is ordered by saved
  pins, then installed file manager/browser/terminal, then other programs.
  Search still covers every visible app; context pin menus still work.
- **[x] Better visual hierarchy:** the top hero, shortcut row, navigation
  tabs, Discover caption, app tiles and footer now use distinct pearl, mint,
  lagoon and lime treatments instead of one continuous turquoise gradient.
  Optional X11 shaping also removes square GTK backing around the two rounded
  utility popups on systems without a compositor.
- **[x] Real folder behavior:** XDG-aware user folders and explicit creation
  confirmation remove hardcoded English folder paths and disabled shortcuts.
- **[x] App-icon identity:** the `org.xfce.thunar` desktop launcher resolves to
  RiceBowl's own turquoise file-manager SVG, rather than the OS fallback.
- **[x] Usable device controls:** Frutiger-only hero, larger readable captions,
  real status readings, volume and mute share the existing verified backend.
- **[x] Actual file-manager controls:** `FRUTIGER_EXPLORER_CSS` styles real
  Thunar widgets with a continuous breadcrumb surface, compact toolbar,
  pale-green navigation sidebar, white file canvas and subdued lime states.
  Replacing Thunar's *structure* remains a separate optional RiceExplorer
  project, never a fake GTK overlay.
- **[x] Recoverable installation:** the exact existing Frutiger GTK asset hash
  is in `trusted-ricebowl-frutiger-aqua-091.json`; historical managed Thunar
  blocks migrate, whereas modified/user-owned GTK CSS remains untouched.
- **[x] Automated QA:** unit and CSS parser tests, all-rice smoke capture and
  a new 1024×768 *actual Thunar* acceptance capture in isolated Xvfb.
  Owner's physical Mint/XFCE test is still required.


- Frutiger is recognizable without blur/compositor effects or a mocked panel.
- All three menu pages display real content and work with mouse and keyboard.
- App icons, titlebar, Thunar and taskbar read as one cohesive eco-glass family.
- All other six rice presets and their status/backup behavior are unchanged.
- No release tag is moved without explicit versioning decision. CI evidence
  does not claim hardware verification on the user's ThinkPad.


---

## Complete Aqua World / Frutiger Aero fidelity and functionality plan (2026-11-04)

> **Target definition:** Frutiger Aero is an aesthetic family, **not a
> historical operating system with one canonical screenshot**. Therefore
> "1:1 fidelity" means 1:1 consistency against a **frozen RiceBowl Aqua World
> reference board**: the user's previously approved luminous water/sky/nature
> mockup; original RiceBowl artwork; and circa-2004–2013 glossy,
> eco-futurist, optimistic consumer-software references. Explicitly
> avoid cloning Windows 7 Aero, ChromeOS Material You, modern glassmorphism
> dashboards, macOS Aqua or just a cyan Windows taskbar.
>
> **Design ambition:** Opening any menu, file, device, setting, media view,
> folder, notification or context menu should feel like entering the same
> richly textured world. Distinctive visual identity must survive
> three clicks deep, an empty/error state, a crowded app list, a USB
> mount and hours of regular Linux desktop use. The installed desktop,
> Linux app launcher, real hardware status and reversible rice switching
> remain functional.
>
> **Progress semantics:** The seven historical [x] milestones above remain
> valid for earlier cosmetic/native implementations and Xvfb checks.
> All [ ] criteria below are **new or re-opened full-product acceptance
> requirements**. They are not assumed implemented just because an earlier
> screenshot or release was accepted.

#### Implementation checkpoint · 4 November 2026

The first deeper implementation slice is in the code, **without closing
the full P0 requirements below**:

- `macrice/frutiger_control_center.py` adds a real native GTK3 Aqua hierarchy:
  nine categories, task detail leaves, search, Back navigation, keyboard-
  accessible controls and explicit missing-utility explanations.
- `Your World` Settings and hero gear open the Aqua Control Center. Tray
  network, sound and battery actions open their corresponding Aqua categories
  instead of immediately leaving Aqua for an XFCE utility.
- The existing backend-verified output volume/mute and live network/battery
  feedback remain; status now refreshes on opening and reports probe failure.
- Places adds Desktop, File system, real Trash, mounted removable/network
  volumes and event-driven Gio mount hotplug updates without background polls.
- CSS scope: only the Frutiger rice receives the deeper Aqua material system.
  Session ownership, apply/restore logic and all other rice profiles are intact.
- Verification: the Python suite, new targeted contracts and native headless
  GTK3 CSS parser. **Native X11 screenshot and actual Mint/XFCE acceptance
  remain unverified in this runtime**.

**Still open:** full NetworkManager and BlueZ control backends, device and
display settings, personalization persistence, compact device flyouts,
RiceExplorer Aqua renderer, icon family, screenshots and the 35 end-to-end
acceptance scenarios.

### 0. Frozen art direction and reference board — P0

- [ ] **Visual reference dossier:** Store annotated, legally sourced
  references showing refractive aqua-glass panels, 2000s web portal
  navigation, rounded image-led icons, natural water/grass/sky scenes,
  translucent product materials, polished orb controls, glossy tabs,
  shadows, water reflections and humanist typography. Include
  the user-selected Aqua World mockup and RiceBowl current screenshots
  as separate comparison columns; record access date and license.
- [ ] **Aqua World's own identity:** choose primary scenario "Your World:
  Explore · Connect · Create"; water-lagoon desktop, organic taskbar,
  independent hero/dashboard, apps/places/settings, nature-linked controls
  and original sound/icon language. Do not implement the Win7 two-column
  Start or ChromeOS launcher hierarchy.
- [ ] **Source period:** consumer-technology optimism roughly
  2004–2013, not a retro CRT/Windows 98 imitation or new flat
  SaaS redesign. Specify which borrowed ideas are stylistic motifs
  and which are never to be reproduced as copyrighted brand assets.
- [ ] **Reference coverage:** desktop idle, apps launcher, search,
  app hover/right-click, place navigation, settings page and subpage,
  quick settings first/second level, window focused/inactive,
  file manager, file preview, transfer/properties dialog,
  toast/notification, account/power, media, loading/empty/offline.
- [ ] **Visual measurement:** geometry, spacing, padding,
  asymmetric organic shapes, radii, highlight stripe placement,
  line/shadow weights, icon visual bounds, color temperature,
  blur/refraction, contrast, text treatment, material layers and
  correct hover/press/focus/disabled animation.
- [ ] **Authenticity rubric:** no generic uniform card grid, no
  unbounded gradients, no textureless flat control pages, no
  overtransparent unreadable text, no accidental Windows/macOS
  native-looking popups masquerading as Aqua World.
- [ ] **Reference matrix:** approved main composition at
  1600x900, practical 1366x768 and 1024x768, 125/150/200%
  scaling, light/dark and reduced-motion variants. Store
  precise expected states with screenshot names and IDs.

### 1. Material system — the signature five-surface grammar — P0

Design tokens and layers must generate every UI surface consistently,
rather than painting every widget with the same green/cyan gradient.

- [ ] **Pearl Shell:** high-key milky glass for text-heavy menus,
  modal dialogs and Settings; softened chromatic edges, readable
  opaque content center, pearl reflection on rim.
- [ ] **Lagoon Lens:** translucent aqua/cyan-refractive surface
  for the launcher hero and taskbar; broad lens highlight,
  layered water-like depth and controlled background sampling.
- [ ] **Lime Energy:** ecological leaf-green positive selection,
  applied/connected/progress states, icon highlights, active tabs;
  warning/error have their own distinguishable roles,
  not arbitrary green for every action.
- [ ] **Water Canvas:** clear white/blue tinted reading planes
  for Files, detail views, lists, search results and previews;
  remain legible over bright water or blue sky.
- [ ] **Chromed Jelly:** polished three-dimensional buttons,
  thumb knobs, tabs, separators, orbs, toggles and toolbar
  controls with upper specular highlight / lower shaded edge.
- [ ] Define semantic palette (brand, text-primary/secondary,
  positive, selected, warning, error, disabled, outline,
  focus, translucent scrim) and layer/shape tokens
  rather than hardcoded one-off color values.
- [ ] Real composited transparency/blur/refraction only
  if X11 compositor supports it with acceptable latency;
  deterministic multilayer gradient/alpha/shadow fallback
  in plain XFCE/Xvfb. A screenshot must still look coherent
  without desktop blur or OpenGL effects.
- [ ] Typography: humanist sans-serif that is redistributable
  (Frutiger-inspired metrics, not illicit font files),
  logo/header/body/caption scale, text shadow where needed,
  compact status numerals, readable 125/150% scaling.
- [ ] Icon spec: bespoke 3D-gradient family with depth/light
  source and perspective shared across Files, Music, Home,
  Network, Trash, Settings, media, Bluetooth, USB, battery,
  alerts and control-panel categories; 16/24/32/48/64/128/256px
  crisp or vector variants; no dissonant monochrome default icon
  unless explicitly treated as an external installed app.
- [ ] Effects library: soft bloom, caustic/ripple/edge sheen,
  elastic-yet-subtle hover lift, press depression,
  tiny bubbles only if non-distracting and power-budgeted,
  with accessibility/reduced-motion and high-contrast variants.
- [ ] Native widgets: checkbox, radio, dropdown, slider,
  segmented tab, tree/list row, scrollbar, tooltips,
  progress meter, close/minimize, invalid input, loading
  and error messages all defined in one material grammar.

### 2. Full-screen desktop scene, wallpaper and ambient identity — P0/P1

- [ ] Curated original wallpapers: Aqua Future (sky, lake, grass,
  sun, bubbles), Marine Blue, Morning Meadow, Cloud Garden,
  Evening Lagoon and dark/low-glare option; no unauthorized
  stock photograph reuse or generic AI gradients alone.
- [ ] Desktop wallpaper crop/scale/multi-display/fit/span,
  high resolution and quality-preserving JPEG/WebP/PNG variants;
  prevent tiled artifacts, oversaturated text backgrounds
  and disproportionate low-resolution upscaling.
- [ ] Seamless handoff from wallpaper to UI: hue,
  highlights and translucent surfaces feel part of the scene,
  but the scene never obscures interface controls.
- [ ] System-appropriate desktop icons and selections
  where the underlying XFCE desktop provides them:
  Files, Home, Trash full/empty, mounted devices,
  user shortcuts; aqua icon states, grid alignment,
  right-click and drag selection.
- [ ] Desktop right-click menu: wallpaper/style, icon size,
  align/sort/refresh, create folder/file, paste,
  display settings, desktop widgets, open terminal;
  actions must be real and keyboard reachable.
- [ ] Optional ambient widgets (clock/date/calendar,
  weather via consented source, battery, CPU/memory,
  music now playing, storage) are movable/disableable,
  resource bounded, screenreader friendly and must use
  **real data**. No fake sunny forecast or decorative
  'connected' labels.
- [ ] Optional wallpaper-based accent extraction,
  daylight/night presets, monitor-specific selection,
  per-rice persistence and safe rollback of globally
  altered XFCE desktop settings.
- [ ] User-selectable ambiance: off/light/full,
  with effects never running expensive constant
  render loops on the ThinkPad while idle.

### 3. Refractive taskbar, apps and window ownership — P0

- [ ] Unique floating/connected aqua taskbar silhouette:
  illuminated bubble Start orb, grouped glossy running
  apps with an active lime lens, separated status capsule
  and right-edge desktop control; no Win7 Superbar
  stacking appearance or macOS Plank clone.
- [ ] Stable app identity via Desktop-ID and WM_CLASS:
  pinned vs running, one/multiple windows, window
  focus/minimize/restore, launch failure, dialogs and
  Attention state; accurate real active-window indicator.
- [ ] Pin/unpin, reorder by drag, context menus
  for app-specific quick actions and recent files when
  real, window preview switching/close with correct
  thumbnail hover and keyboard focus.
- [ ] Taskbar position/size/autohide options as supported,
  multi-monitor and fullscreen-exclusion behavior,
  no phantom panel gap or overlapping XFCE/Plank bars.
- [ ] Hover/press/active/glow states feel like materials,
  with restrained lens movement and deterministic static
  alternatives; no flickering on pointer transfer.
- [ ] Show Desktop, window switcher, keyboard shortcuts,
  workspace indicators and optional activity widgets
  work through actual window-manager APIs.
- [ ] Screen-edge and popover ownership:
  menu opens above taskbar or in bounded side placement,
  no offscreen tooltip, detached utility blank rectangle
  or duplicate system tray after session switch.
- [ ] Context menu of empty taskbar for personalization,
  panel/autohide choice, task manager and session controls
  with safe and reversible settings.

### 4. Your World launcher — deep interaction, not only first page — P0

- [ ] Hero: custom nature/orb mark, "Your World" identity,
  exploration/connect/create cues, only real concise
  hardware summary and profile actions; visually layered
  but with clean information hierarchy.
- [ ] Three tabs remain structurally distinct:
  **Apps** grid/search/library, **Places** locations/
  drives/network/recent, **Settings** system actions,
  appearance, status and personalisation. Each
  has a coherent sub-navigation with back/history,
  search scope and detailed states.
- [ ] Apps: real Gio installed app discovery,
  alphabetical and recent/frequent sections,
  large icon-first grid (user specifically wanted
  larger app icons), responsive density, categories,
  smooth scroll, lazy icon loading, package updates.
- [ ] App pins/favorites/drag/order, context open,
  pin to bar, remove, application info, file location,
  launch with actual .desktop actions and privilege
  gating for administrative operations.
- [ ] **Search:** apps, filesystem, recent documents,
  mounted locations and actual supported settings,
  categories, results with icon/description, Enter
  activates, Escape restores, no-result and slow-backend
  states; never unbounded per-keypress filesystem scan.
- [ ] Places: XDG Home/Documents/Music/Pictures/Videos/
  Downloads/Desktop/Trash; favorites; USB drives,
  mounted shares, local partitions and recent locations.
  Each tile leads to real RiceExplorer/location.
- [ ] Settings: real Control Center home, categories
  and at least three nested levels with Back/Apply/
  Cancel, not merely a few xfce4-settings-manager links.
- [ ] Hero shortcuts (Home/Files/Documents/Music):
  correct targets, context actions, disabled state
  only when unavailable; user-modifiable ordering.
- [ ] Power/footer: Lock, Sign out, Sleep, Restart,
  Shutdown, optional Hibernate only if logind reports it;
  protection against accidental activation, no dead
  power icon or simulated confirmation.
- [ ] Scroll and geometry: user can reach all installed
  apps even when the bottom footer is sticky;
  keyboard focus and scrollbar stay visible and
  non-overlapping at 1024x768 and zoom levels.
- [ ] Popup dismissal on click-outside/Escape and
  focus return to launcher orb, correct multi-monitor
  positioning, keyboard tab/arrow/shift-tab and
  right-click behavior.

### 5. Aqua Control Center — fully functional settings ecosystem — P0

**Existing limitation:** a glossy first-level control palette with
buttons opening external XFCE utilities is a good transitional shell.
The goal requires a deeper **original Aqua World configuration app**,
not a themed root window that immediately drops into standard GTK
on its second click.

- [ ] Dedicated Aqua Control Center architecture with
  dashboard/category/detail panels, search, breadcrumbs,
  back/forward/history, persistent user choices and
  explicit capability/permission status.
- [ ] **Connections:** Wi-Fi signal/SSID list,
  connect/disconnect/forget with secure credentials,
  Ethernet speed/status where available,
  VPN connection/disconnection and NetworkManager
  error handling.
- [ ] **Bluetooth:** real BlueZ adapter/rfkill status,
  scan/pair/connect/remove, headphones and peripherals,
  permission denial, adapter unavailable and timeout.
- [ ] **Sound & media:** volume/mute, default audio output,
  microphone/input levels, input mute, audio profile/
  device routing, MPRIS player transport/metadata
  when present, PipeWire/PulseAudio fallback.
- [ ] **Display & brightness:** backlight slider only
  where actually supported, resolution/refresh/scale/
  rotation/multi-monitor with rollback countdown,
  wallpaper and screensaver, optional Night Light
  with real display backend.
- [ ] **Power:** UPower battery level, charging/discharge,
  remaining-time uncertainty, power saver only when
  real, auto-suspend, screen dim, lid behavior,
  correct no-battery desktop state.
- [ ] **Devices:** keyboard layouts, input language,
  mouse/touchpad/stylus, printers where installed,
  USB/MTP and default file associations; hardware
  hotplug and external changes reflect in panel.
- [ ] **Personalize:** wallpaper packs, Pearl/Lagoon/
  Lime accent intensity, material gloss/translucency,
  font/icon scale, widget density, taskbar form,
  animation level, keyboard/mouse effects and preview/
  apply/revert; no spill into another rice's assets.
- [ ] **Applications:** installed apps and default apps,
  pin management, startup applications with real
  XDG autostart, app launch settings; package
  removal delegated to safe package manager.
- [ ] **System & security:** actual OS/hardware info,
  disks/volumes and free space, network details,
  updates via Linux Mint tools, backup and restore,
  user session and account; no fake Windows Update.
- [ ] **Accessibility:** font scaling, high contrast,
  focus ring, keyboard navigation, reduced motion,
  screenreader and magnifier hooks where installed.
- [ ] Every settings view gets real current value,
  loading/success/error/unavailable/missing-privilege,
  Cancel semantics, retry, dark/light/high contrast
  and a material-correct dialog/tooltip.
- [ ] Coherent control row system: glossy slider thumb,
  switches, tabs, buttons, discrete radio groups,
  disabled text and explanatory detail, status
  badging and mini graphs where actual data is available.
- [ ] Avoid sudo shell invocations in UI; use typed
  DBus APIs, polkit, command escaping, read-after-write
  validation and transaction-style rollback for
  dangerous global display/session settings.

### 6. Hardware flyouts and contextual mini-controls — P0

- [ ] **Volume bubble:** compact glossy slider, speaker
  icon with mute feedback, output device picker,
  volume % optional, synchronise with keyboard Fn
  keys and external player changes.
- [ ] **Network bubble:** available Wi-Fi list, real
  connected SSID, signal and security, LAN/VPN,
  connect/disconnect, disabled adapter, rfkill,
  password prompt, offline and timeout states.
- [ ] **Power bubble:** charge %, AC/battery,
  saver and suspend settings if supported, date/
  time estimates only with reliable UPower data.
- [ ] **Bluetooth bubble:** on/off if permitted,
  connected device names, quick pair/remove,
  discoverable state and link to full Control Center.
- [ ] **Clock/calendar bubble:** date/time, localized
  monthly view, keyboard and month navigation;
  optional agenda only if real calendar integration.
- [ ] **USB/mount bubble:** newly attached devices,
  mount/unmount/eject with progress/errors and
  safety guard on running transfers.
- [ ] **Media bubble:** player name, artwork
  and playback controls from MPRIS with stale
  session cleanup; do not invent album art.
- [ ] **Notifications bubble:** grouped real app
  notices, dismiss/action, do not disturb, quiet
  hours if a policy backend exists, unread count.
- [ ] All bubbles share a controlled material
  vocabulary but differ structurally by task,
  resize intelligently above/taskbar side,
  never clip at 1024x768; no modal focus traps.
- [ ] Replace hardware status shown only in a
  giant dashboard with useful mini actions reachable
  in one click, as requested for other rices.

### 7. RiceExplorer — structural Aqua Files experience — P0

**Architecture contract:** Rust RiceExplorer owns the shared file
engine (copy/move/trash/archive/search/mounts/preview/network/
errors). The **Frutiger Aqua Files renderer** owns the visual
layout and interaction model; it may differ completely from XP,
Windows 7, Windows 10 and ChromeOS skins. A green folder icon
and GTK CSS on Thunar are not enough for this target.

- [ ] Original luminous Aqua Files shell: large
  translucent location hero, easy-to-scan
  favorite places, breadcrumb with glossy segmented
  locations, optional preview/inspector panel,
  file canvas with organic selection and clear
  action toolbar, not Win10 Ribbon or classic Explorer.
- [ ] Navigation: Home, Desktop, Documents, Downloads,
  Music, Pictures, Videos, Recent, Trash, removable
  volumes, LAN/NAS, user favorites and safe
  back/forward/up/search.
- [ ] File views: large glossy icons/grid, compact
  list, details with sortable columns, optional
  thumbnail/media gallery, zoom and selection
  checkboxes, grouping by type/date, hidden files.
- [ ] Real operations: new folder/file, Rename,
  Duplicate, Copy/Cut/Paste/Move, drag/drop,
  multi-select, clipboard interoperable with GTK,
  Create shortcut/symlink where valid.
- [ ] Quick actions clearly labeled: Compress,
  Extract here/Extract to, Share via real provider,
  Copy path, Open With, Preview, Properties,
  Move to Trash, Restore, Empty Trash and
  permanent Delete with confirmation.
- [ ] Archive formats: ZIP, tar.* and 7z where
  backend installed, encrypted archive prompt
  if supported, extraction conflicts and
  zip-slip/path traversal protection.
- [ ] Transfer panels: visible progress, per-file
  name, totals, throughput estimate, Pause/
  Resume/Cancel/Retry, conflict choices,
  collision avoidance on case-insensitive remote
  filesystems, power-loss safe interruption.
- [ ] Native preview: images/PDF/text/metadata and
  media with codec-backed previews, caching
  and file-size limits, corrupted-file/timeout
  isolation and background thumbnail generation.
- [ ] Volumes: UDisks2 local mount/eject/USB,
  GVfs SMB/SFTP/NFS, network share auth,
  NAS reconnect, read-only states, invalid
  credentials, permission denied, MTP Android
  if installed; real free-space state.
- [ ] Properties/details: MIME/size/permissions,
  owner, timestamps, checksum, link target,
  copyable path, change permission via
  authorization and explanatory Linux mapping.
- [ ] Trash follows XDG/GIO trash spec, restores
  original location, handles missing mount
  and exiled network file safely.
- [ ] Layout independence test: modify one Aqua
  Files navigation composition, verify no
  Windows7/10/ChromeOS renderer shifts and no
  shared Rust file engine regression.
- [ ] Performance: 100k files, virtualized list,
  async I/O and thumbnails, cancellable search,
  bounded cache, responsive after mount loss.
- [ ] Third-party Open/Save dialogs via native
  system portals must remain intact; do not
  hijack all GTK app file pickers across rices.

### 8. Windows, titlebars, application UI and system dialogs — P0/P1

- [ ] Rich aquatic XFWM frames with
  light-reflective titlebands, coherent active/
  inactive chrome and 3D-orb minimize/maximize/
  close controls, large but precise hit targets.
- [ ] Frame states for normal, maximized,
  modal, resizable, disabled, urgent/attention,
  fullscreen and compositor fallback.
- [ ] Menubars, application toolbars, dropdowns,
  scrollbars, context menus, treeviews, property
  sheets, alerts, toasts, file operations and
  progress bars use the same pearl/glass system.
- [ ] Interactive states under cursor, keyboard
  and touch; no theme regressions that make
  dropdown text unreadable or a button invisible.
- [ ] Dialog typography, button arrangement
  and iconography remain consistent three
  levels deep; destructive actions are
  visually distinct but not confusing.
- [ ] CSD/SSD compatibility: external Firefox,
  GTK3/GTK4, Qt/XFWM apps each degrade
  cleanly, no crash when a toolkit ignores
  custom frame; describe limitations honestly.
- [ ] Window previews/switching, Alt+Tab,
  maximize/snap/restore and focus rules
  integrated into the glossy taskbar.
- [ ] Polish on file picker/auth prompt:
  true native system dialog where the
  app/toolkit requires it, optional themed
  wrapper only when safe, no fake security UI.

### 9. Eco-iconography and original asset production — P0/P1

- [ ] Icon art bible: three-dimensional objects
  with volume, soft shadow, white specular
  highlights, slight perspective and polished
  saturated eco-aqua palette; categorically
  distinguish folders/docs/music/video/archives/
  tools/devices.
- [ ] Build consistent full sets for desktop,
  taskbar, launcher Apps/Places/Settings,
  Control Center, Files, device controls,
  weather/calendar, notifications, media
  and full/empty Trash; not only the main
  launcher tiles.
- [ ] Icons for user-installed apps should use
  their real branding and accessibility labels
  unless a lawfully distributed themed override
  exists; don't rebrand every app into one
  indistinguishable turquoise square.
- [ ] Animations and microinteraction cues:
  bubble hover/gentle reflection changes,
  active green light, pressed material depth,
  progress fill, drop target previews,
  optional short UI sounds, all switchable.
- [ ] Asset pipeline: deterministic
  vector/parameterized PNG/WebP generator,
  size-aware raster generation and cache,
  theme manifest, versioning, hash review,
  copyright/license manifest and rollback.
- [ ] User custom asset safety: trusted
  managed hash upgrades only, never
  overwrite manually modified theme and
  wallpaper files without explicit backup
  and conflict resolution.
- [ ] Distinguish Aqua World from Win7 Aero
  at a glance *without* wallpaper:
  test two identical application windows
  side-by-side under each rice with
  own controls, icons and taskbar active state.

### 10. Interaction depth, gestures and experience completeness — P1

- [ ] Mouse: left/right/middle where meaningful,
  drag/drop on desktop/Files/taskbar, double-click,
  hover-to-preview and click-outside close,
  safe timing for layered submenus.
- [ ] Keyboard: Super opens Apps, type-to-search,
  Tab/arrows/Enter/Escape/Shift+F10,
  Alt+Tab, Win+E, Win+L, Win+D,
  file CRUD hotkeys and accessibility navigation;
  avoid conflicts with Xfce hotkeys by scoped
  reversible remapping.
- [ ] Touch/pen on X1 Yoga: target size,
  long-press context menu, kinetic scrolling,
  swipe opening panel (only if supported),
  tap vs drag tolerance and orientation.
- [ ] Focus management: popup focus returns
  to trigger, subview Back preserves scroll,
  modal opens anchored without obscuring
  critical controls, keyboard stays usable
  after changing another rice.
- [ ] Multi-monitor: left/right anchor logic,
  popup on triggering display, natural wallpaper
  span, display hotplug, DPI and orientation.
- [ ] Search result changes, file/job updates,
  volume drags and network discovery must never
  freeze the UI thread.
- [ ] Empty states remain visually distinctive
  (no apps found, no media, no connected phone,
  no wireless card, no file preview, offline
  network), with real next actions and
  non-misleading explanations.

### 11. Separate original utilities worth building — P1/P2

- [ ] **Aqua Gallery:** a lightweight image/
  media/PDF viewing surface only if existing
  applications or RiceExplorer preview can't
  provide a cohesive Gallery experience.
  Use codecs and existing system libraries;
  avoid writing a full media engine gratuitously.
- [ ] **Aqua Sounds / Media mini-player:** branded
  controller via MPRIS first, optional standalone
  native media app only if needed; real library
  browsing if a player provider exists.
- [ ] **Aqua Weather / Eco widgets:** optional
  wallpaper-linked weather/calendar card using
  an actual authorized provider, scheduled
  cache and battery-aware refresh; default
  unavailable state until configured.
- [ ] **Aqua Center:** dedicated settings/control
  shell from Section 5, modular Linux services.
  Not a redundant generic 'Settings' skin
  duplicated across every rice.
- [ ] **Aqua Explorer:** RiceExplorer's independent
  renderer rather than a separate filesystem
  backend. Name/branding can be themed while
  core file-job reliability remains shared.
- [ ] **Aqua Search:** reusable indexed local
  search engine, UI integrations from Launcher
  and Explorer, opt-in private metadata index,
  asynchronous cancel and scoped folder policy.
- [ ] **Aqua Capture:** screenshot/window/region
  capture with custom glass UI if desired,
  back by available X11/portal utility,
  never block or run 60 FPS recording by default.
- [ ] **Aqua Welcome/Help:** optional first-run
  interactive tips, settings guide and
  personalization selector with real
  implementation links, no 'Coming soon'
  cards presented as features.

### 12. Real Linux backends, permissions and safety — P0

- [ ] Status service integrates NetworkManager
  (Wi-Fi/LAN/VPN), BlueZ, UPower, PipeWire/
  PulseAudio, UDisks2/GVfs, freedesktop
  notifications, MPRIS, logind and polkit.
- [ ] For each control:
  **discovery -> current state -> command ->
  verification -> error/retry**. Handle
  not installed, not permitted, rfkill blocked,
  temporarily unavailable, no device,
  timeout, bus disconnect, external change.
- [ ] Real input/mic privacy and
  device status updates; never store
  Wi-Fi passwords in plain logs or write
  untrusted shell commands from UI labels.
- [ ] Privileged device/storage/system changes
  go through polkit or system APIs with
  clear permission prompts and no
  indefinite blocking of the desktop.
- [ ] Settings that affect display/panels/
  shortcuts are transactionally applied with
  backup and automatic revert on failure.
- [ ] Notifications and event caches handle
  private content with bounded retention.
- [ ] Network remote volumes: safe mount
  credentials in keyring, no insecure
  automated ssh/sudo scripts, zero-data-loss
  behavior on interrupted copy.

### 13. RiceBowl interoperability and lifecycle — P0

- [ ] One active shell/taskbar owner at a time;
  correct transition Aqua -> XP -> Win7 ->
  Win10 -> ChromeOS -> macOS -> Aqua.
- [ ] Restore other rices' taskbars, titlebars,
  wallpapers, icons, shortcuts, dialogs,
  Plank, XFCE panels and autostart state
  without stale aqua overlays/processes.
- [ ] Per-rice saved pins/app order, icon size,
  color/wallpaper preferences and widget
  states; portable config schema and safe
  migration from historical MacRice/RiceHub.
- [ ] Idempotent install and uninstall,
  relaunch after crash, verify shell process
  ownership and avoid multiple resident
  trays or overlapping popup windows.
- [ ] Rollback to stock XFCE when theme
  asset, shell or display change fails;
  preserve an emergency keyboard/CLI
  recovery route and test it.
- [ ] X11 multi-monitor monitor reordering,
  screen-edge reserved areas and
  compositor on/off behavior validated
  without requiring third-party dock.
- [ ] No cross-rice CSS/class coupling:
  shared widget engine can be reused,
  but Aqua requires independent structure,
  token ownership, app context behavior
  and screenshots. Protect against
  regressions caused by Win7 CSS edits.

### 14. Performance, accessibility, and polish goals — P0/P1

- [ ] Measure cold-start time, GUI idle
  RSS/PSS/CPU, menu open latency,
  app search latency, file browse
  responsiveness, data refresh cost,
  wallpaper/icon memory, compositor
  and battery load on X1 Yoga 2nd Gen
  i7-7600U / 16 GB. Set budgets from
  actual measurements, not guessed figures.
- [ ] Pre-render/cached material surfaces
  and icon sizes; only recalc when accent
  or geometry changes. Limit blur regions,
  animated particles, shadows and GPU
  layers; 30/60 FPS motion must not
  be a permanent idle service.
- [ ] Defer heavy thumbnails, file index
  and multimedia metadata; async
  operations cancellable and bounded.
- [ ] WCAG-oriented contrast, readable
  labels over bright translucent scenes,
  visible focus, keyboard-only navigation,
  ATK/screenreader semantics and
  high-contrast/low-transparency option.
- [ ] Reduced motion/animation off,
  100–200% scaling, small 1024x768
  screens and rotated laptop tablet
  mode still usable.
- [ ] Consistency audit across at least
  ten surface types: start, apps,
  places, settings, nested device page,
  file manager, file preview, dialog,
  notification and tray popover.
- [ ] Error/empty/offline/busy/disabled
  variants and shortcut tooltips
  all match the Aqua materials;
  every visible interactive control
  must have a meaningful action.

### 15. Native screenshot and end-to-end acceptance matrix

| Test | Scenario | Pass criterion |
| --- | --- | --- |
| FA-A01 | Activate Aqua from standard XFCE -> desktop idle | Signature wallpaper, taskbar and icon palette coherent |
| FA-A02 | Open launcher -> Apps -> app context -> launch | Every layer in Aqua style; real app launches |
| FA-A03 | Launcher search -> open real file -> clear query | Useful responsive results, correct keyboard states |
| FA-A04 | Open Places -> removable drive -> file listing | Real mount/location, style and error behavior |
| FA-A05 | Open Settings -> device category -> adjust -> back | Three-level Aqua UI with verified Linux action |
| FA-A06 | Select/copy folders -> relaunch -> recent/favorites | Durable state; no file loss or broken shortcuts |
| FA-A07 | Pin/unpin/reorder five apps -> reboot | Icon order and active/idle state preserved |
| FA-A08 | Multiwindow one app -> hover/activate/close | Correct groups, focused window and preview |
| FA-A09 | Network bubble -> list Wi-Fi -> connect/forget | Real NetworkManager and accurate status |
| FA-A10 | Bluetooth device pair -> deny permission -> retry | Real BlueZ state and helpful errors |
| FA-A11 | Speaker/mic controls -> external volume key -> switch output | Bidirectional verified audio state |
| FA-A12 | Plug AC/USB -> battery/storage bubble -> eject | Accurate sensors, safe remove and errors |
| FA-A13 | Calendar -> next month -> change locale/timezone | Readable native styling and correct date |
| FA-A14 | Receive notification -> action -> dismiss -> DND | Correct native palette and real events |
| FA-A15 | Aqua Files -> icon/list/preview -> search -> navigate | Dedicated renderer, no Thunar chrome leak |
| FA-A16 | Copy 2GB -> pause/resume/conflict/cancel | Progress and safe job state, no corruption |
| FA-A17 | SMB NAS offline -> mount -> retry credentials | No freeze, no secret leak and accurate error |
| FA-A18 | Unzip malicious archive path -> cancel | Traversal blocked, user data preserved |
| FA-A19 | Trash folder -> restore -> empty Trash | XDG semantics and confirmation |
| FA-A20 | Personalize wallpaper/material -> Apply/Cancel | Live preview, correct rollback and persistence |
| FA-A21 | Light, dark, high contrast, no effects | Text legible, consistent materials and preferences |
| FA-A22 | Open properties, error, context menu, dialog | Three-click depth retains Aqua styling |
| FA-A23 | External GTK/Qt window -> titlebar/Alt+Tab/snap | Best-effort integrated chrome, no crashes |
| FA-A24 | 1024x768 -> 1600x900 -> 125/150% -> second monitor | No clipping, right display and workarea |
| FA-A25 | Yoga touchscreen/stylus and keyboard-only | Click/drag/focus accessible and predictable |
| FA-A26 | Compositor off -> open launcher/control popups | No rectangular backing/artifacts; safe fallback |
| FA-A27 | 100k file items + downloads + notifications | GUI responsive and bounded resource use |
| FA-A28 | No BlueZ/UPower/audio/network backend | Honest disabled/unknown state; no dead toggles |
| FA-A29 | Aqua -> Win7 -> Mac -> Aqua -> reboot | No style leakage, duplicate shell or lost config |
| FA-A30 | Kill panel/process -> restart -> restore XFCE | Recovery without destructive reinstallation |
| FA-A31 | Validate icon set at 16/24/48/128px and DPI | Crisp, consistent lighting, correct visual meaning |
| FA-A32 | Compare user mockup to desktop/launcher/Files/Settings | Same art direction and structural coherence |
| FA-A33 | Run with animations off/AC vs battery | Usable static UI and profiled CPU/battery usage |
| FA-A34 | Test permission denial/disk full/copy interruption | Clear message, recovery and no data corruption |
| FA-A35 | Audit all interactive elements with screenreader | Semantic names, logical order, no focus trap |

### 16. Prioritized delivery and release gates

1. **P0 — truthful, cohesive daily driver.** Freeze reference board;
   establish independent Aqua materials and icons; complete
   launcher Apps/Places/Settings depth; build functional Aqua
   Control Center, tray mini-controls, device backends and
   RiceExplorer Aqua renderer; ensure safe file jobs,
   session ownership and rollback.
2. **P1 — believable depth and delight.** Full window/dialog/
   context-menu polish, icon set, original wallpaper
   variants, Desktop/Files integration, notifications/
   calendar, multimedia surfaces, accessible microinteractions
   and touch/multi-monitor behavior.
3. **P2 — carefully scoped optional features.** Ambient widgets,
   weather, Gallery, media, desktop capture, extra
   nature variants and advanced nonessential effects
   if real integrations and performance permit.
4. **Release gate A: behavior.** Every control under
   Apps/Places/Settings and Quick Settings has a
   verified action/disabled explanation, no
   fake status and no accidental destructive operation.
5. **Release gate B: visual fidelity.** At least ten
   independent surfaces (including three levels of
   settings, Files, dialogs and popovers) compared
   with approved Aqua World art board in multiple
   interaction states, sizes and compositor modes.
6. **Release gate C: recovery and performance.**
   CI unit/integration/Xvfb screenshot checks plus
   on-device Linux Mint XFCE acceptance; all
   FA-A01–FA-A35 scenarios evidenced or recorded
   as explicitly open. Do not claim fully complete
   before P0 and critical file safety/recovery pass.

### 17. Ownership boundaries and separate project decisions

| Missing capability | Recommended owner | Why |
| --- | --- | --- |
| Structurally unique glossy file manager, mounting, previews | RiceExplorer Rust core + Aqua renderer | Shared safe I/O, independent deep visual structure |
| Network/audio/power/Bluetooth devices | RiceBowl Linux service adapters + Aqua flyouts | Real status and privileges reused across every rice |
| Wallpaper themes, pearlescent controls, 3D icons | Aqua design system + deterministic art generator | Prevent ad-hoc inconsistent gradients and asset collisions |
| Deep settings UI and personalization | Aqua Control Center module | Distinct 3-level navigation rather than thin XFCE launcher |
| Notifications, calendar and music popup | Aqua shell with shared standard DBus/MPRIS bridge | Distinct original surfaces, real event data |
| Gallery and PDF view | Existing system viewers first; optional native sideproject | Avoid unnecessary codec/security maintenance |
| Native window controls and preview/snap | XFWM/X11 integration layer | Functional WM behavior, not decorative custom animations |
| Search and recent content | Shared bounded indexing service | Fast real search across Launcher and Files |
| Clock, weather, ambient bubbles | Optional sandboxed low-cost widgets | Avoid fake data, battery drain and panel instability |

### Reference and licensing notes

- [CARI: Frutiger Aero aesthetic archive](https://cari.institute/aesthetics/frutiger-aero)
- [CARI Are.na archive and curator references](https://www.are.na/consumer-aesthetics-research-institute/frutiger-aero-ptg8tgmzbig)
- [University of Waterloo Computer Museum: Frutiger Aero, 2004–2013](https://uwaterloo.ca/computer-museum/exhibits/frutiger-aero-future-2000s)

These sources document era, motifs and historical inspiration. They are
**not asset licenses**. Build and ship original illustrations, fonts and
icons under suitable licenses; keep RiceBowl's unique Aqua World
composition and its existing user-approved water/sky/grass aesthetic.
