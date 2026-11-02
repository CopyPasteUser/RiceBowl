# MacMenu for XFCE

**A little macOS inspiration, built for a desktop that is still Linux.**

I like XFCE for the same reasons a lot of people do: it's fast, familiar, and
doesn't get in the way. I just wanted an application menu that felt a bit more
at home next to a macOS-style top bar, dock, and Control Center.

That's how **MacMenu** started. It's a small, native GTK3 launcher with a
clean application grid, useful search, and a handful of carefully chosen
customization options. No browser engine, no giant desktop shell, and no
attempt to replace the parts of XFCE that already work well.

It's made with Linux Mint XFCE in mind, but it isn't tied to one laptop or
one wallpaper.

MacMenu has Midnight and Light appearances, both using the monochrome Linux
penguin icon. The compact launcher has no duplicate power or logout buttons.

## The idea

MacMenu does one job: **find and launch your apps**.

- **Everything in one place.** Browse installed applications by category, or
  switch to Favorites and Recent.
- **Search that gets out of your way.** Just start typing. MacMenu searches
  application names, descriptions, categories, and keywords.
- **A look that fits your desktop.** Choose Auto, Midnight, Light, Graphite,
  Ocean, or Violet. You can also adjust icon size and menu position.
- **A shortcut that actually toggles.** Press once to open, again to close,
  then again to reopen. The optional warm window makes repeat openings feel
  immediate.
- **Native app launching.** MacMenu uses GTK3 and GIO to discover and open
  your installed `.desktop` applications, including supported app actions.
- **A little Linux character.** The penguin logo is custom-made, monochrome,
  and designed to sit comfortably alongside a macOS-inspired desktop.

There is only **one layout**. I tried multiple menu modes along the way, but
they added settings and complexity without making the launcher more useful.

MacMenu also deliberately leaves **lock, logout, and power** controls to a
separate Control Center. They don't need to appear in two different places.
Your existing XFCE Whisker Menu is left untouched.

## Install

You'll need an XFCE desktop with GTK3, preferably running X11. MacMenu is
developed primarily for Linux Mint XFCE and uses system Python 3.10 or newer.

On Linux Mint or Ubuntu, install the GTK dependencies first:

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 librsvg2-common exo-utils
```

### Option 1: Install from the source repository

```bash
git clone https://github.com/CopyPasteUser/xfce-macmenu.git
cd xfce-macmenu
bash install.sh --dry-run
bash install.sh
```

This installs MacMenu **for your user account**, so don't run the installer
with `sudo`. The dry run shows what will change. When upgrading an older
MacMenu installation, the installer checks what it owns, backs it up, and
preserves your settings and favorites.

### Option 2: Download a ready-made package

The [latest release page](https://github.com/CopyPasteUser/xfce-macmenu/releases/tag/v1.0.0-rc11)
has two downloads:

- **ZIP:** Extract the folder and run `bash install.sh` inside it.
- **DEB:** On Linux Mint, Ubuntu, or Debian, install it with:

  ```bash
  sudo apt install ./MacMenu-XFCE_1.0.0-rc11_all.deb
  ```

Use **either** the user installer **or** the Debian package, not both at
the same time. If you already have an old `xfce-macmenu` system package,
the user installer will explain the conflict before changing anything.

## Make it your app menu

After installing, open **XFCE Settings → Keyboard → Application Shortcuts**
and assign this command to a free key combination:

```bash
macmenu --toggle
```

`Super+Space` is a good starting point. You can also use the Super key
alone if XFCE or another menu isn't already using it.

The behavior is simple: **open → close → open → close**. It's the same
command every time; you don't need separate show and hide shortcuts.

Prefer clicking? Add the **MacMenu** application launcher to your XFCE panel
or, later, your macOS-style top bar.

### Handy controls

| Action | Shortcut |
| --- | --- |
| Search | Just type |
| Launch the first match | `Enter` |
| Close the menu | `Esc` or press your toggle shortcut again |
| Favorites / Recent / All Apps | `Alt+1` / `Alt+2` / `Alt+3` |
| Refresh installed apps | `Ctrl+R` |
| Open preferences | `Ctrl+,` |
| App actions and favorites | Right-click an app |

Other useful commands: `macmenu --show`, `macmenu --hide`,
`macmenu --preferences`, `macmenu --quit`, and `macmenu --version`.

## Fast, but with an honest trade-off

MacMenu tries to feel responsive without wasting resources. It reuses GTK
widgets, loads larger app lists in batches, and lets the installed launcher
communicate directly with an already-running instance over GLib/D-Bus.
There is no constant background polling or network service.

**Instant reopening** is enabled by default. It keeps a hidden window ready,
which is great for a keyboard-driven launcher but does use some RAM. Turn it
off in **Preferences → Appearance** if you prefer lower background memory
usage over the fastest repeat openings.

Recent apps and preferences are stored locally under `~/.config/macmenu/`.
There is no telemetry, cloud account, or search-query logging.

## Where the project stands

The current version is **1.0.0 RC11**. It's usable and has automated tests,
but I'm not calling it a stable 1.0 yet. Multi-monitor placement, HiDPI,
accessibility, and behavior across different XFCE setups still deserve more
real-world testing. GTK3 also can't promise the exact translucent blur you
see in macOS, so the design favors readable, opaque surfaces.

The [roadmap](ROADMAP.md) covers the remaining 1.0 work and ideas for later
versions. For a deeper look at the visual choices, see
[Design Decisions](DESIGN_DECISIONS.md).

## Want to help?

Issues, suggestions, and pull requests are welcome — especially reports from
XFCE installations other than Linux Mint. If something breaks, please include
your Linux distribution, XFCE version, whether you're using X11 or Wayland,
and the steps needed to reproduce it. A screenshot helps with layout issues.

To run the Python checks locally:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q macmenu tests capture_screenshot.py scripts/install_user.py
```

There are also native GTK smoke and toggle tests in `tests/`, which need an
active graphical session. No special backend or online account is required
to develop the launcher.

## License

The MacMenu source included in the MacRice suite is distributed under the
suite's [MIT License](../../LICENSE). Its separate standalone repository may
maintain its own licensing and release history.

## Credits

**Vibe-coded, human-directed and AI-assisted.** CopyPasteUser is the creator
and maintainer. ChatGPT and OpenAI Codex supported implementation, UX work,
testing and documentation. See [MacRice contributors](../../CONTRIBUTORS.md).

---

*Made for people who like a polished desktop, but still want to keep the
lightness and freedom of XFCE.*
