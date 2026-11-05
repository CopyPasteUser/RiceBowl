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
| XP Luna | Custom draggable Control Panel caption; now normal WM client that stays open on focus loss | Persist geometry, deeper native task pages, drag-and-drop file surfaces |
| Windows 98 SE | Normal decorated Control Panel window already managed by XFWM4 | Richer system applets, file/desktop drag-and-drop |
| Windows 7 Aero | Normal decorated Control Panel already managed by XFWM4 | Native task dialogs, richer per-app windows and file/desktop drag-and-drop |
| Windows 10 | Standalone native Settings shell; now has draggable custom title and taskbar identity | Stable geometry across external-display changes, deep app pages and file/desktop drag-and-drop |
| ChromeOS | Separately decorated GTK Settings app | ChromeOS-specific file/desktop drop targets and window management fidelity |
| Frutiger Aero | Aqua Control Center now normal, draggable, focus-persistent WM client with native hardware pages | Dedicated secure PIN agent, rollback-safe monitor editor, desktop/file drop targets, deeper control pages |
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
- [ ] Validate focus switching, move, resize, maximize, taskbar, Escape,
  1024×768 and multi-monitor unplug using real XFWM4 on Linux Mint.
- [ ] Add per-rice `Gtk.Dest`/GIO and riceExplorer drag source/target actions
  for moving/copying files only after secure drop semantics and undo exist.
- [ ] Build the local BlueZ PIN/confirm agent with strict request expiry,
  no passkey logging, explicit trust policy and physical device tests.
- [ ] Add a staged monitor mode/position editor only after an independent,
  crash-surviving revert timer is exercised across session changes.
- [ ] Connect riceExplorer's Aqua renderer when its separate project passes
  the shared file-operation compatibility and error-path gates.

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

**Important:** Moving a window by its caption is implemented where stated;
generic file drag-and-drop support is **not** claimed complete.
