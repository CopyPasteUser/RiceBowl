# Windows 10-inspired XFCE rice — 0.5 RC2

This is a native, **installable and reversible XFCE/X11 rice**, not merely a GTK mockup. Both palettes use original RiceBowl artwork, including a crisp blue-and-white Linux penguin as the Start icon instead of a Windows mark; no Microsoft binaries, icons or wallpapers are bundled. The early non-installing concept dialog is retained separately as a design reference.

## Release roadmap and acceptance

The implementation phases have been completed in the repository. **The last physical-hardware gate cannot be checked from CI or virtual X11** and is deliberately left open; until then this is RC2 rather than a stable 1.0.

| Phase | Status | Delivered / acceptance evidence |
| --- | --- | --- |
| 1 · Live shell | **Done** | Dark left-aligned GTK taskbar, keyboard-friendly searchable Start, real Gio app catalog, app launching, persistent pinned apps and tiles, two-line clock, Show Desktop; optional Wnck task switcher and StatusNotifier tray use event signals. |
| 2 · Look and feel | **Done** | Independent dark/light GTK3 and XFWM4 themes, original PNG window controls, flat Linux-penguin Start SVG and icon theme, two high-resolution blue wallpapers, Thunar palette and flat Plank theme. All artwork bundled, no runtime Pillow dependency. |
| 3 · Installation / recovery | **Done** | Preflight checks, no-write plan, user-local theme staging, named autostart, transaction backup schema 4, rollback on apply failure, preservation of customized settings, and switching Aero ↔ Ten ↔ other styles. Schema 1–3 restore compatibility retained. |
| 4 · Product workflow | **Done** | RiceBowl Discover selection, **Check requirements / Apply rice / Restore**, `macrice rice plan/apply/restore`, separate `macrice windows10-shell` command, safe autostart and optional read-only concept preview. |
| 5 · Automated validation and screenshots | **Done** | Unit tests for assets, safety, setup/restore, cross-rice switches, GTK/X11 startup and interaction; CI Xvfb smoke, native screenshots and updated docs. |
| 6 · Real Mint/XFCE acceptance | **Pending owner hardware** | Fresh install and rollback on the actual Linux Mint XFCE/X11 machine; Wnck, SNI tray and native notifications with real apps; multi-monitor, HiDPI, focus, suspend/resume, session autostart, idle CPU/PSS and panel placement. |

### What is real

- Start reads `Gio.AppInfo.get_all()`, excludes hidden entries, searches installed applications and invokes their launchers. Right-click a result to pin/unpin it; taskbar buttons and Start tiles share one persistent Windows 10-specific pin file. No fabricated application names are used in the live shell.
- Wnck3 (if available) supplies real window buttons, activate/minimize, overflow and Show Desktop via signals rather than a polling loop.
- The optional StatusNotifierItem tray integrates supported SNI hosts. Legacy XEmbed icons are outside the current scope.
- Action Center contains real shortcuts to the installed XFCE settings manager, display configuration, `pavucontrol` and NetworkManager connection editor. Missing utilities are visibly disabled. Notification history stays with XFCE's notification daemon; it is **not** a second notification store. Quick buttons do **not** silently toggle radios or audio policy.
- Two original GTK3 / XFWM4 themes and wallpaper choices are installed into XDG user data directories. Existing third-party themes are neither overwritten nor deleted.
- The RC2 penguin icon theme is named `RiceHub-Ten-Penguin` so upgrades never overwrite potentially customized RC1 `RiceHub-Ten` assets; the managed autostart filename and command remain unchanged.
- The existing XFCE Panel is left running and untouched. You can adjust/hide it in XFCE Panel Preferences after inspecting the new taskbar. RiceBowl will not forcibly kill it or rewrite your panel settings.

## Actual running GTK / X11 screenshots

![RiceHub Windows 10 style selection and Apply button](screenshots/ricehub-windows10-gallery-0.5.0rc2.png)

| Start menu and installed applications | Action Center and quick settings |
| --- | --- |
| ![RiceHub Ten penguin Start in X11 with real Gio application catalog, pinned tiles and original wallpaper](screenshots/windows10-live-start-0.5.0rc2.png) | ![RiceHub Ten real GTK Action Center with penguin taskbar over original wallpaper](screenshots/windows10-live-actions-0.5.0rc2.png) |

Captured by `screenshots/capture_ten_shell.py` and `screenshots/capture_windows10_hub.py` against a disposable 1600×900 X11 display. The shell windows are **running GTK widgets**; the original wallpaper is a test fixture in the virtual desktop. These are not photographs of a complete physical Linux Mint installation. Some XFCE features (real notifications, system tray icons, session manager and Wnck windows) are not present in the isolated capture.

## Installation and use

Target: Linux Mint XFCE or another desktop with XFCE **on X11**. Debian/Ubuntu example:

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-wnck-3.0 plank
git clone https://github.com/CopyPasteUser/RiceBowl.git
cd RiceBowl
bash install.sh --dry-run
bash install.sh
macrice rice plan ten-dark   # Read-only checks before any desktop changes
macrice rice apply ten-dark  # Or ten-light; writes a private rollback snapshot
macrice rice restore         # Return to the previous desktop layer
```

`gir1.2-wnck-3.0` is optional for the shell but required for live window buttons. Network/sound quick settings rely on the existing `nm-connection-editor` and `pavucontrol` programs. The basic GTK shell runs without these extras. The shared full-rice engine also reads Plank's GSettings schema and the appropriate XFCE channels; preflight will reject missing prerequisites rather than partially apply a theme. The installer itself never applies a style.

After installation, `ricebowl` opens the style picker. `macrice windows10-shell` opens the shell manually; `macrice windows10-shell --quit` stops it, without terminating the XFCE panel. The managed autostart is activated only while a Windows 10 preset is selected. `macrice rice restore` restores the latest active snapshot. Restore is layered: if you applied Windows 7, then Windows 10, restore once to return to Windows 7 and a second time to return to your initial desktop.

### Session and layout options

```bash
RICEHUB_TEN_TRAY=0 macrice windows10-shell      # Disable the optional SNI tray
RICEHUB_TEN_RESERVE=0 macrice windows10-shell   # Do not request X11 bottom workarea
```

These environment options apply to the shell process; for a login-time override, configure the user session environment. The bar is designed for a 53px bottom strip. Existing panels/docks may need manual positioning. Do not apply this rice inside a Wayland session and expect X11 window management to work.

## Verification and known limitations

```bash
/usr/bin/python3 -m unittest discover -s tests -v
/usr/bin/python3 -m compileall -q macrice launcher.py
# On a machine with xvfb-run and dbus-run-session:
dbus-run-session -- xvfb-run -a /usr/bin/python3 -c 'from macrice.ten_shell import run; raise SystemExit(run(["ricehub-ten-shell", "--smoke-test"]))'
dbus-run-session -- xvfb-run -a -s '-screen 0 1600x900x24' /usr/bin/python3 screenshots/capture_ten_shell.py
```

The screenshots show the completed shell, but do not prove Mint hardware integration. Further acceptance must exercise the desktop session and recovery before declaring 1.0. Known boundaries: X11/XFCE only; compositor blur intentionally absent; native notification history still belongs to XFCE; legacy XEmbed tray icons unavailable; all shortcut services depend on installed desktop utilities. No network daemon, copied proprietary assets, root permissions or automatic panel replacement are required.
