# RiceBowl changelog

## Unreleased — Frutiger Aero Pearl Glass polish (3 November 2026)

- Rebalanced the real Aqua World launcher around pearl-white glass, calmer
  mint app tiles, a clearer Discover section and distinct lime selected tabs.
  The home grid prioritizes saved pinned apps and familiar installed desktop
  programs, while search still covers the complete application catalog.
  Optional native X11 corner masks eliminate rectangular popup backing when
  XFWM4 runs without a compositor.
- Quick Home/Documents/Music links and the Places page now resolve XDG user
  directories correctly; missing directories can be created only after an
  explicit confirmation. The launcher returns to Apps when reopened.
- Improved the actual right-side GTK Control Panel with a dedicated Aqua
  header, more readable captions and better differentiated device-status
  surfaces; verified Linux volume, mute and real settings links are retained.
- Refined native Thunar into an Aqua file manager: one pearl breadcrumb field,
  compact functional navigation buttons, pastel-green sidebar, clean content
  and a restrained lime selection state instead of a wall of turquoise pills.
  A separate CSS overlay migrates exact previous versions but preserves custom
  user styling; the prior native GTK theme hash is whitelisted for backup-safe
  installation upgrades.
- Added 1024×768 actual XFWM4/Thunar screenshot checks in CI, as well as app
  ordering and managed CSS migration regression tests. Physical Mint XFCE
  acceptance remains pending; the v0.9.1 tag is unchanged.

## Unreleased — Windows XP Luna Explorer and Control Panel fidelity (3 November 2026)

- Replaced XP's narrow right-edge settings popup with a centered 2001-style
  Control Panel, offering functional Category/Classic View switching, eight
  Linux-backed applets and a blue sidebar with verified audio/network status.
- Start > Control Panel opens this window. My Documents/Pictures/Music respect
  XDG user directories; missing folders require confirmation before creation.
  Recent Documents now has a proper icon and date-ordered submenu.
- Changed only XP's Thunar controls to a warmer beige Explorer command bar,
  flatter address navigation and blue tasks-pane styling, while retaining
  genuine Thunar filesystem operations and exact CSS migration safeguards.
- Added 1600×900 / 1024×768 native XFWM4/Thunar acceptance captures, matching
  the actual applied window button layout, and replaced only XP's current
  screenshots from the passing GitHub Actions run `41691336596`.
- Remaining: the proprietary Explorer task-pane internals cannot be provided
  by GTK CSS; physical Mint XFCE confirmation is still needed.

## Unreleased — Cross-rice visual QA and native application coverage (3 November 2026)

- Fixed short initial XP Luna/Classic Control Panels and added a capture-time
  regression check for initially hidden volume/mute controls.
- Refined Classic settings to a 1998-style icon view; added functioning Windows 7
  Control Panel search and improved disabled-link contrast in Win7 and XP.
- Reduced Windows 10 taskbar search to a compact button opening existing app
  search; ChromeOS settings links have distinct navigation chevrons.
- Added disposable Xvfb/DBus workspace captures for six actual Thunar windows
  with per-rice GTK/icon styling and XFWM4 frames, rather than mockups.
- Fixed top-level Thunar menu-item spacing in Aero, XP, ChromeOS and Frutiger,
  preserving exact previous managed CSS blocks and unrelated user styles.
- Physical Mint/Plank acceptance and macOS equivalent captures remain open.
  The tagged v0.9.1 release and existing user settings are unchanged.

## Unreleased — ChromeOS Material You native fidelity (3 November 2026)

- Rebuilt the 56px ChromeOS shelf with native Gio pinned and running app icons,
  distinct launcher glyph, activity highlights and live hardware status.
- Added a left-anchored rounded application launcher with bounded 4-column
  grid, genuine installed applications, favorites, search and context pinning.
- Rebuilt right-side Quick Settings around verified output volume/mute,
  battery/network status, local date and real XFCE settings navigation;
  unavailable utilities are visibly disabled, and notifications are not faked.
- Shipped an original flowing pastel wallpaper, rounded XFWM4 button sprites
  and coordinated GTK3/Thunar controls, with a deterministic single-theme
  regeneration command and exact historical managed hashes for safe upgrades.
- Added focused ChromeOS tests, 1024×768 X11 capture checks and up-to-date
  screenshot gallery. Other Rices retain their own designs.
- The historical v0.9.1 release tag remains unchanged; use `main` for current work.

## Unreleased — Windows 10 native fidelity (3 November 2026)

- Replaced the oversized penguin wallpaper with an original deep-blue
  four-pane light composition, retaining a discreet Linux mascot signature;
  both Blue and Midnight retain the recognizable Windows 10 silhouette.
- Rebuilt the actual GTK Start menu into functional navigation, alphabetically
  grouped genuine Gio applications with search and Productivity/Explore tiles
  drawn only from installed applications and saved pins.
- Refined the 40px flat charcoal taskbar with a compact four-pane Linux Start
  badge, live search launcher, icon-only running windows and underline states.
