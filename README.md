<div align="center">

<img src="assets/ricebowl-symbolic.svg" alt="RiceBowl logo" width="88">

# RiceBowl

**Seven desktop styles. One reversible XFCE session.**

A lightweight, native Python/GTK3 desktop customization hub for **Linux Mint XFCE and other XFCE/X11 desktops**.

[Get started](#get-started) · [Styles](#styles) · [Gallery](#gallery) · [Roadmaps](#roadmaps)

</div>

RiceBowl changes real Linux desktop elements—taskbar, Start/launcher, menus, system controls, wallpaper, GTK/XFWM4 themes, icons and Thunar styling. Applications and device controls use real Linux backends. No Electron, telemetry or proprietary OS assets.

> **Development status:** `main` is ahead of the [v0.9.1 pre-release](https://github.com/CopyPasteUser/RiceBowl/releases/tag/v0.9.1). Automated X11 tests run in CI; final multi-monitor, suspend and device acceptance on physical Mint hardware is still open.

## Styles

| Desktop | Distinctive experience |
| --- | --- |
| **macOS Aurora** | MacBar, MacMenu, Control Center and optional Plank dock |
| **[Windows 7 Aero](WIN7_AERO_ROADMAP.md)** | Glass Superbar, classic Start, window actions and Control Panel |
| **[Windows 10](WINDOWS10_ROADMAP.md)** | Flat taskbar, Start tiles and Action Center |
| **[Windows XP Luna](XP_LUNA_ROADMAP.md)** | Blue/green taskbar, XP Start, Help and Control Panel |
| **[Windows 98](CLASSIC_98_ROADMAP.md)** | Classic Start/Run/Find/Help, Quick Launch and System Properties |
| **[ChromeOS](CHROMEOS_ROADMAP.md)** | Shelf, Launcher, Quick Settings, calendar and Settings |
| **[Frutiger Aero](FRUTIGER_AERO_ROADMAP.md)** | Aqua World launcher, native controls and glossy desktop |

All seven are installable profiles with separate visual identities. Their deeper feature-completion checklists remain open.

## Gallery

![Current native Windows 7 Aero shell](screenshots/current/aero-start.webp)

[View the full gallery — 32 current native-X11 screenshots across all rices](screenshots/current/README.md).

Screenshots are from a [passing 4 November 2026 GTK/XFWM4 CI run](https://github.com/CopyPasteUser/RiceBowl/actions/runs/41804502628), not mockups. Integrated macOS MacBar/Plank and physical-machine captures are still pending.

## Get started

Use an **XFCE session on X11**. Install prerequisites, then run the installer as your normal user:

```bash
sudo apt install -y git python3-gi python3-cairo python3-gi-cairo gir1.2-gtk-3.0 gir1.2-wnck-3.0
git clone https://github.com/CopyPasteUser/RiceBowl.git "$HOME/RiceBowl"
cd "$HOME/RiceBowl"
bash install.sh --dry-run
bash install.sh
"$HOME/.local/bin/ricebowl"
```

Installing does **not** apply a rice or stop XFCE Panel. Applying a style requires an explicit confirmation and creates a recovery snapshot.

### Update

From your existing checkout:

```bash
cd "$HOME/RiceBowl"
git pull --ff-only
bash install.sh --dry-run
bash install.sh
```

Never run `install.sh` with `sudo`.

### Switch and recover

```bash
ricebowl                       # Open the hub
macrice rice plan aero-meadow  # Check the change without applying it
macrice rice apply aero-meadow # Apply Windows 7 Aero
macrice rice apply frutiger    # Switch to Aqua World
macrice rice restore           # Restore the previous desktop settings
macrice session-sync           # Reconcile the current session after login
macrice session-keys-restore   # Restore prior keyboard shortcuts
```

The active rice uses **Super** for its launcher and **Right Ctrl** for Control Panel / Quick Settings. Managed assets and keyboard shortcuts are backed up; later user edits are not silently overwritten.

## Scope

- **XFCE/X11** is the supported target; Wayland and full Windows DWM-style blur are outside current support.
- **Thunar stays available.** [riceExplorer](https://github.com/CopyPasteUser/riceExplorer) is a separate, still-developing Rust file manager and is not yet the default.
- **Riceware foundations are available on `main`:** riceSpice, ricePop, ricePlate and an optional riceWine prototype expose real Linux capabilities through `macrice riceware`; seven-rice UI migration is still pending. [Commands and limits](RICEWARE_FOUNDATIONS.md).
- Linux hardware availability and permissions determine which real actions are enabled. Missing capabilities are explained instead of simulated.
- All artwork is original. RiceBowl is not affiliated with Apple, Google or Microsoft.

## Roadmaps

- [RiceBowl 1.0 roadmap](ROADMAP.md) — shared session, release and hardware gates
- [Riceware ecosystem](RICE_ECOSYSTEM_ROADMAP.md) — **riceExplorer, riceSpice, ricePop, ricePlate and riceWine** · [backend usage](RICEWARE_FOUNDATIONS.md)
- [Changelog](CHANGELOG.md) · [CI checks](https://github.com/CopyPasteUser/RiceBowl/actions) · [Contributing](CONTRIBUTING.md) · [MIT license](LICENSE)
