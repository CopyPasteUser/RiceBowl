# Plank dock integration

MacRice includes an **adapter for Plank**, not a fork or vendored copy of the
dock. Plank is an independent GPL-3.0 project; install the system package with
your Linux distribution's package manager. See the [Plank upstream project](https://github.com/ricotz/plank).

On Linux Mint XFCE:

```bash
sudo apt install plank
```

MacRice discovers Plank automatically. Its manager offers **Start** and
**Settings**, which open the existing program and its native preferences.

```bash
macrice open dock       # Start the dock if it isn't already running
macrice dock preferences
macrice dock status     # Read default/effective dock1 preferences
```

The integration uses Plank's relocatable settings path:

```bash
gsettings get net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/dock1/ theme
gsettings get net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/dock1/ position
gsettings get net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/dock1/ icon-size
gsettings get net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/dock1/ hide-mode
```

**Installing the suite never changes pinned apps, dock items, themes, position,
icon size, autostart, XFCE Panel or system packages.** This is intentional:
MacRice should not take ownership of a dock just because the suite was
installed. The separate, explicitly confirmed *Complete Rice* action can set
Plank's appearance values, with a backup and restore; it never edits dock
launchers. If Plank is absent, the three bundled apps still install normally.

The MacRice adapter is vibe-coded with support from ChatGPT and OpenAI Codex;
Plank itself is an independent third-party project, not AI-authored by MacRice.
## Inverted Aurora colors

The complete Aurora presets use two small original Plank themes installed
**only after you explicitly apply a full Rice**:

- **Aurora Night** → `MacRice-Frost`, an off-white semi-opaque dock.
- **Aurora Day** → `MacRice-Obsidian`, a charcoal-black dock.

Both keep the existing bottom/centered 60px dock, intelligent hiding and
zoom. Existing pinned apps, launchers and autostart are untouched. The original
Plank theme setting is backed up and restored by `macrice rice restore`.
Generated theme definitions remain in `~/.local/share/plank/themes/` after
restoring, but are inactive and can be removed manually when not in use.
