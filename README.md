<div align="center">

<img src="assets/ricebowl-symbolic.svg" alt="RiceBowl logo" width="88">

# RiceBowl

**Seven desktop styles. One reversible XFCE session.**

A lightweight, native Python/GTK3 desktop customization hub for **Linux Mint XFCE and other XFCE/X11 desktops**.

[Get started](#get-started) · [Styles](#styles) · [Gallery](#gallery) · [Roadmaps](#roadmaps)

</div>

RiceBowl changes real Linux desktop elements—taskbar, Start/launcher, menus, system controls, wallpaper, GTK/XFWM4 themes, icons and Thunar styling. Applications and device controls use real Linux backends. No Electron, telemetry or proprietary OS assets.

> **Development status:** `main` is ahead of the [v0.9.1 pre-release](https://github.com/CopyPasteUser/RiceBowl/releases/tag/v0.9.1). XP Luna, Windows 7 Aero, Windows 10, Windows 98 SE and ChromeOS integrate shared Riceware 1.0 backends. Windows 10 keeps its native Settings/network/Task View, Windows 98 its classic applets, and ChromeOS its Material You Settings/Quick Settings/notification center. Physical Mint device, multi-monitor and suspend acceptance remain open.

## Styles

| Desktop | Distinctive experience |
| --- | --- |
| **macOS Aurora** | MacBar, MacMenu, Control Center and optional Plank dock |
| **[Windows 7 Aero](WIN7_AERO_ROADMAP.md)** | Glass Superbar, classic Start, window actions, Control Panel and native-history Action Center flag |
| **[Windows 10](WINDOWS10_ROADMAP.md)** | Flat taskbar and Start tiles, native Settings, network list, Task View and real device/notification controls |
| **[Windows XP Luna](XP_LUNA_ROADMAP.md)** | Blue/green taskbar, XP Start, Help and Control Panel |
| **[Windows 98 SE](CLASSIC_98_ROADMAP.md)** | Classic Start/Run/Find/Help, Quick Launch, System Properties and live device dialogs |
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
- **Riceware API 1.0:** shared, opt-in Linux backends for [riceSpice, ricePop, ricePlate and riceWine](RICEWARE_FOUNDATIONS.md). These are internal modules, not four additional background daemons.
- **Migration status:** XP Luna and Windows 7 Aero use riceSpice for taskbar status, audio/Wi-Fi/Bluetooth/power/brightness flyouts and ricePlate for safe desktop shortcuts. Windows 7 reads XFCE notification history via ricePop. **Windows 98 SE** has distinct classic device dialogs and a read-only ricePlate desktop inspector. **Windows 10** uses verified hardware controls and ricePop notification history in its own Action Center. **ChromeOS** keeps its independent Material You shelf and hierarchical Settings, but taskbar status, Quick Settings/Settings device controls and notification history now use bounded riceSpice/ricePop requests with verified readbacks. [Migration checklist](RICEWARE_MIGRATION_GUIDE.md). No default file manager or notification owner is replaced.
- **Windows 10 next-stage UI:** Its Start Settings entry opens a **separate Windows-10-styled Settings shell** with category search, back navigation, Sound/Display/Notifications pages and verified hardware controls. The taskbar network icon opens a real NetworkManager Wi-Fi list with rescan, connect/disconnect and truthful credential errors; Task View switches actual X11 windows and XFCE workspaces, with user-triggered create/move/safe-last-desktop removal. Where installed, Start offers an **opt-in RiceExplorer preview** using `rice-explorer --theme win10`, with Thunar left as the default. Global Win+I/Win+Tab bindings, deep per-category Settings features and physical hardware acceptance are **not complete**.
- Linux hardware availability and permissions determine which real actions are enabled. Missing capabilities are explained instead of simulated.
- All artwork is original. RiceBowl is not affiliated with Apple, Google or Microsoft.

## Roadmaps

- [RiceBowl 1.0 roadmap](ROADMAP.md) — shared session, release and hardware gates
- [Riceware ecosystem](RICE_ECOSYSTEM_ROADMAP.md) — **riceExplorer, riceSpice, ricePop, ricePlate and riceWine** · [backend usage](RICEWARE_FOUNDATIONS.md)
- [Changelog](CHANGELOG.md) · [CI checks](https://github.com/CopyPasteUser/RiceBowl/actions) · [Contributing](CONTRIBUTING.md) · [MIT license](LICENSE)
