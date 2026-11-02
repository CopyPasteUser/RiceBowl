# MacRice for XFCE

**A complete macOS-inspired XFCE desktop, built from small native parts.**

I like macOS's sense of order, but I like XFCE's speed and freedom. MacRice brings those ideas together without replacing the window manager or burying a lightweight desktop under a web stack.

![MacBar and Control Center running together on X11](components/control-center/screenshots/desktop-integration.png)

*Actual GTK3 rendering on a clean virtual X11 display; system status indicators are limited there.*

The native GTK manager shows the installed components, your Plank dock, matching
app-only color presets and your detected XFCE appearance in one small window.

![Aurora Night — an original wallpaper included with MacRice](assets/wallpapers/aurora-night.jpg)

*Aurora Night, one of two original wallpapers. Both are included, with an
illustrative full-desktop preview in the manager.*

![Illustrative complete desktop preview with MacBar, MacMenu, Control Center and Plank](screenshots/full-rice-overview-0.2.0rc2.png)

*Illustrative layout rendering. The interactive preview in the application is native GTK; this image is not a live desktop capture.*

## What's inside

| Component | Job |
| --- | --- |
| [MacMenu](components/macmenu/) · RC11 | Search, browse and launch installed apps. |
| [Control Center](components/control-center/) · 2.1.1 | Wi-Fi, audio, media, quick actions, settings and a fast D-Bus toggle. [Screenshot](components/control-center/screenshots/control-center-2.1.1.png) |
| [MacBar](components/macbar/) · 1.1.0 | A clean, instantly restylable top bar with launchers, network, sound, battery and clock. [Screenshot](components/macbar/screenshots/macbar-1.0.0.png) |
| [Plank](components/plank/) · system package | The existing bottom dock. Detect its settings, start it and open its native preferences without overwriting pins or layout. |
| **MacRice Manager** · 0.2.0 RC3 | Installs the bundled apps, previews the full Rice, switches Aurora Day/Night and safely restores desktop settings even after individual preferences change. |

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

Run the installer **as your normal user, not with sudo**. It delegates to the three tested user-local installers, preserves existing settings and uses their backups during upgrades. Control Center starts hidden for quick reopening; MacBar is installed but doesn't replace XFCE Panel. Plank stays independently managed by your distribution; to add it on a system where it's missing, run `sudo apt install plank` separately.

If you have the old system-wide `xfce-macmenu` DEB, the installer stops and explains the conflict rather than silently removing a package.

To install from a terminal without starting GTK, run `bash install.sh --no-start`. To add MacBar to login while **keeping** XFCE Panel, use `bash install.sh --bar-autostart`. Only replace XFCE Panel after verifying your top-bar launchers and rollback path; the suite never does this automatically.

## Use it

```bash
macrice gui             # Native GTK settings manager
macrice status          # Check all four components, including Plank
macrice inspect         # Safe, read-only XFCE appearance detection
macrice open menu       # Toggle MacMenu
macrice open center     # Toggle Control Center
macrice open bar        # Start MacBar
macrice open dock       # Start Plank if it is not running
macrice dock status     # Read Plank dock settings
macrice dock preferences # Open Plank's native settings
macrice theme Midnight  # Apply matching colors to the three apps
macrice preview         # See the complete desktop before changing anything
macrice rice plan night # Check all themes, fonts, monitor keys (read-only)
macrice rice apply night # Style GTK, XFWM, Thunar, MacBar, Plank and wallpaper with backup
macrice rice apply day  # Switch back to Aurora Day at any time
macrice rice restore    # Restore the most recent saved desktop appearance
```

**Stuck on Aurora Day?** Run `macrice rice plan night` to check requirements,
then `macrice rice apply night` to switch directly. You do not need to restore
first. In RC3, `macrice rice restore` restores settings that MacRice still owns
and reports any preferences you changed afterward instead of blocking the
whole desktop. The new Plank Glass themes are slightly translucent and leave
earlier MacRice dock themes untouched.

To update from **any working directory**, run:

```bash
bash -c 'set -e; d="$(mktemp -d)"; git clone -q --depth 1 https://github.com/CopyPasteUser/macos-xfce-rice.git "$d/macrice"; bash "$d/macrice/install.sh"'
```

Other presets: **System**, **Light**, and **Graphite**. Only the three bundled apps' theme settings change. XFCE's GTK theme, window decorations, icon pack, fonts, Plank setup, personal notes and favorites are left alone. Each theme action saves a private backup before writing any file.

On a WhiteSur-Dark / WhiteSur-light / Bibata / Inter setup, the **System** preset follows the dark GTK appearance. MacRice reads the current dock's effective theme, position, icon size and hide mode through Plank's dock1 GSettings path; it does not guess them from unset dconf overrides.

For a **complete desktop Rice**, including GTK, right-side window decorations,
Thunar, icons, cursor, Inter fonts, inverted MacBar/Plank colors and one of two wallpapers, see
the [full Rice guide](RICE.md). Full Rice is never applied during installation.
The installer leaves your existing XFCE desktop unchanged until you confirm
the change in the preview window or call `macrice rice apply` explicitly.

For keyboard shortcuts in XFCE, use `macmenu --toggle` for MacMenu and `macos-control-center-toggle` for Control Center.

## Where files go

- Replaceable app bundle: `~/.local/share/macrice/`
- Persistent desktop backups and wallpapers: `~/.local/share/macrice-state/`
- Stable command and GUI launcher: `~/.local/bin/macrice`
- Each app's settings remain in its original `~/.config/` directory.
- The suite does not ask for root access or start a background network service.

The GTK manager runs only while open. The menu and Control Center may keep their existing hidden, resident windows for fast toggles. MacBar and the existing Plank dock are separate long-running GTK processes.

## What still needs testing

Automated tests verify suite configuration, installer planning, user-local paths and component contracts. The components retain their own test suites. Real XFCE hardware behavior—multi-monitor positioning, Wi-Fi/Bluetooth indicators, Plank coexistence, suspend/resume and actual PSS memory—should be checked before replacing the old panel.

See [ROADMAP.md](ROADMAP.md) for the path to stable 1.0.

## Contributing and license

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md). MacRice is released under the [MIT License](LICENSE); component notices and licenses are retained in their folders.

**Vibe-coded, human-directed, AI-assisted.** Project design and development
used ChatGPT and OpenAI Codex. See [CONTRIBUTORS.md](CONTRIBUTORS.md) for honest
credits, the original wallpaper creation notes and third-party acknowledgments.

*Inspired by macOS, built for Linux.*
