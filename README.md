<div align="center">

<img src="assets/ricebowl-symbolic.svg" alt="RiceBowl logo — a bowl of rice" width="108">

# RiceBowl

**Seven desktop personalities. One reversible XFCE session.**

A lightweight, native GTK3 desktop-style manager for Linux Mint XFCE and other XFCE/X11 environments.

[Latest release](https://github.com/CopyPasteUser/RiceBowl/releases/tag/v0.8.0) · [Changelog](CHANGELOG.md) · [Development roadmap](ROADMAP.md) · [CI](https://github.com/CopyPasteUser/RiceBowl/actions)

</div>

## What is RiceBowl?

RiceBowl transforms an XFCE desktop using original GTK3, XFWM4, icon, wallpaper, taskbar, launcher and file-manager themes. Select a desktop in the graphical hub, review its requirements and apply it with a restore snapshot. The application is written in Python/GTK3, without an Electron runtime, remote services or telemetry.

**Version 0.8.0** is the **visual-identity and hardware-status release**: XP, Classic, ChromeOS, Frutiger Aero, Windows 7 and Windows 10 now have distinct hand-drawn app/places icons and themed notification indicators. ChromeOS and Frutiger use their own launcher structures rather than a repainted Windows menu. Taskbars read actual battery percentage/charging state, network route and audio state. The macOS rice is intentionally unchanged.

## Desktop families

| Desktop | Included experience |
| --- | --- |
| **macOS · Aurora** | MacBar, MacMenu, Control Center, optional Plank dock, three palettes |
| **Windows 7 · Aero** | Glass-inspired taskbar, live Start search, Aero window chrome, control panel |
| **Windows 10 · Ten** | Dark/light styles, Start tiles, running apps, Action Center |
| **Windows XP · Luna** | Blue/green taskbar, XP-inspired Start, categorized control panel |
| **Windows 98 / 2000 · Classic** | Compact gray taskbar, classic Start, square dialogs and controls |
| **ChromeOS · Pastel Shelf** | Centered app launcher, rounded shelf and device settings |
| **Y2K · Frutiger Aero** | Aqua-inspired shell, original wallpaper, glossy controls and icons |

All seven families are installable and reversible. The non-macOS menus launch **real applications** from the desktop catalog, with Wnck-based window buttons when the relevant library is present. Control panels open installed system utilities; unavailable tools are disabled rather than simulated. No Microsoft, Google or Apple proprietary assets are bundled.

### Current 0.8.0 live-X11 gallery

The images below are created by GitHub Actions from real GTK3 windows under a virtual X11 desktop. They are **not static mockups** or captures from a physical Mint system. The hardware test on a laptop remains pending.

| XP Luna | Windows 98 / 2000 Classic |
| --- | --- |
| ![RiceBowl XP Luna Start menu](https://github.com/CopyPasteUser/RiceBowl/releases/download/v0.8.0/ricebowl-winxp-start-0.8.0.png) | ![RiceBowl Classic Start menu](https://github.com/CopyPasteUser/RiceBowl/releases/download/v0.8.0/ricebowl-winclassic-start-0.8.0.png) |

| ChromeOS | Frutiger Aero |
| --- | --- |
| ![RiceBowl ChromeOS launcher](https://github.com/CopyPasteUser/RiceBowl/releases/download/v0.8.0/ricebowl-chromeos-start-0.8.0.png) | ![RiceBowl Frutiger dashboard](https://github.com/CopyPasteUser/RiceBowl/releases/download/v0.8.0/ricebowl-frutiger-start-0.8.0.png) |

| Windows 7 Aero | Windows 10 |
| --- | --- |
| ![RiceBowl Aero 7 Start menu](https://github.com/CopyPasteUser/RiceBowl/releases/download/v0.8.0/ricebowl-aero-start-0.8.0.png) | ![RiceBowl Windows 10 Start menu](https://github.com/CopyPasteUser/RiceBowl/releases/download/v0.8.0/ricebowl-windows10-start-0.8.0.png) |

[Browse all 12 menu and control-panel captures in the v0.8.0 release](https://github.com/CopyPasteUser/RiceBowl/releases/tag/v0.8.0).

### Historical gallery

| Windows 7 Aero | Windows 10 |
| --- | --- |
| ![Windows 7-inspired running XFCE desktop](screenshots/windows7-aero-desktop-0.3.0rc2.png) | ![Windows 10-inspired GTK3 Start menu](screenshots/windows10-live-start-0.5.0rc2.png) |
| [Start menu](screenshots/windows7-aero-startmenu-0.3.0rc2.png) · [Thunar](screenshots/windows7-aero-files-0.3.0rc2.png) | [Action Center](screenshots/windows10-live-actions-0.5.0rc2.png) |

| Windows XP Luna | Classic 98/2000 |
| --- | --- |
| ![Windows XP Luna GTK3 launcher](screenshots/ricehub-winxp-start-0.6.0.png) | ![Classic 98/2000 GTK3 launcher](screenshots/ricehub-winclassic-start-0.6.0.png) |

| ChromeOS | Frutiger Aero |
| --- | --- |
| ![ChromeOS-inspired running GTK3 launcher](screenshots/ricehub-chromeos-start-0.6.0.png) | ![Frutiger Aero GTK3 launcher](screenshots/ricehub-frutiger-start-0.6.0.png) |

**Screenshot provenance:** these are real virtual-X11 captures from earlier releases (0.3–0.6), retained as historical examples. They are **not** new 0.7 captures or evidence of physical Linux Mint acceptance. The macOS + Plank full-desktop image in the repository is an illustrative composition, not a live capture.

## Install

**Target:** XFCE on X11. Install as your regular desktop user, never with `sudo`.

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-wnck-3.0
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

RiceBowl recognizes exact original theme/icon files from releases 0.6, 0.7.0 and 0.7.1. Unmodified old assets are upgraded with a dated backup under `~/.local/share/{themes,icons}/.ricebowl-asset-backups/`. Genuine user modifications are **never silently overwritten**. If `Check requirements` reports an existing customized theme, select **Repair local theme assets…** in the hub (confirmation and backup required), or run:

```bash
macrice rice repair-assets ten-dark  # Explicitly replace only this Rice's bundled assets
macrice rice plan ten-dark           # Read-only verification
macrice rice apply ten-dark          # Apply after confirmation / snapshot
```

You can replace `ten-dark` with another non-macOS style. This repairs theme/icon assets only; it does not delete your XFCE settings or Plank configuration. Review the preserved recovery folders before cleaning them up.

### Live taskbar indicators

The **battery** reads Linux power_supply capacity and charging status (including weighted multi-battery devices); on machines without a battery the battery widget is hidden. **Wi-Fi/Ethernet** is based on the active physical route, including VPN-tunnel fallbacks. **Audio** reads PipeWire/WirePlumber or PulseAudio with bounded calls. No unavailable state is displayed as a working toggle, and every indicator opens a real settings application where installed.

## Architecture and safety

- **GTK3 desktop hub:** `macrice/hub.py`, catalog, installation preflight and backups.
- **Native shell layer:** shared GTK/Gio/Wnck lifecycle for Windows-style and other non-macOS bars, with independent per-rice styling.
- **macOS components:** MacMenu, Control Center and MacBar are maintained within `components/` and intentionally preserved.
- **Thunar:** scoped CSS, original icon/GTK theme assets and reversible user settings. Customized GTK CSS outside the managed section is preserved.
- **Recovery:** settings snapshots and explicit restore, bounded private logs, user-local files, no silent package installation.

**Upgrade compatibility:** RiceBowl retains some legacy `RiceHub-*` internal theme identifiers, D-Bus names, state paths, managed autostart filenames and the `macrice` command. These are intentional compatibility contracts for older installations and restore points, **not the public product name**. The old `ricehub` shortcut is hidden from the application menu but remains executable.

## Validation and 0.7.1 screenshots

The [GitHub Actions test workflow](https://github.com/CopyPasteUser/RiceBowl/actions/workflows/ci.yml) runs the Python suite and native GTK/X11 checks. Its `ricebowl-0.7.1-native-x11-captures` artifact contains fresh virtual-display launcher/control screenshots for XP, Classic, ChromeOS and Frutiger. These are not physical Linux Mint screenshots and are intentionally kept separate from the historical screenshots above.

## Limitations

Physical Linux Mint XFCE validation of fast desktop switching, multiple monitors, login/resume and interactions with an independently configured Plank autostart is still outstanding. True live compositor blur, legacy XEmbed tray compatibility and full Wayland support are not claimed. The CI workflow runs Python regression tests and isolated GTK/X11 integration checks; it does not replace hardware acceptance.

For technical details, see [Windows 7](WINDOWS7.md), [Windows 10](WINDOWS10.md), [release notes](RELEASE_NOTES.md), [migration notes](RICEBOWL.md) and the [historical architecture notes](RICEHUB.md).

## Repository name and compatibility

The canonical repository is **`CopyPasteUser/RiceBowl`**. GitHub redirects older `CopyPasteUser/RiceHub` links, but new clones and documentation use the RiceBowl URL. The existing `ricehub` command and legacy `RiceHub-*` theme/state identifiers remain supported for compatibility; do not rename them manually.

## License

MIT. Original project artwork and code; not affiliated with the operating-system vendors whose interfaces inspired the rices. See [LICENSE](LICENSE), [contributors](CONTRIBUTORS.md) and [contributing](CONTRIBUTING.md).
