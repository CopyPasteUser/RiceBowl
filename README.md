<div align="center">

<img src="assets/ricebowl-symbolic.svg" alt="RiceBowl logo" width="88">

# RiceBowl

**Seven desktop styles. One reversible XFCE session.**

A lightweight, native Python/GTK3 desktop customization hub for **Linux Mint XFCE and other XFCE/X11 desktops**.

[Get started](#get-started) · [Styles](#styles) · [Gallery](#gallery) · [Roadmaps](#roadmaps)

</div>

RiceBowl changes real Linux desktop elements—taskbar, Start/launcher, menus, system controls, wallpaper, GTK/XFWM4 themes, icons and Thunar styling. Applications and device controls use real Linux backends. No Electron, telemetry or proprietary OS assets.

> **Release status: 0.9.1+ development — not yet stable 1.0.** The [v0.9.1 pre-release](https://github.com/CopyPasteUser/RiceBowl/releases/tag/v0.9.1) remains the last tagged build. Recovery, diagnostics and deeper Aqua controls passed the [PR #65 native-X11 CI](https://github.com/CopyPasteUser/RiceBowl/pull/65). **The newer Bluetooth scan/display-readout changes need their own CI, and physical Mint/XFCE acceptance remains open.**

| 1.0 workstream | Engineering status | Remaining gate |
| --- | --- | --- |
| Six non-macOS shells and stock XFCE recovery | ✅ Automated switching/rollback tests | Real login, HDMI and suspend tests |
| Health, opt-in update and performance report | ✅ Implemented and unit-tested | Native GUI CI, owner update/rollback drill |
| Frutiger Wi-Fi, sound, power, Bluetooth | ✅ Verified actions + on-demand BlueZ scan | Physical pairing/PIN confirmation, enterprise Wi-Fi |
| Frutiger calendar, USB mounts and media | ✅ GTK calendar, user-confirmed unmount, MPRIS controls | Physical-device checks and deeper polish |
| Aqua file manager and display arrangement | ◐ Native read-only X11 monitor topology | riceExplorer renderer and safe layout editor |

Track every remaining item in the [1.0 roadmap](ROADMAP.md) and [owner acceptance sheet](ACCEPTANCE_1_0.md). The **macOS Aurora UI is intentionally unchanged**.

## Styles

| Desktop | Distinctive experience |
| --- | --- |
| **macOS Aurora** | MacBar, MacMenu, Control Center and optional Plank dock |
| **[Windows 7 Aero](WIN7_AERO_ROADMAP.md)** | Glass Superbar, classic Start, window actions, Control Panel and native-history Action Center flag |
| **[Windows 10](WINDOWS10_ROADMAP.md)** | Flat taskbar and Start tiles, native Settings, network list, Task View and real device/notification controls |
| **[Windows XP Luna](XP_LUNA_ROADMAP.md)** | Blue/green taskbar, XP Start, Help and Control Panel |
| **[Windows 98 SE](CLASSIC_98_ROADMAP.md)** | Classic Start/Run/Find/Help, Quick Launch, System Properties and live device dialogs |
| **[ChromeOS](CHROMEOS_ROADMAP.md)** | Shelf, Launcher, Quick Settings, calendar and Settings |
| **[Frutiger Aero](FRUTIGER_AERO_ROADMAP.md)** | Aqua World launcher, real device controls and Bluetooth discovery, local calendar, USB/network mounts, MPRIS playback, X11 display readout |

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
macrice doctor
macrice update check --refresh
macrice update apply --yes
```

For a strictly pinned CLI update, append `--revision <full SHA shown by check>`;
the Hub's confirmation always pins its reviewed revision automatically.

The **Recovery** tab also has read-only health checks and a user-confirmed
updater. The updater accepts a clean official Git `main`, stages a pinned
revision and attempts archived recovery on install failure. It does **not**
verify signed releases or guarantee atomic multi-component rollback. For a
manual source update, `cd "$HOME/RiceBowl" && git pull --ff-only && bash install.sh`
still works. Never run any installer/updater with `sudo`.

### Switch and recover

```bash
ricebowl                       # Open the hub
macrice rice plan aero-meadow  # Check the change without applying it
macrice rice apply aero-meadow # Apply Windows 7 Aero
macrice rice apply frutiger    # Switch to Aqua World
macrice rice restore           # Restore the previous desktop settings
macrice session-sync           # Reconcile the current session after login
macrice session-keys-restore   # Restore prior keyboard shortcuts
macrice performance report --samples 5 --json  # On-demand PSS/CPU/threads
```

The active rice uses **Super** for its launcher and **Right Ctrl** for Control Panel / Quick Settings. Managed assets and keyboard shortcuts are backed up; later user edits are not silently overwritten.
The resource report includes the six non-macOS RiceBowl shells when running and does not install an always-on monitor. A failed shell startup or panel handoff attempts to recover the original XFCE panel and shortcuts. Check recovery on your real XFCE machine before relying on it unattended.

## Scope

- **XFCE/X11** is the supported target; Wayland and full Windows DWM-style blur are outside current support.
- **Thunar stays available.** [riceExplorer](https://github.com/CopyPasteUser/riceExplorer) is a separate, still-developing Rust file manager and is not yet the default.
- **Riceware API 1.0:** shared, opt-in Linux backends for [riceSpice, ricePop, ricePlate and riceWine](RICEWARE_FOUNDATIONS.md). These are internal modules, not four additional background daemons.
- **Migration status:** XP Luna and Windows 7 Aero use riceSpice for taskbar status, real device flyouts and ricePlate desktop shortcuts; Windows 7 also reads ricePop history. **Windows 98 SE** has distinct classic device dialogs and a read-only ricePlate inspector. **Windows 10** has verified hardware controls and ricePop history in Action Center. **ChromeOS** uses bounded riceSpice/ricePop for its Material You Shelf, Settings and notifications. **Frutiger Aero** uses the same verified worker for its Aqua Control Center, tray and compact Wi-Fi, audio, power and MPRIS flyouts, plus a local calendar and Gio mounts with confirmed, asynchronous unmount. Nearby Bluetooth discovery is bounded and cancels on close; pairing delegates PIN approval to the default BlueZ system agent. X11 monitor mode/position readout is native and read-only, leaving potentially disruptive writes to XFCE's rollback-capable display settings. Enterprise Wi-Fi flows also remain system-owned. An Aqua notification flyout reads XFCE's real ricePop history. [Migration checklist](RICEWARE_MIGRATION_GUIDE.md). No default file manager or notification owner is replaced.
- **Windows 10 next-stage UI:** Its Start Settings entry opens a **separate Windows-10-styled Settings shell** with category search, back navigation, Sound/Display/Notifications pages and verified hardware controls. The taskbar network icon opens a real NetworkManager Wi-Fi list with rescan, connect/disconnect and truthful credential errors; Task View switches actual X11 windows and XFCE workspaces, with user-triggered create/move/safe-last-desktop removal. Where installed, Start offers an **opt-in RiceExplorer preview** using `rice-explorer --theme win10`, with Thunar left as the default. Global Win+I/Win+Tab bindings, deep per-category Settings features and physical hardware acceptance are **not complete**.
- Linux hardware availability and permissions determine which real actions are enabled. Missing capabilities are explained instead of simulated.
- All artwork is original. RiceBowl is not affiliated with Apple, Google or Microsoft.

## Roadmaps

- [RiceBowl 1.0 roadmap](ROADMAP.md) — shared session, release and hardware gates
- [1.0 owner acceptance](ACCEPTANCE_1_0.md) — full switching, security, performance and hardware checklist
- [Riceware ecosystem](RICE_ECOSYSTEM_ROADMAP.md) — **riceExplorer, riceSpice, ricePop, ricePlate and riceWine** · [backend usage](RICEWARE_FOUNDATIONS.md)
- [Changelog](CHANGELOG.md) · [CI checks](https://github.com/CopyPasteUser/RiceBowl/actions) · [Contributing](CONTRIBUTING.md) · [MIT license](LICENSE)
