# RiceBowl native windows and drag-and-drop — cross-rice contract

**Status: active 1.0 workstream (5 November 2026).** This applies to every
non-macOS rice. **macOS Aurora stays unchanged**, as requested.

## Product rule

Settings, file management, device configuration and other long-lived tasks
must behave like applications integrated into the actual Linux desktop:

1. **Own windows:** individual, independently focusable and resizable XFWM4
   clients, visible in task switcher and taskbar. Custom rice titlebars may
   preserve their historical look, but must support mouse dragging, keyboard
   focus, accessibility names and window-manager shortcuts. Do not confuse
   full-screen-look popovers with real application windows.
2. **Real drag-and-drop:** file/URI drops go to appropriate file/desktop
   surfaces through the GTK/GIO drag targets or, later, riceExplorer's own
   explicit file-operation contract. Never interpret a dropped file as an
   executable installer, trusted config or command. No opaque drop targets on
   settings windows; only specific documented actions such as a wallpaper
   preview may accept supported file types and must confirm changes.
3. **Real system behavior:** Linux APIs own actions, e.g. NetworkManager,
   BlueZ, PipeWire, UPower, Gio/UDisks2, xfconf and RandR/XFWM4. Distinct rice
   renderers use one tested backend; no fake toggles or competing services.
4. **Lifecycle:** an ordinary settings window remains visible after another
   app takes focus, preserves its user-chosen position when reopened, does not
   always float above other apps, and closes without leaving input grabs or
   leaked asynchronous workers. Popovers and menus deliberately *do* close on
   focus changes.
5. **Recovery:** desktop/session changes preserve all user windows where
   feasible, with safe owner-scoped cleanup on rice switch. Monitor changes
   and external-drive operations require explicit confirmation and rollback.

## Status by rice

| Rice | Independent settings/window foundation | Remaining integration |
| --- | --- | --- |
| XP Luna | Draggable WM Control Panel and persisted geometry; local regular-file copies to existing folder shortcuts | Deeper native task pages, full folder moves and physical DnD testing |
| Windows 98 SE | WM Control Panel with persisted geometry; Desktop inspector exports URI drags and confirms copies to Desktop | Richer system applets and complete desktop/file manager DnD |
| Windows 7 Aero | WM Control Panel, persisted geometry and local file-copy targets on Places | Native task dialogs, deeper per-app windows and full folder DnD |
| Windows 10 | WM-integrated native Settings shell, draggable caption and persisted geometry | Deep app pages and complete folder/file DnD |
| ChromeOS | Normal GTK Settings app with persisted, bounded geometry | ChromeOS file/desktop targets and window-fidelity work |
| Frutiger Aero | Draggable/persisted Aqua Control Center, bounded file-copy Places, opt-in timed RandR trial | Independent guard hardware proof, richer pages and full file DnD |
| macOS Aurora | **Frozen — preserved** | No changes in this workstream |

## Implementation sequence

- [x] Shared `macrice.rice_windows` normal-window and themed-caption helpers,
  with fast, isolated unit tests.
- [x] Remove transient/always-on-top/auto-hide behavior from the Frutiger and
  Luna settings windows. Keep Aqua's hand-placed location and size after the
  first opening; Windows 10 Settings also preserves user placement.
- [x] Extend Aqua's native Bluetooth detail page with bounded on-demand
  discovery and verified pairing via the current BlueZ **system default** agent.
- [x] Add a visible RiceBowl sidebar update button backed by the existing
  pinned, confirmed and recoverable updater; no automatic installation.
- [x] [PR #67](https://github.com/CopyPasteUser/RiceBowl/pull/67) passed
  native GTK/X11 CI for these window changes and existing screenshot regressions.
- [x] Per-role XDG user window geometry saved atomically and clamped to
  a reachable display after unplug/reconfiguration; no new resident service.
- [x] Shared limited URI targets for XP/Win7/Aqua folder shortcuts and the
  Win98 Desktop inspector: confirmed regular-file copies, no overwrites,
  background transfer, per-operation undo of *unchanged* copied files.
- [x] Aqua single-active-monitor mode/position trial implementation with a
  detached per-session guard and automatic 18-second unconfirmed rollback.
- [ ] Verify the new DnD bindings, guard and geometry lifecycle on native GTK
  CI and physical multi-monitor XFCE/X11, including display-server failure.
- [ ] Validate focus switching, move, resize, maximize, taskbar, Escape,
  1024×768 and multi-monitor unplug using real XFWM4 on Linux Mint.
- [ ] Full folder/move/cross-volume DnD, clipboard integration and themed
  riceExplorer renderers **wait until riceExplorer 1.0**. XFDesktop/Thunar own
  those workflows in the meantime; do not duplicate their file manager UI.
- [ ] Build the local BlueZ PIN/confirm agent with strict request expiry,
  no passkey logging, explicit trust policy and physical device tests.
- [ ] Hardware-validate the guard across resolution failure, HDMI disconnect,
  GUI crash and session interruption before marking writable layouts complete.
- [ ] Connect riceExplorer only **after its own 1.0 release**, then verify the
  shared file-operation compatibility and error-path gates.

## Release acceptance

- Each non-macOS rice can open its own Settings window, Alt-Tab away and back,
  drag it between monitors, resize it, and continue working without losing
  settings state or unexpected close/raise behavior.
- Focus/keyboard and at least 200% scaling leave every live action reachable;
  controls report unavailable providers and errors honestly.
- Actual file drops are tested for valid/invalid URI, cancellation, denied
  permissions, moving the same file, multi-selection and cross-volume changes.
- GitHub GTK/X11 CI and owner Mint/XFCE hardware acceptance both pass before
  moving this workstream from development to complete.

**Important:** Moving a window and limited, confirmed local-file copying are
implemented where stated. Complete file-manager drag-and-drop, full monitor
transactions and physical hardware sign-off are **not** claimed complete.
