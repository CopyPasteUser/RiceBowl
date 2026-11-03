# RiceBowl changelog

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
