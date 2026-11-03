<div align="center">

<img src="assets/ricebowl-symbolic.svg" alt="RiceBowl logo — a bowl of rice" width="108">

# RiceBowl

**Seven desktop personalities. One reversible XFCE session.**

A lightweight, native GTK3 desktop-style manager for Linux Mint XFCE and other XFCE/X11 environments.

[Latest release](https://github.com/CopyPasteUser/RiceBowl/releases/tag/v0.9.1) · [Changelog](CHANGELOG.md) · [Development roadmap](ROADMAP.md) · [CI](https://github.com/CopyPasteUser/RiceBowl/actions)

</div>

## What is RiceBowl?

RiceBowl transforms an XFCE desktop using original GTK3, XFWM4, icon, wallpaper, taskbar, launcher and file-manager themes. Select a desktop in the graphical hub, review its requirements and apply it with a restore snapshot. The application is written in Python/GTK3, without an Electron runtime, remote services or telemetry.

**Current source:** Windows 7 Aero has its own 48px Superbar, grouped running windows,
native X11 window previews (with safe icon fallback), app Jump Lists, desktop Peek
and a two-column Start menu, plus a real eight-category Control Panel window
with working task navigation and links to installed Linux settings utilities.
XP Luna has a refined 2001-era Start with XDG-aware folder shortcuts, original
window chrome, a 40px taskbar, an XP-style category Control Panel with a
functional Classic View switch, and warm/beige Explorer-like Thunar controls.
The Control Panel keeps truthful network, battery and audio controls in its
blue side pane. **Windows 98 / 2000 Classic** now has the
authentic teal desktop, a compact 34px beveled taskbar, real cascading Start
hierarchies, a three-column icon-view Control Panel and square window chrome.
**Frutiger Aero / Aqua World** has a distinct
water-and-nature identity with pearl-glass taskbar, live Apps / Places / Settings
launcher, original refractive XFWM artwork and matching GTK/Thunar controls.
**Windows 10** now has a three-zone Start with genuine pinned app tiles and
an XFCE-backed right-side Action Center and a compact taskbar search button,
against original cobalt four-pane
Linux artwork and flat dark/light window and file-manager themes.
**ChromeOS / Material You** now has a distinct lavender 56px shelf, compact
bottom-left app launcher with pinned applications and a real searchable Gio
grid, and a bottom-right Quick Settings popup with verified volume/mute,
network/battery state and direct XFCE settings links. Its original pastel
abstract wallpaper, rounded window art and GTK/Thunar theme are independent
of every Windows desktop; navigation chevrons distinguish settings links from
real state controls. All of these operate on actual Linux applications and X11
windows; they do not emulate Windows or ship proprietary Microsoft assets.

The tagged **v0.9.1** package predates these fidelity improvements. For the
latest source use `main`; see [Windows 7 engineering notes](WIN7_AERO_ROADMAP.md),
[XP Luna engineering notes](XP_LUNA_ROADMAP.md) and
[Frutiger Aero implementation roadmap](FRUTIGER_AERO_ROADMAP.md) and
[Windows 98 implementation roadmap](CLASSIC_98_ROADMAP.md) and
[Windows 10 implementation roadmap](WINDOWS10_ROADMAP.md) and
[ChromeOS implementation roadmap](CHROMEOS_ROADMAP.md). RiceBowl verifies a
replacement taskbar is mapped before handing off from XFCE Panel and keeps
recoverable desktop settings backups.

## Desktop families

| Desktop | Included experience |
| --- | --- |
| **macOS · Aurora** | MacBar, MacMenu, Control Center, optional Plank dock, three palettes |
| **Windows 7 · Aero** | Cobalt-blue Linux-penguin wallpaper, golden folders, Explorer-style Thunar with original file icons, 48px glass Superbar, previews, Jump Lists, Peek, two-column Start and eight-category Control Panel |
| **Windows 10 · Ten** | 40px charcoal bar, blue four-pane Linux wallpaper, real three-zone Start with alphabetical apps/grouped tiles, compact running windows, tall functional Action Center, Explorer-like dark/light chrome |
| **Windows XP · Luna** | Molded blue/green 40px taskbar, two-column 2001 Start, XDG folders, original XFWM4 chrome, XP-style Thunar and centered category/Classic Control Panel with live system status |
| **Windows 98 / 2000 · Classic** | Flat teal wallpaper, 34px embossed taskbar, Linux-penguin Start badge, keyboard-operable classic Programs / Favorites / Documents / Settings cascades, original navy XFWM windows and coordinated GTK/Thunar 3D controls |
| **ChromeOS · Material You** | 56px pastel shelf, original flowing lavender wallpaper, real pinned Gio apps, searchable left-side Launcher, rounded Quick Settings with verified output volume/mute, truthful network/battery and XFCE device settings; matching GTK/Thunar and XFWM4 art |
| **Y2K · Frutiger Aero / Aqua World** | Sky/water/grass wallpaper, glossy cyan-and-lime live taskbar, original pearl-window chrome, large Gio app tiles, Apps / Places / Settings launcher and coordinated GTK/Thunar controls |

All seven families are installable and reversible. The non-macOS menus launch **real applications** from the desktop catalog, with Wnck-based window buttons when the relevant library is present. Control panels open installed system utilities; unavailable tools are disabled rather than simulated. No Microsoft, Google or Apple proprietary assets are bundled.

### Latest screenshots from `main`

These images show actual GTK3 shells captured under virtual X11, not design
mockups or proof of a physical Mint installation. The gallery also includes
real Thunar windows running under each rice's XFWM4, GTK and icon themes.
Superseded screenshots are excluded.

| Windows 7 Aero | Windows 10 |
| --- | --- |
| ![Windows 7 Aero Start and Superbar](screenshots/current/aero-start.webp) | ![Windows 10 Start](screenshots/current/windows10-start.webp) |

| XP Luna | Windows 98 / 2000 |
| --- | --- |
| ![Windows XP Luna desktop](screenshots/current/winxp-start.webp) | ![Windows Classic desktop](screenshots/current/winclassic-start.webp) |

| ChromeOS | Frutiger Aero |
| --- | --- |
| ![ChromeOS Material You search and app launcher](screenshots/current/chromeos-start.webp) | ![Frutiger Aero apps and places dashboard](screenshots/current/frutiger-start.webp) |

[Current Control Panels and six actual file-manager workspaces](screenshots/current/) · [CI full-resolution captures](https://github.com/CopyPasteUser/RiceBowl/actions/workflows/ci.yml)

The Aero Thunar screenshot comes from the passing **Explorer-refinement**
X11 capture; its Start and Control Panel remain from the verified previous
fidelity pass. The XP captures show its own later fidelity pass; other rice
images retain their last verified run; see
[capture provenance](screenshots/current/README.md).

| Windows 7: actual Thunar + XFWM4 | ChromeOS: actual Thunar + XFWM4 |
| --- | --- |
| ![Windows 7 real Thunar file manager](screenshots/current/aero-workspace.webp) | ![ChromeOS real Thunar file manager](screenshots/current/chromeos-workspace.webp) |

**File-manager scope:** the installed Thunar remains a functional GTK3 file manager; RiceBowl themes its window chrome, sidebar, toolbar, selected rows and path navigation. The conceptual "Recent + Downloads" dashboard in the reference images is **not** presented as an implemented Thunar feature.

For macOS, use the live shell on an XFCE/X11 session; the historical
composite mockups have been removed to avoid presenting them as current builds.

## Install

**Target:** XFCE on X11. Install as your regular desktop user, never with `sudo`.

```bash
sudo apt install python3-gi python3-cairo python3-gi-cairo gir1.2-gtk-3.0 gir1.2-wnck-3.0
git clone https://github.com/CopyPasteUser/RiceBowl.git
cd RiceBowl
bash install.sh --dry-run
bash install.sh
ricebowl
```

The installer creates user-local launchers and copies managed assets. **Installing alone does not apply a rice, terminate XFCE Panel, or overwrite your Plank configuration.** Some themes and macOS components have additional optional prerequisites shown by the built-in preflight.

Existing installation? Update using the same repo:

```bash
git pull --ff-only
bash install.sh --dry-run
bash install.sh
ricebowl
```

If installed from an old clone, keep that directory or clone afresh before updating. Do not run the installer as root.

### Everyday commands

```bash
ricebowl                            # Open the desktop-style manager
ricehub                             # Old launcher, kept for compatibility
macrice status                      # Inspect desktop and components
macrice rice plan winxp             # Inspect a theme before applying it
macrice rice apply winxp            # Apply with a recovery snapshot
macrice rice apply chromeos
macrice rice apply aero-cascade
macrice rice apply frutiger
macrice rice restore                # Restore latest applicable snapshot
macrice session-sync                # Reconcile current XFCE session
macrice session-keys-restore        # Restore previous keyboard bindings
```

RiceBowl binds the active rice's menu to **Super** and its quick settings / control panel to **Right Ctrl**, with backup and restoration of the previous XFCE shortcut bindings. The switch engine coordinates active taskbars, XFCE Panel and Plank without force-killing unrelated sessions.

### Theme upgrades and safe repair

RiceBowl recognizes exact original theme/icon files from earlier releases, including the pre-Aqua Frutiger theme. Unmodified old assets are upgraded with a dated backup under `~/.local/share/{themes,icons}/.ricebowl-asset-backups/`. Genuine user modifications are **never silently overwritten**. If `Check requirements` reports an existing customized theme, select **Repair local theme assets…** in the hub (confirmation and backup required), or run:

```bash
macrice rice repair-assets ten-dark  # Explicitly replace only this Rice's bundled assets
macrice rice plan ten-dark           # Read-only verification
macrice rice apply ten-dark          # Apply after confirmation / snapshot
```

You can replace `ten-dark` with another non-macOS style. This repairs theme/icon assets only; it does not delete your XFCE settings or Plank configuration. Review the preserved recovery folders before cleaning them up.

### Interactive device controls

The status area reads battery capacity/charging, the effective network connection and output volume. Clicking battery or sound opens the appropriate Rice's Control Panel. The new volume slider and mute button use PipeWire/WirePlumber or PulseAudio commands and verify the resulting device state before reporting success. The per-Rice Control Panels scroll on smaller displays rather than falling outside the screen. Missing audio backends are explicitly disabled.

### Live taskbar indicators

The **battery** reads Linux power_supply capacity and charging status (including weighted multi-battery devices); on machines without a battery the battery widget is hidden. **Wi-Fi/Ethernet** is based on the active physical route, including VPN-tunnel fallbacks. **Audio** reads PipeWire/WirePlumber or PulseAudio with bounded calls. No unavailable state is displayed as a working toggle, and every indicator opens a real settings application where installed.

## Architecture and safety

- **GTK3 desktop hub:** `macrice/hub.py`, catalog, installation preflight and backups.
- **Native shell layer:** shared GTK/Gio/Wnck lifecycle for Windows-style and other non-macOS bars, with independent per-rice styling.
- **macOS components:** MacMenu, Control Center and MacBar are maintained within `components/` and intentionally preserved.
- **Thunar:** scoped CSS, original icon/GTK theme assets and reversible user settings. Customized GTK CSS outside the managed section is preserved.
- **Recovery:** settings snapshots and explicit restore, bounded private logs, user-local files, no silent package installation.

**Upgrade compatibility:** RiceBowl retains some legacy `RiceHub-*` internal theme identifiers, D-Bus names, state paths, managed autostart filenames and the `macrice` command. These are intentional compatibility contracts for older installations and restore points, **not the public product name**. The old `ricehub` shortcut is hidden from the application menu but remains executable.

## Validation and screenshots

The [GitHub Actions workflow](https://github.com/CopyPasteUser/RiceBowl/actions/workflows/ci.yml)
checks the Python suite, all six native non-macOS GTK shells, window lifecycle,
small-screen clipping, Thunar's legacy CSS migration and real virtual-X11
screenshots with actual XFWM4-managed application windows. The checked-in
[`screenshots/current/`](screenshots/current/) gallery is refreshed from the
latest successful run; obsolete historical image files have been removed.

## Limitations

Physical Linux Mint XFCE validation of fast desktop switching, multiple monitors,
login/resume and an independently configured Plank autostart is still outstanding.
Aero Peek uses reversible Show Desktop hover, not Windows DWM compositing. GTK/X11
preview thumbnails are best-effort and fall back to real app icons when an X11
drawable cannot be read. Full DWM blur, legacy XEmbed tray compatibility and
Wayland support are not claimed.

For technical details, see [Windows 7](WINDOWS7.md), [Windows 10](WINDOWS10.md), [release notes](RELEASE_NOTES.md), [migration notes](RICEBOWL.md) and the [historical architecture notes](RICEHUB.md).

## Repository name and compatibility

The canonical repository is **`CopyPasteUser/RiceBowl`**. GitHub redirects older `CopyPasteUser/RiceHub` links, but new clones and documentation use the RiceBowl URL. The existing `ricehub` command and legacy `RiceHub-*` theme/state identifiers remain supported for compatibility; do not rename them manually.

## License

MIT. Original project artwork and code; not affiliated with the operating-system vendors whose interfaces inspired the rices. See [LICENSE](LICENSE), [contributors](CONTRIBUTORS.md) and [contributing](CONTRIBUTING.md).
