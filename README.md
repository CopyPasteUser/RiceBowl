# RiceHub

### Your desktop, your rules. A home for XFCE rices.

RiceHub is a small, native Linux app for turning an ordinary XFCE desktop into something personal. It started with a love of macOS's clean interface and XFCE's speed. The goal is bigger now: one friendly place to discover, preview, apply and eventually share complete desktop styles — without swapping out your desktop environment.

**The macOS-inspired rice works today.** Windows 7 has two reversible Aero-inspired styles and a GTK Start/taskbar implementation. **Windows 10 now has a first interactive GTK prototype**, while Windows 11 remains **Coming soon**. RiceHub `0.4.0 RC1` is a preview release, not a pixel-perfect multi-OS emulator or a physically validated stable release.

## Meet RiceHub

![RiceHub gallery displaying the new Windows 10 prototype](screenshots/ricehub-windows10-gallery-0.4.0rc1.png)

*Actual GTK3 RiceHub window in a virtual X11 session. Choose a rice, inspect its preview and check requirements for installable profiles. Windows 10 is still preview-only.*

### Windows 7: original Aero for Linux

| Complete desktop and Aero taskbar | Start menu and installed programs |
| --- | --- |
| ![Aero Cascade desktop with penguin Start button, pinned apps, clock and Show Desktop](screenshots/windows7-aero-desktop-0.3.0rc2.png) | ![Open GTK3 Aero Start menu with installed applications and places](screenshots/windows7-aero-startmenu-0.3.0rc2.png) |
| Thunar and original XFWM4 window decoration | Search in the Start menu |
| ![File manager in an Aero-decorated window over the Cascade wallpaper](screenshots/windows7-aero-files-0.3.0rc2.png) | ![Live Start-menu search filtered to installed terminal applications](screenshots/windows7-aero-search-0.3.0rc2.png) |

