# RiceBowl riceware ecosystem roadmap

Status: **initial backend foundations implemented, renderer migration and acceptance open** (4 November 2026). This remains the implementation contract for shared capabilities behind the seven structurally distinct rice families, not an announcement of completed applications or a release.

**Goal:** one dependable Linux capability layer with seven deliberately different desktop experiences. A rice must be able to change component structure, navigation, controls and visual assets—not just colors—without duplicating filesystem safety logic, inventing system state or breaking a running session.

## Decisions and boundaries

| Component | Ownership / deployment | Decision | Trigger for expansion |
| --- | --- | --- | --- |
| **riceExplorer** | Existing independent Rust repository | **Required shared file manager**; finish its safety/volume/network/recovery gates before replacing Thunar | Follow [riceExplorer ROADMAP](https://github.com/CopyPasteUser/riceExplorer/blob/main/ROADMAP.md) |
| **riceSpice** | Initially an internal RiceBowl capability module plus rice-owned renderers | **Build incrementally from existing backends**; no new daemon/repository now | Separate app/process only when independent lifecycle and multiple frontends materially require it |
| **ricePop** | Initially adapters around existing native/XFCE notifications | **Conditional independent notification host** | Only when authentic cross-application history/actions cannot be provided safely through existing supported APIs |
| **ricePlate** | Initially XFDesktop + existing rice-specific desktop adapters | **Conditional independent desktop surface** | Only when tested desktop requirements cannot be delivered through XFDesktop and scoped extensions |
| **riceWine** | Opt-in internal prototype, future independent helper if justified | **Minimal isolated-prefix prototype; not required for RiceBowl 1.0** | Separate repository only after demonstrated need beyond Wine/Bottles/Lutris launch flows |
| RiceBowl shell/session | Existing RiceBowl repository | **Keep shared**: profile switching, backup/restore, launcher/taskbar/window tracking, tray ownership | Do not create a second shell manager |
| Linux infrastructure | NetworkManager, BlueZ, PipeWire/PulseAudio, UPower, UDisks2/GVfs, XFWM4/XFCE | **Reuse platform services** | Never create a competing network, Bluetooth, audio or window-management daemon for aesthetic fidelity |

**Non-goals:** a mandatory Wine runtime, a new operating system, a new general-purpose window manager, forced replacement of the login manager, proprietary Windows/macOS/ChromeOS assets, global default-app changes, nonfunctional toggles or idle background services without user opt-in.

Existing code to preserve and audit: `macrice/hardware_status.py`, `bluetooth_dbus.py`, `shell_session.py`, `aero_windows.py`, `aero_tray.py`, `frutiger_native_controls.py`, `win7_control_panel.py`, `luna_control_panel.py`, `chrome_settings.py`, `chrome_notification_backend.py`, `chrome_notifications.py`, `ten_action_center.py`, `luna_notifications.py`, `luna_desktop.py`, and `win7_desktop.py`. These are working starting points, not disposable prototypes. MacMenu, MacBar, Control Center and optional Plank keep their existing lifecycles.

## Names and project identity

All helper names use the same **rice** family but keep an immediately understandable subtitle. Four names now refer to importable internal backend foundations, **not shipped standalone programs or repositories**.

| Name | User-facing purpose |
| --- | --- |
| **riceExplorer** | Customizable file manager (existing separate Rust project) |
| **riceSpice** | Real Linux system settings and profile-specific Control Panels (start inside RiceBowl) |
| **ricePop** | Notification delivery/history and profile-specific presentation (conditional) |
| **ricePlate** | Desktop surface, icons and desktop context actions (conditional) |
| **riceWine** | Opt-in Wine application setup, per-app prefixes and launch integration (future optional project) |

The names are stable enough for planning; reserve public executable names, D-Bus IDs and separate repositories only when implementation boundaries have passed their decision gates. A new rice is **not** required to depend on all five helpers.

## Backend foundation checkpoint — 4 November 2026

- [x] `macrice.riceware.spice`: on-demand structured hardware state and explicit
  actions delegating to existing verified backends, without session mutation.
- [x] `macrice.riceware.pop`: XFCE-native notification history, read/dismiss,
  quiet mode and an explicit, bounded `notify-send` operation. No duplicate log.
- [x] `macrice.riceware.plate`: read-only desktop item model and existing safe
  XP/Win7 shortcut management. No XFDesktop replacement or file mutation engine.
- [x] `macrice.riceware.wine`: optional local prefix creation and explicit
  unprivileged process start using installed Wine tools; never scans/imports,
  edits or removes other prefixes. Failed initialization remains recoverable.
- [x] `macrice riceware` CLI, module tests and bundled installer verification.
- [ ] Migrate individual rice renderers once API contracts are validated on
  actual Linux Mint hardware; do not check off S0–S6 by inference.
- [ ] Evaluate an independent ricePlate process/host, ricePop notification
  ownership and riceWine standalone project only after their respective gates.

See [Riceware foundation API and manual checks](RICEWARE_FOUNDATIONS.md).

## Required architectural contracts

1. **One source of truth:** use the active RiceBowl profile/session state for renderer selection. Switching a rice updates UI presentation without replaying device changes, changing file associations or killing in-flight riceExplorer jobs.
2. **Backend versus renderer:** real Linux reads/writes, capability checks, permission handling and timeouts live in shared adapters; profile-specific UI controls, layouts, iconography and navigation stay in their respective renderers. Do not consolidate seven UIs into one themed card grid.
3. **Truthful state:** after a mutating device action, read back the actual state before displaying success. Distinguish loading, missing device, unsupported operation, disconnected, permission denied and command failure.
4. **Explicit authority:** no silent network disconnect, Bluetooth pairing, destructive file operation, power action, removal of desktop files or replacement of notification hosts. Use the existing session plan/apply/restore flow where desktop ownership changes.
5. **Lightweight operation:** event-driven subscriptions where supported, bounded workers/timeouts and no permanent duplicate polling loops. Benchmark cold launch, idle PSS/CPU and interaction latency before setting performance budgets.
6. **Compatibility:** XFCE/X11 is the primary target; never claim native compositor/DWM parity. Respect user-edited assets, startup entries, notification services and custom default apps. Preserve existing profile keys and configuration migrations.
7. **Fail-safe coexistence:** a missing optional shared component must leave the chosen rice and ordinary XFCE applications usable; Thunar remains available until riceExplorer passes its release gate.
8. **Testing:** disposable filesystem fixtures and temporary X11 sessions for automated changes; real Linux Mint hardware sign-off for Wi-Fi/Bluetooth/audio/battery, suspend/resume, HDMI, HiDPI, Plank and multi-rice switching.

## Implementation phases

### S0 — Audit and baseline (P0; prerequisite)

- [ ] Inventory every device/settings method and its caller, including duplicated Bluetooth/audio/network/display logic and current fallback paths. Identify which adapters already perform readback.
- [ ] Trace all seven renderers' deep Settings, tray, notification, desktop and Explorer entry paths, including second/third-click behavior; document what is real, disabled or a system-tool launcher.
- [ ] Record active session ownership: XFCE panel, XFDesktop, notification host, SNI watcher, MacBar, Plank, keyboard shortcuts and default file manager. Test plan/apply/restore on disposable XDG data.
- [ ] Establish targeted unit/GTK/Xvfb tests and a capture matrix (800x600, 1024x768, 1600x900, multi-monitor where available). Keep current screenshots and manifest provenance.
- [ ] Document boundaries and rollback for each proposed component; record a baseline PSS/CPU/startup measurement on actual supported hardware before optimizing.

**Gate:** an accurate, source-linked inventory and passing baseline regressions. No new processes or repositories.

### S1 — Shared riceSpice capability layer (P0; build inside RiceBowl)

- [ ] Consolidate only duplicated hardware operations around existing `hardware_status`/BlueZ/NetworkManager/audio/display helpers; preserve callers through compatible adapters. Do not rewrite functioning backends.
- [ ] Expose structured capability/state/action results, including availability and reason, loading, timeout, denied and readback mismatch. Keep writes asynchronous and bounded, with no privileged shell interpolation.
- [ ] Cover actual audio output/input selection and volume/mute, Wi-Fi scan/connect/disconnect, Ethernet status, Bluetooth power/paired devices, battery/AC, backlight where writable, power profile and display enumeration. Add further controls only when at least one rice requires them.
- [ ] Prove no duplicated device polling or redundant per-renderer mutation code; keep feature-specific adapters only where Linux APIs genuinely differ.
- [ ] Inject fake hardware adapters into regression tests for success, absent backend, permission denial, disconnected device, stale asynchronous results and readback disagreement.
- [ ] Preserve existing XP/Win7/Frutiger/ChromeOS controls and settings paths while moving their business logic to the shared layer.

**Gate:** each migrated action works and is verified in at least two structurally different rice renderers; zero regressions in the other five. No new riceSpice executable at this stage.

### S2 — Deep, independently structured Settings experiences (P0/P1)

- [ ] Windows 98: classical icon Control Panel, tabbed applets and period-correct dialogs backed by real Linux capabilities.
- [ ] Windows XP: category/classic Control Panel, task-oriented detail pages and native-feeling property sheets.
- [ ] Windows 7: category/large/small-icon Control Panel, breadcrumbs, history, search, useful third-level applet pages and classic device dialogs.
- [ ] Windows 10: dedicated multi-page Settings navigation and Action Center quick actions; no recycled Win7 Control Panel surface.
- [ ] ChromeOS: dedicated hierarchical Settings app, Quick Settings subpages and device controls; retain the existing ChromeOS implementation and notification-history fallback.
- [ ] Frutiger Aero: distinct Aqua Control Center with nested pages, sliders, switches, live device lists and consistent material hierarchy; preserve the existing native-control work.
- [ ] macOS Aurora: Control Center and system-preference style navigation, reusing MacRice components without forcing Windows layouts onto them.
- [ ] Verify keyboard focus, Esc/Back, search, breadcrumbs or tabs where appropriate, small-screen scroll, and second/third-click loading/error/disabled states in every profile.

**Gate:** each enabled setting performs a real action or offers a truthful explanation; no renderer is just a recolored shared Settings window. Separate process/repository requires a measured lifecycle justification and a compatibility migration plan.

### S3 — ricePop decision and optional implementation (P1; conditional)

- [ ] Inventory current XP balloons, Win7 notification area, Windows 10 Action Center and ChromeOS notification history/calendar behavior; prefer existing native/XFCE hooks when sufficient.
- [ ] Define shared notification/event data needed by the UIs (source, timestamp, optional action, urgency, dismissal, privacy limits), without claiming third-party events inaccessible to the current owner.
- [ ] Prototype an optional session-local notification host only if full cross-application delivery/history/actions cannot be achieved safely through the existing host. Observe the single-owner Freedesktop D-Bus contract.
- [ ] On opt-in ownership change: detect the existing host, save prior state, prevent dual ownership, provide bounded readiness checks and guarantee restore/fallback after crash, switching or logout.
- [ ] Give XP small balloons, Win7 period-appropriate alerts, Windows 10 actionable history, ChromeOS cards/calendar and macOS Notification Center distinct renderers. Keep notification history local and provide clear/delete/privacy controls.
- [ ] Test third-party notifications, actions, transient/persistent events, quiet behavior, malformed/oversized payloads, duplicate delivery, switching during a notification, X11 focus and fallback to existing XFCE notifications.

**Gate:** real cross-app events reach the intended UI with no lost or duplicated notifications, and session restore works. If existing APIs meet requirements, record ricePop as **not needed** and keep it a module.

### S4 — ricePlate decision and optional implementation (P1; conditional)

- [ ] Compare XFDesktop's native icon grid, drag/drop, context menus, trash, wallpaper, file launch and multi-monitor behavior against Win98/XP/Win7/macOS/ChromeOS/Aqua requirements; log specific unachievable interactions.
- [ ] First extend existing `luna_desktop`, `win7_desktop` and XFDesktop integration with reversible scoped configuration; respect user-created desktop files, symlinks and launcher placement.
- [ ] If genuine blocking requirements remain, prototype an isolated desktop surface on a disposable XFCE/X11 session; avoid fighting XFDesktop for wallpaper, input, workarea, selection or file-icon ownership.
- [ ] Implement distinct per-rice desktop policies: classic Explorer icons/menus, XP My Computer/Trash, Aero desktop, ChromeOS normally icon-free, macOS Finder-like and Aqua-specific behaviors. Share file mutation operations with riceExplorer; never make a second copy/move engine.
- [ ] Verify keyboard/mouse/touch where available, drag in/out, icon arrange/select, new/rename/trash, panel workareas, hotplug, multiple monitors, login/relogin and full restore after desktop-surface failure.

**Gate:** there is demonstrated functionality that XFDesktop cannot reliably deliver, a safe replacement/fallback path, and measured resource impact. Otherwise do **not** ship a ricePlate process.

### S5 — riceWine feasibility and opt-in compatibility helper (P2; independent of core release)

- [ ] Verify concrete user journeys for running selected Windows applications from XP/7/10-inspired shells. Compare installed Wine tools and existing Bottles/Lutris workflows before proposing a new launcher; do not rebuild their package management.
- [ ] If gaps remain, define a minimal, unprivileged frontend for selecting the installed Wine executable, creating and inspecting per-application prefixes, importing existing prefixes only after consent, and launching a chosen executable with bounded logs.
- [ ] Keep every prefix isolated, preserve user-owned `WINEPREFIX` data, use explicit confirmation and backup/export before removal or migration, and never run arbitrary downloaded installers or elevated commands automatically.
- [ ] Make Windows-app menu entries optional user-created desktop launchers with safe argument handling, clear icon/provenance, error reporting and reversible RiceBowl pinning. Do not modify system-wide MIME handlers.
- [ ] Show installed Wine version, prefix architecture and actual application execution outcome without promising compatibility with particular software, anti-cheat, DRM or game launchers.
- [ ] Prove cold startup, idle cost, source integrity, prefix ownership, cancellation, failed installer recovery and clean uninstall on disposable test prefixes. No persistent daemon.
- [ ] Decide whether a **separate riceWine repository** is warranted only after the small prototype demonstrates a user benefit beyond a configured native Wine/Bottles/Lutris launcher.

**Gate:** useful Windows-app integration without unsafe prefix mutations or mandatory Wine dependency. This is optional and **must not block RiceBowl, riceExplorer or the seven-rice 1.0 release**.

### S6 — riceExplorer integration and final acceptance (P0 release dependency)

- [ ] Keep the separate Rust file-manager repo authoritative for filesystem mutations, security decisions, queue, storage backends and recovery; RiceBowl may select a visual profile and location but must never duplicate file transfer code.
- [ ] Consume riceExplorer's stable, documented theme/launch interface; only add live theme IPC when its contract and in-flight job preservation are tested. Do not invent an unimplemented API.
- [ ] Verify structurally distinct Windows 98/XP/7/10/ChromeOS/macOS/Frutiger file-manager renderers on the same safe core, including error and progress dialogs.
- [ ] Gate default-file-manager handoff on riceExplorer's real safety, mount/network, recovery and Mint acceptance. Keep user choice, Thunar fallback and preserved MIME defaults.
- [ ] Run seven-rice cycle: Win98 -> XP -> Win7 -> Win10 -> ChromeOS -> Frutiger -> macOS -> Win98. Validate open windows, file jobs, tray ownership, notification flow, desktop icons, shortcuts, Plank/MacBar, theme assets and recovery.
- [ ] Capture genuine same-revision deep-interaction screenshots, inspect popup bounds and record CI outputs and performance measurements.
- [ ] Release only after clean install/update/rollback/uninstall, verified real-hardware sign-off and README/changelog/roadmap updates.

**Gate:** an XFCE/X11 daily-driver cycle without state loss, duplicate panels/notification hosts or unjustified new daemons. A separate release is not required for a roadmap-only change.

## Dependencies and order

1. **S0** is mandatory before any extraction or new program.
2. **S1 -> S2** delivers the immediate shared-settings benefit and can proceed independently of riceExplorer's unfinished file-operation gates.
3. **S3, S4 and S5 are decision gates**, not automatic repo-creation tasks. Only pursue after specific user-visible gaps and safe ownership evidence are recorded. riceWine is a separate, optional capability track.
4. **S6** depends on riceExplorer's separately verified release gates and shared-session compatibility. No production default-file-manager switch beforehand.
5. Maintain the main [RiceBowl roadmap](ROADMAP.md) and each rice-specific fidelity roadmap. Cross-reference component work instead of checking off broad original-fidelity requirements prematurely.

## Definition of done for any new shared component

- [ ] A documented real need in at least two rice families or a demonstrated platform limitation that cannot be handled with a small existing adapter.
- [ ] Single, explicit owner and process lifecycle; no conflicting XFCE, D-Bus, SNI, desktop, file-manager or session ownership.
- [ ] Distinct renderer contracts and a real functional Linux backend, including loading/empty/error/permissions states.
- [ ] Safe opt-in, persisted preferences only where necessary, reversible apply/restore and preserved user-customized settings.
- [ ] Targeted regressions, native X11 interaction checks, real hardware sign-off and measured idle cost.
- [ ] English README, changelog, migration notes and current screenshots updated with every implementation milestone.

**Decision principle:** build the smallest reusable capability that actually meets the fidelity target. Promote a module to an independent application only when ownership, isolation or lifecycle needs demonstrably justify the additional process and maintenance cost.
