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

**No changes are made to pinned apps, dock items, themes, position, icon size,
autostart, XFCE Panel or system packages.** This is intentional: MacRice should
not take ownership of an existing dock just because the suite was installed.
If Plank is absent, the other three applications still install normally.
