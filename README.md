<div align="center">

<img src="assets/ricebowl-symbolic.svg" alt="RiceBowl" width="88">

# RiceBowl

**Seven personalities. One Linux desktop.**

A collection of deeply customizable, OS-inspired desktop experiences — growing into a lightweight, modular desktop environment powered by **Wayland + labwc**.

[See the desktops](#seven-desktop-experiences) · [Install today](#try-ricebowl) · [Wayland roadmap](RICEBOWL_DE_ROADMAP.md) · [Screenshot gallery](screenshots/current/README.md)

</div>

<p align="center">
  <a href="screenshots/current/aero-start.webp"><img src="screenshots/current/aero-start.webp" width="48%" alt="Aero Seven desktop and Start menu"></a>
  <a href="screenshots/current/frutiger-start.webp"><img src="screenshots/current/frutiger-start.webp" width="48%" alt="Frutiger Aero launcher"></a>
  <a href="screenshots/current/winxp-start.webp"><img src="screenshots/current/winxp-start.webp" width="48%" alt="XP Luna taskbar and Start menu"></a>
  <a href="screenshots/current/windows10-start.webp"><img src="screenshots/current/windows10-start.webp" width="48%" alt="Windows 10-inspired Start menu"></a>
</p>

<p align="center"><sub>Real GTK/X11 project captures. <a href="screenshots/current/README.md">Explore the full gallery.</a></sub></p>

> **Status:** RiceBowl **0.9.x remains an XFCE/X11 development preview**. An optional, independently selectable [labwc/Wayland session preview](WAYLAND_SESSION.md) is now available for testing; it still uses a temporary Waybar shell. RicePlate and the complete standalone DE are not finished. Real-hardware acceptance is required.

The optional Wayland preview also supports two early data-driven panel layouts (`ricebowl de recipes`); the native RicePlate shell remains in development.
An isolated [native Rust layer-shell experiment](WAYLAND_SESSION.md#native-riceplate-layer-shell-experiment-developers-only) is available for developers; it does not yet replace the functional Waybar panel.

## Seven desktop experiences

- **Windows 98 / Classic:** compact menus, classic taskbar and Control Panel.
- **XP Luna:** cobalt taskbar, two-column Start and Luna-style settings.
- **Windows 7 Aero:** glass-inspired Superbar, Start menu and desktop controls.
- **Windows 10:** Start tiles, Task View, action center and native-style settings.
- **Frutiger Aero:** bright, organic dashboards and interactive controls.
- **ChromeOS:** launcher, shelf and quick settings.
- **macOS Aurora:** menu bar, dock integration and macOS-inspired controls.

Every rice has its own layout and identity, backed by real Linux status and actions. The artwork is original, not copied from other operating systems.

## Try RiceBowl

Currently for **Linux Mint XFCE or a compatible XFCE/X11 session**:

```bash
sudo apt install -y git python3-gi python3-cairo python3-gi-cairo gir1.2-gtk-3.0 gir1.2-wnck-3.0
git clone https://github.com/CopyPasteUser/Ricebowl.git "$HOME/RiceBowl"
cd "$HOME/RiceBowl"
bash install.sh --dry-run
bash install.sh
"$HOME/.local/bin/ricebowl"
```

Choose a rice in the Hub. Switching requires confirmation and saves recovery state; installation alone does not apply a theme.

- **Update:** use the Hub's update action or `ricebowl update`.
- **Check requirements:** `macrice doctor --style aero-meadow`.
- **Restore:** `macrice rice restore`.
- **Customize:** [Rice packs and profiles](RICEPACK_SPEC.md).

## From ricing suite to desktop environment

The long-term goal is a **desktop-creation framework**: recreate OS-inspired interfaces or turn AI-generated UI mockups into functioning rices using shared components and validated profiles, without building a new shell for each design. This authoring workflow is [planned, not shipped](RICEBOWL_DE_ROADMAP.md).

RiceBowl will keep the existing styles while replacing XFCE-specific desktop responsibilities incrementally:

1. **RiceSession + labwc:** an optional, independently selectable Wayland session.
2. **RicePlate:** panels, taskbars, desktop icons, wallpapers and launchers.
3. **RiceSpice + RicePop:** Linux settings, quick controls, notifications and OSD.
4. **RiceField + Taskotto:** independent, themeable file manager and task manager.
5. **Stability and efficiency:** cross-session compatibility, measured memory use, hardware testing and recovery.

The XFCE/X11 workflow remains available while the Wayland path matures. We reuse Linux services such as NetworkManager, PipeWire and UPower instead of duplicating them.

[Full DE development roadmap](RICEBOWL_DE_ROADMAP.md) · [Current XFCE resource boundaries](XFCE_RESOURCE_BOUNDARIES.md) · [Rice ecosystem](RICE_ECOSYSTEM_ROADMAP.md)

**Try the experimental session:** [setup, limitations and recovery](WAYLAND_SESSION.md). Installation is a separate, explicit choice; the normal RiceBowl installer does not modify your login sessions.

## Project links

[Releases](https://github.com/CopyPasteUser/Ricebowl/releases) · [Roadmap](ROADMAP.md) · [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [MIT License](LICENSE)

RiceBowl is not affiliated with Microsoft, Apple or Google. [RiceField](https://github.com/CopyPasteUser/Ricefield) remains a separate release candidate and does not replace Thunar automatically.
