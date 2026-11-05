# Rice packs · data-only preset format v1

RiceBowl supports **named, plug-in presets** that reuse one of its existing,
transactionally tested XFCE rices. They are intentionally **not executable
plugins**: a downloaded JSON file cannot start a process, add a command,
install a theme or replace system services. New wallpapers, third-party
renderers and asset bundles need a separate, reviewed import mechanism.

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

To support genuinely custom visual packs, next define bounded asset import,
copyright/licensing checks, file integrity, trust model, collision policy,
transactional installation and full removal/rollback. Do not reinterpret
arbitrary JSON paths as shell commands or run third-party scripts.
