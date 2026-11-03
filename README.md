<div align="center">

<img src="assets/ricebowl-symbolic.svg" alt="RiceBowl logo — a bowl of rice" width="108">

# RiceBowl

**Seven desktop personalities. One reversible XFCE session.**

A lightweight, native GTK3 desktop-style manager for Linux Mint XFCE and other XFCE/X11 environments.

[Latest release](https://github.com/CopyPasteUser/RiceBowl/releases/tag/v0.7.1) · [Changelog](CHANGELOG.md) · [Development roadmap](ROADMAP.md) · [CI](https://github.com/CopyPasteUser/RiceBowl/actions)

</div>

## What is RiceBowl?

RiceBowl transforms an XFCE desktop using original GTK3, XFWM4, icon, wallpaper, taskbar, launcher and file-manager themes. Select a desktop in the graphical hub, review its requirements and apply it with a restore snapshot. The application is written in Python/GTK3, without an Electron runtime, remote services or telemetry.

**Version 0.7.1** introduces the RiceBowl name and rice-bowl logo, profile-specific control panels, and more differentiated Thunar styling across the non-macOS rices. The established macOS rice is intentionally unchanged.

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

### Gallery

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
