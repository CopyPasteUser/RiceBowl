# RiceBowl 0.8.0 — Distinct Rices and native system tray

RiceBowl 0.8.0 is an XFCE/X11 pre-release centered on **six genuinely different non-macOS desktops**. The proven macOS rice, user configuration, Plank settings, backup system and old launcher aliases remain unchanged.

## Desktop and artwork

- Original **42 differentiated application and place icons** (file manager, settings, browser, terminal, home, folder, trash) for Windows 7 Aero, Windows 10, XP Luna, Classic 98/2000, ChromeOS and Frutiger Aero.
- **66 matching status icons**, four individual heritage Start graphics and more expressive rice-specific taskbar/button/control CSS.
- ChromeOS has a centered search and app-grid launcher, rather than the Windows 10 tile interface. Frutiger Aero has a separate aqua/eco dashboard; other profiles retain their own era-appropriate Start menus and system controls.

## Battery, network and sound

- The lower-right status area now displays **real battery charge and charging state**, not a fabricated icon. No battery: no battery widget.
- Active Wi-Fi and Ethernet are determined from Linux interfaces and routing, with a VPN fallback for underlying Wi-Fi.
- Audio percent and mute come from WirePlumber/PipeWire or PulseAudio, with bounded subprocesses and no UI-thread blocking.
- Network, sound and battery buttons open appropriate installed settings tools; disabled or unavailable features are clearly reported.

## Theme migration and recovery

- The prior `Existing customized theme conflicts with RiceBowl` bug caused by routine official asset updates is addressed with a **version-aware migration**. Exact official 0.6, 0.7.0 and 0.7.1 assets are verified against bundled known Git hashes and upgraded with a dated full backup.
- Unknown modifications still cannot be silently overwritten. The Hub's **Repair local theme assets…** action or `macrice rice repair-assets ten-dark` deliberately backs up and replaces only that Rice's themes/icons. No current desktop setting is switched by repair.
- Reject symlinks and unmanaged asset paths; existing D-Bus IDs, theme directory names, old `ricehub` and `macrice` commands remain compatible.
- Explicit repair of Windows 10 Dark or Light affects **only the selected variant plus its shared icon pack**; edits to the other variant remain untouched.

## Verification and remaining gates

GitHub Actions runs the Python suite, native GTK/X11 smoke and window tracking tests, and captures real GTK menu/control screenshots under a virtual X11 desktop. The release contains a source ZIP, SHA-256 checksum and the new captures.

**Physical Linux Mint XFCE acceptance is not yet complete**: repeat switching, real battery, Wi-Fi under VPN, Plank autostart, multi-monitor and external display/compositor behavior should be checked on target hardware before promoting this from pre-release.

## Upgrade

From a clone of the canonical repository:

```bash
git pull --ff-only
bash install.sh --dry-run
bash install.sh
ricebowl
```

Or clone: https://github.com/CopyPasteUser/RiceBowl

Details: [README](README.md), [0.8.0 roadmap](RELEASE_0_8_0_ROADMAP.md), [Changelog](CHANGELOG.md).

## Pre-release verification record

The release candidate passed [GitHub Actions run 41585293457](https://github.com/CopyPasteUser/RiceBowl/actions/runs/41585293457):
**175 core Python tests**, native GTK/X11 smoke coverage for each desktop family, existing component regression suites, and **12 independently validated 1600 × 900 PNG captures** of real GTK windows under virtual X11. The captured gallery is attached to this GitHub pre-release, rather than represented as physical Mint screenshots.

The project has not yet passed physical Mint XFCE acceptance for Plank coexistence, battery charging on hardware, monitor hotplugging and long-running session changes.