- Built a right-edge Action Center with real settings launchers, honest
  notification scope, battery/network/audio details, verified output volume
  and mute, and disabled states for missing XFCE utilities.
- Updated dark/light GTK3, Thunar and sharp XFWM4 chrome, hover/focus states,
  and original sprite art. The other desktop families stay independent.
- Included exact historical Ten theme/icon hashes for safe backup-backed
  upgrades that never silently overwrite user customization.
- Added Windows 10 native 1024x768 screenshot checks and focused fidelity tests.
- The source-only work does not move the existing v0.9.1 release tag.

## Unreleased — Windows 98 / 2000 Classic fidelity (3 November 2026)

- Replaced the inaccurate ocean-style desktop with original solid Windows-98-era
  teal; the actual Linux shell now uses a slim 34px gray beveled taskbar and a
  19px pixel-art CRT/penguin Start emblem.
- Rebuilt the native Classic launcher as a dense cascading Programs, Favorites,
  Documents and Settings menu with real Gio apps, places, system tools, Find,
  Run, Help and session-confirmation shutdown; unavailable tools stay disabled.
- Drew original square XFWM4 navy/silver 27px titlebars and 22px buttons in
  normal, disabled, hovered and pressed states. Coordinated GTK3, Thunar and
  retro pixel menu controls retain native keyboard and accessibility semantics.
- Added narrowly scoped `--classic-only` asset rebuilding and precise original
  Classic asset hashes for backup-backed upgrades without overwriting user art.
- Added Classic 1024×768 native-X11 gallery regression and Classic-specific
  fidelity tests; 229 tests and all six native shell captures passed GitHub CI.
- Corrected the gallery validator's old PNG-size assumption: solid teal really
  produces smaller losslessly compressed screenshots, and proper screenshot
  dimensions, uniqueness and visible controls remain independently checked.
- The Classic Control Panel now has a functional navy 1998 caption and close
  button while preserving its real audio/network/device settings.
- Source improvements are not a retroactive change to the tagged v0.9.1 build.

## Unreleased — Frutiger Aero / Aqua World fidelity (3 November 2026)

- Hand-drew a deeper pearlescent cyan/lime taskbar, an organic water/leaf Start orb,
  the original glass XFWM4 window-frame/button states and corresponding GTK3/Thunar controls.
- Redesigned the **actual native GTK launcher** into a luminous `Your World`
  dashboard with real hardware status, working places/settings quick links,
  searchable three-column Gio application tiles, context pinning and Show more.
- Gave Frutiger its own icon theme inside Xvfb previews without changing the
  OS-wide GTK settings. Normalized unusual application icons to 48 px.
- Made Frutiger Control Panel larger and more useful, with visible device
  details, verified audio controls and a distinct refractive hardware card.
- Added trusted hashes for unmodified pre-Aqua theme/icon bundles so updates
  remain backup-backed; user-customized files continue to be protected.
- Extended native 1024×768 screenshot tests to Frutiger and verified all
  six non-macOS shells; refreshed only current gallery screenshots.
- No tagged release is moved by these source-only improvements. Physical
  Linux Mint XFCE and compositor-dependent rendering still need owner review.

## 0.9.1 — XP popup geometry and safer panel handoff (3 November 2026)

- Position the XP Luna Start menu against the actual mapped GTK window height, not its requested 560 px; shrink its program-list minimum height so the taskbar stays exposed.
- Add a native GTK application readiness action on taskbar map and verify it over the local D-Bus session before retiring the stock XFCE Panel.
- On a failed taskbar startup, stop the incomplete replacement and attempt to recover XFCE Panel and previously saved keyboard shortcuts. Preserve Plank ownership and the existing restore snapshots.
- Move post-apply and post-restore session reconciliation off the Hub's GTK main thread to avoid UI stalls during startup checks.
- Extend layout and session regressions, and gate the release on real virtual-X11 popup bounds, smoke tests and 12 fresh gallery captures.
- The owner accepted the 0.9.0 desktop designs and functionality, with the XP menu/taskbar overlap identified as the remaining issue. The 0.9.1 geometry fix still needs a final physical-machine check.

## 0.9.0 — Four reference-driven GTK/XFCE rice refinements (3 November 2026)

### Implemented, not rendered mockups
- **XP Luna:** independently built two-column Start menu, blue user band, light program list, bright blue Places column and real session-dialog controls; raised green Start button, glossy blue taskbar and live hardware controls.
- **Windows 98 / 2000:** a native cascading Programs menu populated from installed desktop applications, vertical navy brand rail, inset gray taskbar, square controls, genuine Find search and real system shortcuts.
- **ChromeOS:** 12 installed-app launcher tiles with search-on-demand, distinct left launcher, centered app shelf and rounded right-hand status cluster; icon-only running-window buttons and soft pastel control styling.
- **Frutiger Aero:** live Apps / Places / Settings pages with actual installed apps, folders and XFCE tools; luminous cyan glass, bright lime selected tabs and profile-specific hardware controls.
- More faithful native Thunar GTK3 chrome for each of those four: toolbars, menu bars, path controls, sidebars, selected rows and status bars. Thunar functionality remains Thunar; the reference mockups' custom file-dashboard layout is not claimed.
- 36 additional original folder, document, media, desktop, disk and network icons, preserved by the heritage asset generator; previous curated assets retained.
- Working, debounced **volume slider and mute toggle** with bounded PipeWire/PulseAudio commands and read-back verification. Battery and network detail text show real hardware state.
- Recognize exact 0.8 managed theme hashes and old 0.8 Thunar CSS blocks during upgrades; protect unrelated customizations and preserve the entire macOS implementation.
- Virtual X11 screenshot validation and additional migration, hardware, and icon regression tests. Physical Linux Mint XFCE/Plank/multi-monitor testing remains necessary before a stable release.