*Real RiceHub 0.3 RC2 captures from a temporary XFCE/X11 session, not painted mockups or a physical Linux Mint acceptance test. The optional Wnck window list and StatusNotifier icons were unavailable in this session, so they are not shown. See the [Windows 7 gallery and coverage notes](WINDOWS7.md#screenshots--coverage).*

The two included [Aero Meadow](assets/wallpapers/aero-meadow.jpg) and [Aero Cascade](assets/wallpapers/aero-cascade.jpg) wallpapers were created for this project. Windows 7 also includes:

- A unique glossy **Aero Penguin** Start symbol — Linux identity, no Windows logo.
- Original RiceHub-Aero **GTK3, XFWM4 window-border and icon themes**, plus matching Thunar styling.
- A lightweight bottom taskbar with pinned apps, a live clock, a searchable Start menu and **live running-window buttons**. Open windows can be activated, minimized and restored; extra windows appear in a compact overflow menu. The app catalog uses Gio and the optional window list uses Wnck signals, without process polling.
- A matching glass Plank theme. While Aero is selected, Plank moves to an autohiding left edge so it doesn't overlap the taskbar; the previous dock preferences are restorable.
- A user-local login autostart entry, created only when you apply an Aero rice and removed when returning to macOS.

The Aero shell now includes **experimental StatusNotifier tray icons**, **Show Desktop**, user-pinnable taskbar programs (persistent across logins), an adaptive Start menu, accessible keyboard search, native network/sound shortcuts and an opt-in translucent gradient. It can reserve the X11 bottom workarea for maximized windows. **Legacy XEmbed icons and true compositor blur are not supported.** The Start button and Escape close the menu; focus dismissal remains best-effort under X11. Existing MacBar or XFCE Panel instances are never forcibly terminated.

**[Explore every Windows 7 component and visual asset](WINDOWS7.md)** — complete file-by-file inventory, installation, customizations, verification, genuine screenshot gallery and open limitations. RiceHub contains no copied Microsoft visual assets.

For live window buttons on Linux Mint XFCE, install the optional Wnck3 introspection package:

```bash
sudo apt install gir1.2-wnck-3.0
```

Without Wnck, the Aero taskbar still opens with pinned apps, Start search and a clock. RiceHub does not install packages for you. Live-window tracking requires an X11 session, not Wayland.

### Windows 10: first interactive prototype

| Start menu, search and blue tiles | Action Center and quick actions |
| --- | --- |
| ![Live GTK3 Windows 10 concept with Start menu and sample tiles](screenshots/windows10-start-preview-0.4.0rc1.png) | ![Live GTK3 Windows 10 concept with Action Center](screenshots/windows10-action-center-preview-0.4.0rc1.png) |

*Real GTK3 screenshots in an isolated virtual X11 display, not an installed XFCE desktop. The visible applications and quick actions are interactive examples only; no system changes occur.*

Select **Windows 10** in RiceHub's Discover gallery and choose **Explore Windows 10 preview**. The prototype includes a left-aligned dark taskbar, searchable app list, a productivity tile group, an original blue wallpaper and a separate Action Center. Installation, live applications and system tray integration are next steps. See [Windows 10 prototype details and roadmap](WINDOWS10.md).

### macOS rice with Plank

![Illustrative macOS-inspired XFCE desktop with a Plank-style dock](screenshots/macos-rice-with-plank-0.2.0rc1.png)

*Illustrative complete-desktop composition, including a **Plank-style** dock. This is not a photograph of a live Plank installation; the virtual test session doesn't have Plank. For real GTK screenshots, see [MacMenu](components/macmenu/screenshots/), [Control Center](components/control-center/screenshots/) and [MacBar](components/macbar/screenshots/).*


## What's in RiceHub?

The hub itself is written with Python and GTK3. It opens when you need it and doesn't install a web stack, new resident daemon or telemetry service.

| Hub area | Available now |
| --- | --- |
| **Discover** | Browse and search OS-inspired rices, filter by availability, preview wallpaper palettes and check requirements before applying. |
| **My Desktop** | See detected GTK, window, icon, cursor, font and Plank settings without changing them. |
| **Components** | Toggle MacMenu and Control Center, start MacBar and Plank, inspect or explicitly repair bundled apps. |
| **Performance** | Choose Light, Balanced or Visual settings; measure process memory and CPU on demand. |
| **Backups & Restore** | Find private full-rice restore points and recover the last supported state, while respecting later personal changes when possible. |
| **What's Next** | Explore planned Windows styles and see what's actually still being built. |

### Supported desktop styles

| Family | Styles | Status |
| --- | --- | --- |
| macOS-inspired | Aurora Night, Aurora Day, Liquid Glass Night, Liquid Glass Day, Classic Aqua | **Available (preview)** |
| Windows 10-inspired | Classic productivity desktop | **Interactive preview only** |
| Windows 11-inspired | Centered taskbar and launcher | **Coming soon** |
| Windows 7-inspired | Aero Meadow, Aero Cascade | **Aero release candidate** |

The working macOS rice brings together [MacMenu](components/macmenu/), [Control Center](components/control-center/), [MacBar](components/macbar/), Plank, Thunar, WhiteSur-based GTK/window themes, icons and Aurora wallpapers. All three bundled apps keep their own tested installers. Plank remains a system package and your pinned dock items are preserved.

## Get started

Tested primarily with Linux Mint XFCE / X11. Other XFCE/X11 setups may work, but don't assume every theme or system service is installed.

```bash
sudo apt install python3-gi gir1.2-gtk-3.0
git clone https://github.com/CopyPasteUser/RiceHub.git
cd RiceHub
bash install.sh --dry-run
bash install.sh
ricehub
```

The previous `macos-xfce-rice` GitHub address redirects to RiceHub, so old bookmarks and install commands should continue to work. No `sudo` for `install.sh`. The installer does **not** apply a full rice, remove the XFCE panel, change your icons, or silently install missing themes. It installs user-local tools and keeps existing component settings.

If you want Plank and don't have it yet, install it separately using your distribution's package manager. The full macOS style also needs compatible WhiteSur, Bibata and Inter assets; the preflight check tells you what's missing.

**Already installed?** Update from any directory:

```bash
bash -c 'set -e; d="$(mktemp -d)"; git clone -q --depth 1 https://github.com/CopyPasteUser/RiceHub.git "$d/ricehub"; bash "$d/ricehub/install.sh"'
```

### Everyday commands

```bash
ricehub                       # Open the new desktop rice hub
macrice hub                   # Same application, legacy CLI
macrice status                # Check installed components and appearance
macrice rice plan night       # Inspect changes before applying anything
macrice rice apply night      # Apply Aurora Night with a recovery snapshot
macrice rice apply day        # Change to Aurora Day
macrice rice apply glass-day  # Try Liquid Glass Day
macrice rice plan aero-meadow  # Check the Windows 7-style Aero preset
macrice rice apply aero-meadow # Apply original Aero styling (with rollback snapshot)
macrice rice apply aero-cascade # Switch to the glassier Aero palette
macrice aero-shell             # Toggle the real Aero Start menu / taskbar
macrice aero-shell --quit      # Stop the Aero shell
macrice rice restore          # Restore the latest active rice snapshot
macrice performance report    # One-off memory / CPU sample
macrice gui                   # Original MacRice manager (still supported)
```

For your XFCE shortcuts, use `macmenu --toggle` and `macos-control-center-toggle`. The existing fast resident toggle behavior is unchanged.

## Safe by default

- **No surprise restyling.** Installing and opening RiceHub do not modify your desktop appearance. A full rice requires a successful preflight and your confirmation.
- **Recoverable changes.** Desktop snapshots live outside the replaceable app bundle, under `~/.local/share/macrice-state/`.
- **No takeover.** The XFCE panel is not replaced automatically. Plank launchers and layout are not overwritten during installation.
- **No extra background monitor.** The hub runs on demand. CPU/memory sampling happens only when you request it.
- **Honest previews.** Windows 7 has an experimental Apply button and an optional separate sample preview. Windows 10 offers a non-installable interactive prototype; Windows 11 is a placeholder. Some graphical effects depend on your existing X11 compositor.

## Where this is going

The first goal is a dependable macOS rice and a useful central manager. The Windows 7 Aero candidate shares the safe apply/restore engine and adds a user-configurable taskbar and optional SNI tray. Physical Mint XFCE testing and compatibility work remain before a stable Aero 1.0; Windows 10 has started as an interactive proof of concept and Windows 11 is planned. See the [RiceHub product roadmap](RICEHUB.md) and [MacRice engine roadmap](ROADMAP.md).

The existing MacMenu, Control Center and MacBar repositories have not been deleted. Their code stays independently testable while RiceHub becomes the main home for complete rices.

## Built in the open

RiceHub is MIT-licensed, community-friendly, and a little bit experimental. Issues, bug reports and real XFCE screenshots are welcome — see [Contributing](CONTRIBUTING.md) and [Security](SECURITY.md).

**Vibe-coded, human-directed and AI-assisted.** ChatGPT and OpenAI Codex helped with design and engineering; see [Contributors](CONTRIBUTORS.md) for credits and notes about original assets. This project is not affiliated with Apple or Microsoft and does not distribute their proprietary themes or logos.

*Inspired by familiar desktops. Built for Linux.*
