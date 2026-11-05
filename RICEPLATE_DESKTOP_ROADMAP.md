# ricePlate — desktop ownership inside RiceBowl

> This document describes the **existing XFCE/X11 path** and its guarded
> preview. The separate **labwc/Wayland** RicePlate implementation is planned
> in [RICEBOWL_DE_ROADMAP.md](RICEBOWL_DE_ROADMAP.md); it does not silently
> replace the current XFDesktop session.

**Decision (5 November 2026):** ricePlate remains an internal RiceBowl
component. Building and maintaining a separate repository or permanently
resident desktop process is **not** justified by the current functionality.
XFWM4, XFConf/XSettings and XFCE session management are intentionally kept.
Changing that decision **within the existing X11 session** requires an actual
measured and tested benefit.

## Stage 1: safe desktop canvas preview (implemented)

- `macrice.riceware.plate` remains the single real Desktop inventory and
  rice-specific settings source. It never interprets `.desktop` `Exec` lines.
- `macrice riceware plate preview --style winxp` starts a normal, separately
  focusable GTK3 window. It uses the selected rice's bundled wallpaper and
  original icon theme where possible, and previews actual *current-user*
  Desktop files with a bounded 256-entry listing.
- The GTK canvas supports selection, keyboard activation, Enter, Shift+F10,
  context actions to open the selected item or Desktop directory, plus Refresh.
  Actual file opening is explicitly user-triggered through Gio's existing
  default application; symlinks are not launched by the preview.
- Per-rice appearance includes icon sizes (24–96 px), placement (left/right),
  show icons and show hidden files. A separate private config key is stored for
  each rice. Save is explicit and uses an atomic, mode-0600 user-local file;
  corrupt, unsupported or symlinked configs are never silently overwritten.
- The canvas reads Desktop asynchronously through the existing riceware worker,
  drops stale callbacks, has explicit empty/error/hidden states and creates no
  daemon, startup task or private file copy engine.
- When supported, a Gio directory monitor updates the preview after file
  creation, rename, deletion and writes, with a short debounced callback;
  unsupported mounts retain the Refresh button. The monitor and pending source
  are cancelled on window close. No periodic scans are used.
- Default placement: 98/XP/7/10/Frutiger left, macOS right, ChromeOS icons off.
  User overrides survive switching styles; **no XFDesktop setting is touched**.

### Test it

```bash
macrice riceware plate preview --style winxp
macrice riceware plate preview --style aero-meadow
macrice riceware plate preview --style winclassic
macrice riceware plate preview --style chromeos
macrice riceware plate preview --style night
```

The preview is not a replacement desktop; its normal window is deliberate.
The original `macrice riceware plate status|install|remove` behavior is preserved.

## Stage 2: close real desktop feature gaps (open)

- [ ] Compare per-rice native icon arrangements, launch behavior, selection,
  file rename/trash and desktop context menus with XFDesktop on Mint/X11.
- [x] Use live Gio directory change notifications rather than a periodic
  timer; keep asynchronous GTK reads and a manual fallback on unsupported mounts.
- [ ] Implement keyboard-accessible non-drag item repositioning and persistent
  monitor/workspace-aware geometry with bounds on 1024×768 and mixed DPI.
- [ ] Add actual desktop focus/selection semantics, contrast/high-contrast
  variants and verified native X11 hit-testing (not screenshot-only).
- [ ] Reuse riceExplorer's confirmed file move/copy/trash API when ready;
  do not maintain competing filesystem mutation behavior.
- [ ] Prove the user can recover manually from malformed desktop entries,
  files disappearing mid-open, symlink/hardlink traps and inaccessible mounts.

## Stage 3: optional desktop takeover (gated; NOT implemented)

- [ ] Measure settled XFDesktop and ricePlate PSS/CPU on owner hardware.
- [ ] Build an **opt-in** takeover plan with explicit readiness, backup and
  restoration of wallpaper/icon preferences and ownership. Never leave two
  desktop surfaces listening for pointer events or rendering the same icons.
- [ ] On crash or failed start, restore XFDesktop and original shortcuts.
- [ ] Verify full desktop hit testing, multi-monitor/rotation/hotplug,
  taskbar workareas, login/relogin, suspended sessions and window layering.
- [ ] Integrate the selected rice's desktop policy into normal switching only
  after owner sign-off; leave XFWM4/window decoration untouched.

**Gate:** no always-on ricePlate, no disabled XFDesktop autostart, no new
service, no separate repository and no claimed idle savings until those
physical tests succeed. This is a customizability-focused incremental
foundation, not an unverified Linux desktop replacement.
