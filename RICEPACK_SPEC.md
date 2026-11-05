# Rice packs · presets v1 and visual assets v2

RiceBowl supports both **v1 named presets** and **v2 visual packs** built on
one of its existing, transactionally tested XFCE rices. Neither format is an
executable plugin: no scripts, extra services or network downloads run.

## Visual pack v2 · create, inspect and import

Create a directory containing `manifest.json` and only the assets you use:

```text
my-rice/
  manifest.json
  wallpaper/background.png
  gtk/gtk-3.0/gtk.css
  xfwm/xfwm4/themerc
  xfwm/xfwm4/close-active.png
  icons/index.theme
  icons/16x16/apps/example.png
```

Example `manifest.json` (leave the `files` field out; the builder writes all
file hashes automatically):

```json
{
  "schema_version": 2,
  "id": "my-seaside",
  "name": "My Seaside",
  "base_style": "aero-meadow",
  "description": "A custom Aero colorway",
  "license": {
    "spdx": "CC0-1.0",
    "author": "Your name",
    "source": "My original artwork"
  },
  "assets": {
    "wallpaper": "wallpaper/background.png",
    "gtk": true,
    "xfwm": true,
    "icons": true
  }
}
```

Every declared asset is optional, but at least one is required. If you only
want a custom wallpaper, remove `gtk`, `xfwm` and `icons` plus their files.
For custom GTK/WM/icon themes, the minimum files are respectively
`gtk/gtk-3.0/gtk.css`, `xfwm/xfwm4/themerc` and `icons/index.theme`.
Icons can inherit `Adwaita` through `index.theme`; use PNG/JPEG for artwork.

```bash
macrice riceware packs build --directory my-rice --output my-seaside.zip
macrice riceware packs inspect --archive my-seaside.zip
# Review license, authorship and source before acknowledging their terms:
macrice riceware packs import --archive my-seaside.zip --accept-license
macrice riceware packs check my-seaside
# Changes the live desktop, with the normal Rice backup and rollback:
macrice riceware packs apply my-seaside --yes
# First restore/switch away, then remove an inactive pack:
macrice rice restore
macrice riceware packs remove my-seaside --yes
```

The Hub's Appearance picker also lists imported visual packs next to their
base style, previews their imported wallpaper (when present), checks the
actual assets and uses its normal confirmation/rollback flow. Installing
is never the same as activating; use `macrice rice restore` to undo a rice.

**Security boundaries.** v2 accepts local ZIP files only: no unpacking
arbitrary paths, symlinks, executable scripts, SVG/XML, or CSS network/file
resource references. The builder refuses to overwrite an archive. Import is
limited to 32 MiB ZIP / 48 MiB extracted, 128 files, 12 MiB per file and a
64 KiB manifest. File SHA-256 checksums, user ownership and permissions are
verified again before applying. Theme and icon names are dedicated to each
pack revision; existing names are never overwritten. Partial imports are
cleaned up. Removal refuses an active theme or referenced pending restore;
accepted removals move original assets and metadata to private recovery
storage under `$XDG_DATA_HOME/ricebowl/removed/` (not a permanent erase).

The license information is a **user declaration**, not cryptographic
signature verification or legal proof of rights. Only import art and themes
you have permission to use. GTK/CSS and image decoders still process those
files, so import assets from sources you trust. Independent renderer code,
remote marketplace installs and automatic executable plugins remain out of
scope for v2.

## Named preset v1 (no custom files)

## Discover and check

```bash
macrice riceware packs list
macrice riceware packs show winxp
macrice riceware packs check winxp
macrice riceware packs template winxp
```

`list`, `show`, `check` and `template` are read-only. `check` reports essential
XFCE/X11 binaries and optional integrations such as riceExplorer; a missing
optional component never blocks the selected rice. For a **full asset/settings
preflight**, use `macrice doctor --style winxp` or `macrice rice plan winxp`.

## Install a named preset

Save a small JSON file as
`$XDG_DATA_HOME/ricebowl/packs/my-luna.json` (normally
`~/.local/share/ricebowl/packs/my-luna.json`):

```json
{
  "schema_version": 1,
  "id": "my-luna",
  "name": "My Luna",
  "base_style": "winxp",
  "description": "XP-inspired desktop for my laptop"
}
```

The directory and file are **created by you**, not by the discovery command.
`id` must be unique (including against built-in styles), use lowercase ASCII
letters/numbers/hyphens, and match the filename. No unknown properties are
allowed. A pack can only choose a supported `base_style`; its name and
description are metadata, not executable code or appearance overrides.

RiceBowl scans that directory only when requested, without a watcher or idle
poller. Symlinks, oversized files, non-user-owned files, group/world-writable
files, unknown keys and invalid base styles are rejected. Bad files remain
untouched; diagnostics do not print their contents or absolute paths.
Valid user presets also appear next to their base style in the Hub's existing
**Appearance** dropdown when you select that rice family. The Hub uses the
same Check → confirmation → Apply → Restore flow as built-in styles.

```bash
macrice riceware packs list
macrice riceware packs show my-luna
macrice riceware packs check my-luna
# The following intentionally changes the current desktop:
macrice riceware packs apply my-luna --yes
```

Applying a preset uses the **existing** RiceBowl rice transaction: preflight,
private backup, rollback on failure, and a session/taskbar handoff. It is not
automatic just because the JSON exists. Return with `macrice rice restore`.

## Profile and component ownership

- The canonical `STYLES` registry remains the authority for GTK, XFWM, icon
  and wallpaper assets. `PROFILE_FAMILIES` identifies the seven renderer
  families. A pack references them, so copies cannot drift independently.
- Session reconciliation resolves the current GTK theme through the same
  style-to-family mapping as the pack manifest. Multiple built-in variants
  that share a GTK theme must use the same shell family; unknown or ambiguous
  themes return to the normal XFCE panel recovery path.
- XFWM4, XFCE power/notification services, desktop and session management
  stay in place. riceExplorer remains an optional external integration until
  its separate release/acceptance gate is passed.
- Discovery and capability checks spawn no permanent process and change no
  user settings. They are *not* proof that Wi-Fi, HDMI, Bluetooth, suspend or
  idle memory behavior passed physical Mint XFCE acceptance.

### Future expansion gate

Adding new renderer code, CSS resource imports, SVG icon sanitization and
verified pack publishers will require separate review. Neither v1 nor v2
accepts arbitrary commands from a manifest.
