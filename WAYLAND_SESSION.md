# RiceBowl (Wayland Preview) — first login-session track

**Experimental / opt-in.** This is an independently selectable labwc session
with a temporary native Waybar panel, not the finished RicePlate/RiceSpice/
RicePop desktop. The current XFCE/X11 rice suite and its backups stay intact.
Mint 22/Ubuntu 24.04's labwc **0.7.1** is supported by using its
`--startup` command and requesting compositor exit when the shell finishes.

## Prerequisites

- Linux display manager that enumerates `/usr/share/wayland-sessions`
  (check your specific login manager on the actual computer).
- User-local RiceBowl already installed with `bash install.sh`.
- `labwc`, `waybar`, `foot`, `fuzzel`, `swaylock`, a proper logind
  `XDG_RUNTIME_DIR` and D-Bus user session.
- `xdg-desktop-portal`, GTK and wlroots portal backends for file pickers
  and screencast; `xwayland` for legacy X11 clients.
- Optional: `swaybg` wallpaper, `swayidle` idle lock, `mako`
  notifications and an installed user polkit agent.

The package only installs the session chooser, a small forwarding wrapper,
RiceBowl-specific portal preferences and a namespaced systemd user target.
It **does not install RiceBowl itself**, overwrite `~/.config/labwc`, edit
global XFCE configuration or set the default session.

## Build and opt in (Debian/Ubuntu/Mint)

From the current RiceBowl checkout:

```bash
bash install.sh --dry-run
bash install.sh
ricebowl de check --json
sh scripts/build_wayland_session_deb.sh
```

Review the package before installing:

```bash
dpkg-deb --contents dist/ricebowl-wayland-session_0.1.0~preview1_all.deb
sudo apt install ./dist/ricebowl-wayland-session_0.1.0~preview1_all.deb
```

Log out. In the login manager's session selector, choose
**RiceBowl (Wayland Preview)**. Your existing XFCE session remains an
independent choice. If the entry is not shown, use the current XFCE session
and inspect the display manager's session-directory support before changing
system settings.

**Nothing in the ordinary `bash install.sh` enables this session.** Do not
install the preview package on a production-only machine without keeping a
working alternative login/session available.

### Nested developer test

From another desktop, `ricebowl de start --nested` explicitly launches a
separate compositor with activation-environment updates disabled, so it
doesn't hijack the current desktop's D-Bus/systemd Wayland variables.
The compositor still requires hardware/driver support for a nested backend.

### RicePlate layout recipes (first data-only contract)

The experimental Waybar adapter can render two structurally different,
declarative RicePlate panel layouts without starting a second panel or
modifying your live desktop configuration:

```bash
ricebowl de recipes
ricebowl de start --nested --recipe classic
ricebowl de start --nested --recipe chrome
```

Custom recipes use the strict JSON schema illustrated in
`macrice/de/resources/recipes/`. Supply an **absolute path** to an owner-only,
regular JSON file (`chmod 600 YOUR_FILE.json`). Recipes are limited to 64 KiB,
known panel widgets and six-digit colors. They cannot run commands, import CSS,
load assets or define new system actions. Temporary Waybar configurations are
created under the private `XDG_RUNTIME_DIR` and removed at session exit.

This demonstrates structural composition through a shared recipe contract;
it does **not** mean RicePlate's Rust layer-shell renderer, arbitrary mockup
conversion or all seven native profiles are implemented yet.

### Native RicePlate layer-shell experiment (developers only)

The repository additionally includes `components/riceplate-wayland`, an
event-driven Rust/Smithay Client Toolkit layer-shell prototype. It paints a
simple labelled surface with a fixed `Apps` button that launches the installed
Fuzzel command without passing any recipe data to a shell. When labwc offers
`wlr-foreign-toplevel-management`, the prototype also displays live window
titles and supports click-to-activate via the Wayland seat; clicking an active
task requests minimization. The window list
is deliberately bounded and only the visible entries accept clicks; if the
protocol is missing the panel keeps its launcher and reports the limitation.
It is **not** a replacement taskbar: it still lacks grouping, a calendar
popover, tray, notification handling or multi-output ownership. Do not start it automatically
alongside Waybar.

The native prototype understands two *bundled* schema-v1 RicePlate recipes:
`classic` (left-aligned bottom taskbar) and `chrome` (centered task list and
taller shelf). Both are parsed from the same recipe JSON files as the
temporary Waybar adapter, with strict schema/widget/color checks. It also
accepts owner-private absolute JSON recipe files (regular files, permissions
`0600`, no final symlinks, maximum 64 KiB). The three implemented widgets
(launcher, tasks and local-time clock) may be arranged in the start, center or
end section in any order, including custom top panels; their hit areas follow
the rendered geometry and shrink on narrow displays. The clock is updated
on minute boundaries through the Wayland event loop without a 1 Hz timer.
Other indicators and the tray still need functional Rust backends. The native
renderer deliberately omits unavailable widgets without displaying pretend
buttons. Custom recipes cannot contain commands or arbitrary executable code.

