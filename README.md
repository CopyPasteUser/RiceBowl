# MacRice for XFCE

**Three small native apps. One calmer Linux desktop.**

I like macOS's sense of order, but I like XFCE's speed and freedom. MacRice brings those ideas together without replacing the window manager or burying a lightweight desktop under a web stack.

![MacBar and Control Center running together on X11](components/control-center/screenshots/desktop-integration.png)

*Actual GTK3 rendering on a clean virtual X11 display; system status indicators are limited there.*

The native GTK manager shows installed components, matching color presets and
your detected XFCE appearance in one small window.

## What's inside

| Component | Job |
| --- | --- |
| [MacMenu](components/macmenu/) · RC11 | Search, browse and launch installed apps. |
| [Control Center](components/control-center/) · 2.1.1 | Wi-Fi, audio, media, quick actions, settings and a fast D-Bus toggle. [Screenshot](components/control-center/screenshots/control-center-2.1.1.png) |
| [MacBar](components/macbar/) · 1.0.0 | A clean top bar with launchers, network, sound, battery and clock. [Screenshot](components/macbar/screenshots/macbar-1.0.0.png) |
| **MacRice Manager** · 0.1.0 | Installs the components, shows status, launches apps and applies matching themes. |

Every component remains a complete project with its own tests and installer. The existing repositories aren't deleted.

## Install safely

For **Linux Mint XFCE/X11** or a comparable GTK3 desktop:

```bash
sudo apt install python3-gi gir1.2-gtk-3.0
git clone https://github.com/CopyPasteUser/macos-xfce-rice.git
cd macos-xfce-rice
bash install.sh --dry-run
bash install.sh
```

Run the installer **as your normal user, not with sudo**. It delegates to the three tested user-local installers, preserves existing settings and uses their backups during upgrades. Control Center starts hidden for quick reopening; MacBar is installed but doesn't replace XFCE Panel.

If you have the old system-wide `xfce-macmenu` DEB, the installer stops and explains the conflict rather than silently removing a package.

To install from a terminal without starting GTK, run `bash install.sh --no-start`. To add MacBar to login while **keeping** XFCE Panel, use `bash install.sh --bar-autostart`. Only replace XFCE Panel after verifying your top-bar launchers and rollback path; the suite never does this automatically.

## Use it

```bash
macrice gui             # Native GTK settings manager
macrice status          # Check the three installed components
macrice inspect         # Safe, read-only XFCE appearance detection
macrice open menu       # Toggle MacMenu
macrice open center     # Toggle Control Center
macrice open bar        # Start MacBar
macrice theme Midnight  # Apply matching colors to the three apps
```

Other presets: **System**, **Light**, and **Graphite**. Only the apps' own theme settings change. XFCE's GTK theme, window decorations, icon pack, fonts, Plank setup, personal notes and favorites are left alone. Each theme action saves a private backup before writing any file.

For keyboard shortcuts in XFCE, use `macmenu --toggle` for MacMenu and `macos-control-center-toggle` for Control Center.

## Where files go

- App bundle and appearance backups: `~/.local/share/macrice/`
- Stable command and GUI launcher: `~/.local/bin/macrice`
- Each app's settings remain in its original `~/.config/` directory.
- The suite does not ask for root access or start a background network service.

The GTK manager runs only while open. The menu and Control Center may keep their existing hidden, resident windows for fast toggles. MacBar is a separate long-running GTK process.

## What still needs testing

Automated tests verify suite configuration, installer planning, user-local paths and component contracts. The components retain their own test suites. Real XFCE hardware behavior—multi-monitor positioning, Wi-Fi/Bluetooth indicators, Plank coexistence, suspend/resume and actual PSS memory—should be checked before replacing the old panel.

See [ROADMAP.md](ROADMAP.md) for the path to stable 1.0.

## Contributing and license

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md). MacRice is released under the [MIT License](LICENSE); component notices and licenses are retained in their folders.

*Inspired by macOS, built for Linux.*
