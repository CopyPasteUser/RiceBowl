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
| Per-rice taskbar / launcher skin | `macrice/heritage_shell.py` or `macrice/ten_shell.py` |
| Desktop GTK/XFWM/icons/wallpaper assets | `scripts/build_heritage_assets.py` → checked-in `assets/` |
| Exclusive active shell, Plank, MacBar and XFCE panel | `macrice/shell_session.py` |
| Recoverable Super_L and Control_R shortcuts | `macrice/session_shortcuts.py` |
| Backups and partial restore | `macrice/rice.py`, schema 5 |

## Desktop identity

- **Aurora / macOS:** restrained dark/light WhiteSur, native MacBar and user-managed Plank.
- **Windows 7:** icon-only Aero penguin Start orb, 42px glass Superbar,
  active/hover glass task backplates, two-column white-program/blue-places Start,
  working All Programs and search, amber session-dialog shutdown, original blue
  XFWM4 frame/button sprites and Explorer-like Thunar controls. The live Win7
  shell owns `win7-*` CSS classes and `_create_win7_menu()` in `aero_shell.py`;
  `scripts/build_aero_assets.py` owns the checked-in original XFWM4/icon artwork.
  The distinct XP, Classic, Frutiger and Windows 10 shells must not be restyled.
- **Windows 10:** flat neutral panels and blue highlights with an original blue penguin.
- **XP Luna:** 40px cobalt/green molded taskbar, contiguous bright-cyan notification
  tray, user-account Start header, ivory programs and pastel-blue system-links
  columns, separate log-off/power affordances, and a warm meadow wallpaper.
  Live menu structure and geometry are in `macrice/aero_shell.py`; all XP-only
  colors and states are in `heritage_shell.DETAIL_CSS["winxp"]`.
  `scripts/build_heritage_assets.py --luna-only` refreshes the original drawn
  XFWM4 titlebar/button states and layered GTK/Thunar controls without touching
  other reviewed themes. XP artwork is original; preserve valid installed
  `.desktop` launchers and disabled unavailable Linux utilities.
- **98 / 2000:** square relief borders, cool gray chrome, high-density menus and teal wallpaper.
- **ChromeOS:** light pastel background, soft shelf, rounded launcher and quiet blue accents.
- **Frutiger Aero:** translucent cyan-to-turquoise panels, nature-inspired green landscape and airy highlights.

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
