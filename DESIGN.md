# RiceBowl visual and interaction contract

RiceBowl is an XFCE/X11 desktop-style studio. The GTK3 manager is intentionally
modern and compact; the *applied desktop shells* follow the visual language of
their selected era. The app is not a pixel-accurate OS emulator, and all art is
original Linux artwork. Windows 11 and Liquid Glass are out of scope.

## Canonical owners

| Concern | Source of truth |
| --- | --- |
| Catalog names, variants and status | `macrice/hub_catalog.py` |
| User-visible full-rice presets | `macrice/rice.py` |
| Native shell lifecycle / keyboard / window list | `macrice/aero_shell.py` |
| Per-rice taskbar / launcher skin | `macrice/heritage_shell.py`, `macrice/chrome_shell.py` or `macrice/ten_shell.py` |
| Desktop GTK/XFWM/icons/wallpaper assets | `scripts/build_heritage_assets.py` and targeted `scripts/build_chrome_assets.py` → checked-in `assets/` |
| Exclusive active shell, Plank, MacBar and XFCE panel | `macrice/shell_session.py` |
| Recoverable Super_L and Control_R shortcuts | `macrice/session_shortcuts.py` |
| Backups and partial restore | `macrice/rice.py`, schema 5 |

## Desktop identity

- **Aurora / macOS:** restrained dark/light WhiteSur, native MacBar and user-managed Plank.
- **Windows 7:** icon-only Aero penguin Start orb, 48px glass Superbar,
  smoky slate-blue (not cyan-water) taskbar with active/hover glass backplates,
  two-column ivory-program/steel-blue-places Start,
  working All Programs and search, amber session-dialog shutdown, original blue
  XFWM4 frame/button sprites and Explorer-like Thunar controls. The Aero file
  manager has its own light Windows 7 Explorer styling in
  `macrice/thunar.py:AERO_EXPLORER_CSS`: native flat toolbar buttons, a unified
  breadcrumb, unboxed shortcut navigation, white canvas and pale status strip.
  The applied profile manages Thunar's real `/last-menubar-visible` Boolean:
  hidden in Seven, restored visible on the other rices, journaled for rollback.
  Original golden folder, drive, network and MIME-type icons live in the Aero
  icon theme's scalable places/mimetypes directories; they never alter the
  other themes. True Libraries, native details pane and contextual Explorer
  commands are beyond CSS-only Thunar theming and are not simulated. The live Win7
  shell owns `win7-*` CSS classes and `_create_win7_menu()` in `aero_shell.py`;
  `macrice/aero_superbar.py` groups immutable Wnck snapshots by WM_CLASS,
  supplies active-aware group overflow, and feeds GTK window previews and Jump
  Lists. A 450ms Show Desktop hover provides reversible Peek; it is not full
  compositor transparency. `scripts/build_aero_assets.py` owns generated art;
  curated generic-folder SVG is maintained directly in `assets/icons/RiceHub-Aero/`.
  Both wallpapers now use a **2009 Aero cobalt/navy glow** with an original glass
  Linux penguin, not green valleys or watery transparency (those belong to
  Frutiger Aero). Stable profile keys `aero-meadow` / `aero-cascade` remain for
  backup compatibility; their visible names are **Aero Seven Blue / Night**.
  Runtime colors are owned by the `win7-*` CSS in `aero_shell.py` and mirrored
  here as design intent. `macrice/win7_control_panel.py` owns a separate real
  decorated 810×565 Control Panel window using the eight historical Windows 7
  categories, clickable task links, working category/detail/back navigation and
  search. Only installed XFCE/Linux tools can launch; missing actions are
  disabled with explanatory tooltips. Real device status and volume controls
  remain in a clearly named expandable Linux hardware region, never a fake
  Windows toggle. Its eight 64×64 original SVG category icons live exclusively
  in the Aero theme's `scalable/apps/ricehub-cp-*.svg` assets, avoiding accidental
  changes to other rices or missing system-theme glyphs. The Control Panel is
  opened from Start or `Control_R`; no
  anachronistic Control Panel gear occupies the right notification area. The
  48px bar carries larger pinned and running-app icons; Wnck supplies original
  large icons where available. XP, Classic, Frutiger and Ten stay untouched.