In a *disposable/nested* labwc session, developers with Rust 1.86+ can try:

```bash
cargo run --manifest-path components/riceplate-wayland/Cargo.toml -- --recipe chrome
```

To exercise RicePlate as the **only** panel within RiceBowl's isolated labwc
session, first install the experimental binary into your user-local PATH:

```bash
cargo install --path components/riceplate-wayland --locked
ricebowl de start --nested --panel native --recipe chrome
```

This is an explicit developer opt-in, **not** the login-manager default. The
temporary Waybar dependency remains installed and available for recovery: if
RicePlate crashes or cannot start after session preflight, the session logs
the problem and restores Waybar automatically. A deliberate clean panel exit
or an external session shutdown does not restart Waybar. If the native binary
is absent before startup, the CLI refuses the request without touching the
current desktop. The native panel deliberately omits system widgets not yet
implemented; use ordinary `ricebowl de start --nested` for a fuller preview.

To preview a private recipe without changing any desktop settings:

```bash
recipe_copy=$(mktemp --suffix=.json)
cp macrice/de/resources/recipes/classic.json "$recipe_copy"
chmod 600 "$recipe_copy"
cargo run --manifest-path components/riceplate-wayland/Cargo.toml -- --recipe "$recipe_copy"
rm -- "$recipe_copy"
```

The dedicated CI workflow compiles it and checks that both bundled recipes and
a private custom recipe remain alive on a real headless labwc compositor.
The Python session tests additionally verify native launch, crash fallback,
D-Bus restart argument preservation and intentional shutdown behavior.
Nothing changes the XFCE path, Waybar default or the optional session package.

## First-session controls

| Key | Action |
| --- | --- |
| Super + Return | Open Foot terminal |
| Super + Space | Open Fuzzel launcher |
| Super + L | Lock with Swaylock |
| Alt + F4 | Close the focused window (labwc default) |
| Desktop right-click | labwc root menu, including Exit |

Until RicePlate is native, Waybar provides the taskbar, clock, tray and
available system indicators. Only one panel is started. A terminated panel
requests a clean labwc exit instead of leaving the user on an empty desktop.
The temporary shell does not use XFCE's panel or XFDesktop.

## Session boundaries and recovery

- Labwc reads **only** the bundled `macrice/de/resources/labwc` configuration
  through `--config-dir`. The user's own labwc setup is left untouched.
- The session launcher rejects root execution, missing core dependencies,
  unsafe runtime-directory permissions and an accidental non-nested launch
  inside a desktop.
- labwc 0.7.1 needs an explicit D-Bus activation-environment import; the
  session's autostart performs it for primary sessions. Nested instances
  never import shared activation variables.
- The preview starts/stops its own `ricebowl-session.target`; it does not
  stop `graphical-session.target` used by other sessions.
- The temporary shell supervises its Waybar and optional helper processes.
  Its exit requests termination only of the labwc instance it belongs to.
- The login package can be uninstalled with
  `sudo apt remove ricebowl-wayland-session`. Your user-local RiceBowl
  installation, XFCE session and personal files remain.

If the Wayland session fails to start, the display manager should return to
its greeter. Select XFCE. If the greeter itself is unavailable, use a text
console (`Ctrl+Alt+F3`) to remove the optional session package, **not** the
XFCE desktop packages. Review the user's journal and display-manager logs.

## Physical acceptance checklist (not yet signed off)

- [ ] Login manager lists both RiceBowl Wayland and XFCE.
- [ ] Login, logout, repeated login and crash recovery work.
- [ ] Waybar taskbar, launchers, focus/Alt-Tab, multi-monitor and hotplug.
- [ ] Clipboard between native Wayland and XWayland apps.
- [ ] Flatpak/portal file picker, screenshot, OBS/PipeWire screencast.
- [ ] Polkit authentication (with and without an installed agent).
- [ ] Swaylock, idle lock, suspend/resume, lid and power-button behavior.
- [ ] Input layout/IME, touchpad/tablet, HiDPI scaling and accessibility.
- [ ] Systemd and D-Bus activation variables remain correct across logout
      and returning to XFCE.
- [ ] Real baseline PSS/RSS, idle CPU and login duration recorded on Mint.

These are genuine device acceptance gates; CI cannot replace them. If they
fail, the XFCE session stays the supported default.

[Main DE roadmap](RICEBOWL_DE_ROADMAP.md) · [Current XFCE boundaries](XFCE_RESOURCE_BOUNDARIES.md)
