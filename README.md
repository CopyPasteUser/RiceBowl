<div align="center">

<img src="assets/ricebowl-symbolic.svg" alt="RiceBowl" width="80">

# RiceBowl

**Build a desktop, not just a theme.**

A lightweight, modular Linux desktop project for recreating classic OS experiences and building original **AI-assisted rices** from reusable components.

[Desktop gallery](screenshots/current/README.md) · [Wayland roadmap](RICEBOWL_DE_ROADMAP.md) · [Get started](#try-it)

</div>

![RiceBowl XP Luna desktop](screenshots/current/winxp-start.webp)

## What is RiceBowl?

Today, RiceBowl is a **seven-style XFCE/X11 ricing suite**: Windows 98, XP Luna, Windows 7, Windows 10, Frutiger Aero, ChromeOS and macOS-inspired experiences. Each has its own menus, panels and controls, using original artwork and real Linux integrations.

It is also becoming an independent, floating **Wayland desktop environment based on labwc**. Its long-term goal is a *desktop construction kit*: give an AI a reference screenshot or an original mockup, and use validated layout recipes and shared functional components to build a usable rice—without writing a new desktop shell for each design.

The optional Wayland preview has declarative nested panels, a genuine labwc root menu, wallpapers, visual tokens, compact layouts and safe offline recipe editing. Its experimental native Rust RicePlate shell supports **clickable desktop icons** through schema-v5 recipes, with multi-resolution screenshot diagnostics for creators. Movable icons, desktop widgets, automated mockup conversion and the 1.0 release are still in development. The established XFCE session remains available.

## Try it

On Linux Mint XFCE or a compatible XFCE/X11 session:

```bash
sudo apt install -y git python3-gi python3-cairo python3-gi-cairo gir1.2-gtk-3.0 gir1.2-wnck-3.0
git clone https://github.com/CopyPasteUser/Ricebowl.git "$HOME/RiceBowl"
cd "$HOME/RiceBowl"
bash install.sh --dry-run
bash install.sh
"$HOME/.local/bin/ricebowl"
```

Select a rice in the Hub; installation alone does not change your desktop. Use `ricebowl update` to check for updates or `macrice rice restore` to undo a rice switch.

## Explore

- [Wayland preview, installation and safety](WAYLAND_SESSION.md)
- [AI-friendly shell recipes and components](WAYLAND_SESSION.md#schema-v5-native-desktop-icons-preview)
- [Desktop environment development roadmap](RICEBOWL_DE_ROADMAP.md)
- [Rice ecosystem (RiceField, Taskotto and more)](RICE_ECOSYSTEM_ROADMAP.md)
- [Contributing](CONTRIBUTING.md) · [License](LICENSE) · [Releases](https://github.com/CopyPasteUser/Ricebowl/releases)

RiceBowl is independent of Microsoft, Apple and Google; no proprietary operating-system artwork is included. Real-hardware acceptance is required before a stable release.