- **Windows 10:** native 22H2-era flat charcoal (#101014) 40px taskbar,
  compact four-pane/penguin Start mark, icon-only taskbar search opening the
  functional Start search field (not two simultaneous search boxes), icon-first
  running-app buttons with active bottom underline, real network/audio/battery
  status and a two-line clock. The ten-shell GTK CSS in macrice/ten_shell.py
  owns the runtime #0078d7 accent and rectangular hover/focus treatments.
  aero_shell._create_ten_menu() owns a three-zone nav rail / alphabetical Gio
  application list / genuine-app pinned tile groups (saved pins/context menus).
  The dark 362px Action Center is built by macrice/ten_action_center.py: a
  truthful RiceBowl notifications area, real Linux settings launchers and
  shared verified output volume, mute, network and battery readers, not fake
  connectivity switches. scripts/build_ten_assets.py owns the original deep
  cobalt four-pane beam/penguin wallpapers, crisp flat dark/light GTK3/Thunar
  controls and sharp 31px XFWM4 buttons. Exact historical original hashes in
  assets/trusted-ricebowl-ten-before-fidelity.json allow safe backup-backed
  upgrades while preserving custom theme edits. No blur, Win7 glass, XP gloss
  or Windows 11 centered widgets belong in Ten.
- **XP Luna:** 40px cobalt/green molded taskbar, contiguous bright-cyan notification
  tray, user-account Start header, ivory programs and pastel-blue system-links
  columns, separate log-off/power affordances, and a warm meadow wallpaper.
  Live menu structure and geometry are in `macrice/aero_shell.py`; XP-only
  colors and states are in `heritage_shell.DETAIL_CSS["winxp"]` and
  `CONTROL_DETAIL_CSS["winxp"]`. User folders resolve through XDG directory
  settings; missing folders offer an explicit create/open confirmation.
  `scripts/build_heritage_assets.py --luna-only` refreshes the original drawn
  XFWM4 titlebar/button states and layered GTK/Thunar controls without touching
  other reviewed themes. `macrice/luna_control_panel.py` is a centered XP category
  window with an actual Classic View switch, eight Linux-equivalent settings
  categories and a pale-blue sidebar with truthful network, battery and verified
  output-volume controls. `macrice/thunar.py:LUNA_EXPLORER_CSS` confines XP Explorer's
  warm beige toolbar, flatter path controls and blue tasks-pane treatment to
  Thunar; it cannot replace Thunar's actual shortcuts pane with Windows Explorer
  tasks. Missing Linux utilities remain visibly disabled. The window scrolls on
  compact monitors; XFCE taskbar/session recovery is unchanged.
- **98 / 2000:** visually faithful 1998 desktop: solid `#008080` wallpaper,
  compact 34px `#c0c0c0` taskbar, 19px original CRT/penguin Start badge,
  2px white/light-gray/dark recessed versus raised frames, `#000080` focused
  menu and active XFWM title, and 27px high hard-edged window title chrome.
  `aero_shell._create_classic_menu()` alone owns the dense 262px vertical
  `RiceBowl 98` side rail plus true GTK cascading Programs, Favorites,
  Documents and Settings; Find, Run, Help and Shutdown launch only real
  installed Linux services or are disabled. `heritage_shell.DETAIL_CSS[
  "winclassic"]` owns the live taskbar/menu states, including keyboard focus;
  `scripts/build_heritage_assets.py --classic-only` owns the original GTK,
  XFWM, pixel app icons and teal wallpaper, with carefully preserved existing
  curated folder artwork. `assets/trusted-ricebowl-classic-before-fidelity.json`
  enables safe, backup-backed upgrades of byte-identical older managed assets.
  The palette must never use gloss, water, transparency or XP-rounded controls.
  Its Control Panel uses an inset three-column icon view with centered labels
  and a vintage caption, rather than Luna's category navigation list.
- **ChromeOS / Material You:** independent pastel-indigo `#e7e9f8` and iris
  `#4b66d7` identity with an original flowing wallpaper, 56px shelf,
  consistent app circles, window activity underline and accessible status pill.
  `aero_shell._create_chrome_launcher()` renders a 610px left-anchored rounded
  app launcher: real Gio apps, four saved/favorite pinned shortcuts, bounded
  multirow grid, filter, keyboard focus, load-more and actual pin contexts.
  `macrice/chrome_quick_settings.py` renders a 396px bottom-right settings
  popup with date, verified Linux volume/mute, real network and battery status
  and only installed XFCE/NetworkManager utility navigation. It deliberately
  does not pretend to toggle Wi-Fi, Bluetooth or notifications; XFCE still
  owns notifications. Settings links use navigation chevrons, reserving toggle
  affordances for real controls whose state is verified.
  `macrice/chrome_shell.py` owns Chrome-only selectors and
  optional X11 rounded popup window shapes even without a compositor.
  `scripts/build_chrome_assets.py` generates this profile's original wallpaper,
  35px XFWM4 frames/buttons and light GTK3/Thunar styles. Rebuild with
  `python3 scripts/build_heritage_assets.py --chrome-only`; all-rice builds
  call the same generator last. The Chrome historical managed asset manifest
  allows safe upgrade of matching old installations, retaining user edits.
- **Frutiger Aero / Aqua World:** independent luminous turquoise/cyan and lime
  eco-futurist identity over original water/grass/blue-sky artwork. The live
  taskbar has a thick pearlescent top light, a recognizable aqua Start orb,
  rounded glass-like running-window capsules and a separate green-blue status
  cluster; it must never inherit Windows 7's slate-blue Superbar visual code.
  `_create_frutiger_menu()` renders a rounded `Your World` head with **real**
  Wi-Fi/Ethernet, audio and battery status; accessible search; four working
  system locations; and **Apps / Places / Settings** pages. The Apps view is an
  icon-first Gio app grid with working search, launch, Show more and pin menus;
  unavailable Linux settings tools are disabled. Dedicated selectors live in
  `heritage_shell.DETAIL_CSS["frutiger"]` and are scoped with `frutiger-*` /
  `aqua-*`. `scripts/build_heritage_assets.py --frutiger-only` regenerates
  original glossy XFWM4 button sprites and GTK3/Thunar widget styling without
  rebuilding other rices. Exact prior asset hashes in
  `assets/trusted-ricebowl-frutiger-before-aqua.json` allow backup-backed
  upgrades while protecting genuine user customization. This is native GTK
  refraction **suggestion**, not claimed GPU backdrop blur.
  The refined Aqua launcher puts real pinned/familiar Gio apps first, preserves
  full search and returns to Apps on reopening. Its locations resolve XDG
  folders and require explicit confirmation to create any that are missing.
  Frutiger alone uses `thunar.FRUTIGER_EXPLORER_CSS`, reducing the breadcrumb
  into a single pearl glass address surface, compacting real GTK toolbar
  actions and calming the file canvas and mint navigation pane. The native GTK
  asset generator mirrors this visual polish. The older unmodified Aqua GTK
  asset is upgradeable through an exact-hash manifest, without overwriting
  edited user themes. A future optional RiceExplorer could own the structural
  UI that GTK CSS cannot control; Thunar remains the stable default.

Desktop styles must remain recognizable without blur, desktop GPU effects or
third-party panels. Do not depend on non-existent proprietary OS resources.
`heritage_shell.CSS` is the live shell palette; the build script creates matching
GTK/XFWM assets. Change both together when a theme identity changes.

## Behavioral rules

- `Super_L` toggles the active rice's menu; `Control_R` toggles its quick settings.
- Every shell performs actual Gio app discovery/launch and event-driven Wnck
  task switching. Menu and settings are independent toggles with Escape support.
- Exactly one RiceBowl taskbar may be active. The manager must stop inactive bars,
  Plank and MacBar before starting the selected taskbar; XFCE's stock panel
  exits only after a successful replacement handoff.
- A preview remains read-only sample data, even when its rice is installable.
- Applying a rice journals a backup *before* writing XFCE preferences.
  Restoration preserves subsequent user edits and never overwrites custom art.
- Desktop workarea and search/menu geometry adapt to the current monitor.
- GTK3 semantic button widgets, explicit accessible names, visible focus, and
  keyboard search are core features; color alone must not indicate activity.

## Release acceptance

Headless tests, native GTK/Xvfb shell smoke, window-close crash regression,
fresh install, login reconcile, rapid multi-rice switching and real Mint XFCE
hardware tests must pass before declaring a fully stable release. Screenshots
must be real X11 captures or explicitly labeled illustrations.

The gallery also needs genuine Thunar processes for all six non-macOS rices,
with their own GTK, icon and XFWM4 themes under a real X11 window manager.
Disposable `*-workspace-*` captures are not image-composited file managers.
macOS still needs an equivalent current live MacBar/Plank capture. Neither
CI alone nor mockups replace the owner's real Mint/Plank sign-off.