## 0.8.0 — Distinct identities, hardware tray and recoverable theme upgrades (3 November 2026)

### More individual non-macOS desktops

- Added **42 original vector icons** for file manager, folders, settings, browser, terminal, home and trash across Aero 7, Windows 10, XP Luna, Classic 98/2000, ChromeOS and Frutiger Aero; the previous clones are gone.
- Added **four independent heritage Start icons** and **66 status icons** for each desktop's battery, Wi-Fi/Ethernet and audio indicators.
- ChromeOS now has a centered app/search dashboard, not a recolored Windows 10 Start screen. Frutiger Aero has an independent organic-glass dashboard with quick places; XP, Classic, Aero and Ten retain appropriate distinct navigation.
- Extended per-rice notification-area geometry, colors, control surfaces, hover/focus states, spacing, and matching native Thunar treatments.

### Real tray behavior

- Show actual Linux battery percent/charging state from sysfs, aggregated over multiple batteries; hide the widget when no battery is present.
- Read active route, including VPN-underlay Wi-Fi fallback; read PipeWire/WirePlumber/PulseAudio volume and mute using bounded subprocesses.
- Launch installed XFCE settings utilities instead of fake toggles; the probes run on a background worker to keep GTK responsive.

### Theme conflict remediation and safety

- Automatically recognize *exact* official 0.6, 0.7.0 and 0.7.1 assets by embedded trusted Git blob hashes, then upgrade with **dated whole-theme backups**.
- Leave user-modified themes untouched by default; use the explicit, confirmed Hub **Repair local theme assets…** button or `macrice rice repair-assets STYLE` to back up and replace only that style's assets.
- Fail closed on symlinks, unmanaged paths and unexpected files. Keep macOS implementation, D-Bus IDs, session coordinators and user state compatible.

### Validation

- Full Python regression suite, six virtual-X11 shell smoke tests, native Wnck window-lifecycle test, and 12 real GTK menu/control captures in CI.
- Physical Mint XFCE battery/Plank/multi-monitor acceptance remains outstanding; release is a **pre-release** until confirmed.

## 0.7.1 — Consistent RiceBowl branding (3 November 2026)

- Standardized RiceBowl names across GTK window titles, sidebar icon, desktop entries, system tools, documentation and the package metadata (which previously reported 0.5.0rc2).
- GitHub repository now uses the canonical name `CopyPasteUser/RiceBowl`; old `CopyPasteUser/RiceHub` URLs redirect.
- Updated visible GTK/icon theme names and the accessible labels in original SVG artwork; retained the existing RiceHub-prefixed theme directories as compatibility identifiers.
- Safely recognize exact old theme metadata and managed autostart entries. Back up original theme indices and SVG metadata before an atomic label-only migration; customized artwork and entries are not overwritten.
- Updated the source asset generators and added migration regression tests. This maintenance release supersedes v0.7.0 without changing the working macOS rice.

## 0.7.0 — RiceBowl identity and themed controls (3 November 2026)

### Desktop experience
- Introduced the RiceBowl name, original rice-bowl SVG application icon and user-local `ricebowl` desktop/CLI launcher.
- Refined live system-control panels for XP Luna, Windows 98/2000 Classic, ChromeOS and Frutiger Aero. The controls expose actual available XFCE/system settings applications and disable unavailable commands.
- Added differentiated Thunar toolbars, location controls and sidebars for **all six non-macOS** desktop families (Aero 7, Ten, XP, Classic, ChromeOS, Frutiger). Existing 0.6 managed CSS is recognized during upgrades, while modifications outside the owned block remain untouched.
- Preserved the existing macOS implementation and dock behavior.

### Upgrade safety
- The `ricehub` and `macrice` commands, user state paths, managed startup entries and D-Bus shell identifiers remain compatible.
- The old RiceHub desktop shortcut stays installed but is hidden from the app menu to avoid duplicates.
- Added regression tests for new/legacy launcher coexistence, Thunar migration, custom CSS protection and SVG validity.
- Repository rename is **not complete**. Until owner-side GitHub Settings changes the name, the canonical clone URL remains `CopyPasteUser/RiceBowl`.

### Validation
- Automated Python tests and isolated GTK/X11 checks are managed by the repository's GitHub Actions workflow; results must be checked per commit.
- Physical Linux Mint XFCE multi-monitor, compositor, fast profile switching and Plank-autostart acceptance remain open.

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
