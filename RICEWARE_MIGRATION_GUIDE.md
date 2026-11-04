# Riceware 1.0: incremental renderer migration guide

This guide describes the **shared backend API 1.0** shipped inside RiceBowl.
It does not mean that a new desktop shell, independent notification daemon,
desktop compositor or standalone Wine manager has passed 1.0 acceptance.
Existing renderers and Linux services keep ownership throughout migration.

## Contract and ownership

| Integration | Shared backend | UI owner / safe fallback |
| --- | --- | --- |
| Hardware controls | `macrice.riceware.spice` | Each rice's own control panels; existing `hardware_status` paths |
| Notifications | `macrice.riceware.pop` | XFCE Notifyd owns delivery/history; existing native per-rice UIs |
| Desktop icons | `macrice.riceware.plate` | XFDesktop owns wallpaper, file actions and drag/drop |
| Windows app launchers | `macrice.riceware.wine`, `wine_apps` | Optional Wine installation and managed private prefixes only |
| Async UI calls | `macrice.riceware.worker` | Each popover/window owns and closes its request runner |
| Rice selection | `macrice.riceware.profiles` | Active RiceBowl session/profile remains authoritative |
| File operations | Separate `riceExplorer` repository | Thunar/GIO fallback until riceExplorer is independently accepted |

The API is imported from Python, without a service or IPC installation:

```python
from macrice.riceware import API_VERSION, manifest
from macrice.riceware import plate, pop, profiles, spice, wine_apps

assert API_VERSION == "1.0"
print(manifest()["components"].keys())
print(profiles.family("winxp"))  # "winxp"
print(spice.action_specs())       # UI control range and input types
print(plate.snapshot())           # Read-only XFDesktop inventory
print(wine_apps.list_apps())      # Empty if no managed Wine prefixes
```

Use each module's structured return values, not its terminal JSON or text.
`spice.read()` and `spice.change()` return a `Result` with `status` of `ok`,
`unavailable` or `error`; only `ok` after a write means a verified readback.
Never assume an absent provider is switched off. Do not call any synchronous
hardware or notification backend from the GTK main loop.

## GTK integration pattern

```python
from gi.repository import GLib
from macrice.riceware import pop, spice
from macrice.riceware.worker import LatestRequestRunner

runner = LatestRequestRunner(GLib.idle_add, workers=3)

def show_audio(response):
    # This callback runs on GTK's main thread.
    if response.error:
        show_error(response.error)
    elif response.value.status == "ok":
        render_audio(response.value.value)
    else:
        show_unavailable(response.value.reason)

runner.submit("audio", lambda: spice.read("audio"), show_audio)
runner.submit("audio", lambda: spice.change("audio_volume", 35), show_audio)

def on_notifications_changed():
    runner.submit("history", pop.history, render_history_response)

observer = pop.watch(on_notifications_changed)

# On widget/window destruction, before destroying GTK objects:
observer.close()
runner.close()
```

`show_error`, `render_audio`, `show_unavailable` and
`render_history_response` above are renderer-owned UI functions. A fresh
request with the same key suppresses an older **display callback**; it cannot
undo a hardware write already in progress. Disable/reconcile a writable
control while its mutation is pending, rather than submitting competing
writes. The runner stops accepting work after `close()`; neither workers nor
the observer are global resident services. A notification watch is optional:
if XFCE Notifyd is missing, retain the existing fallback view.

## Migration order, one rice at a time

| Phase | Rice family / existing style keys | First safe adapter switch |
| --- | --- | --- |
| 1 | Windows XP (`winxp`) | Audio/Wi-Fi/Bluetooth sliders in XP flyouts and Control Panel |
| 2 | Windows 7 (`aero-meadow`, `aero-cascade`) | Same real controls in Aero tray and device applets |
| 3 | Windows 98 (`winclassic`) | Classic Control Panel and XFDesktop shortcut visibility |
| 4 | Windows 10 (`ten-dark`, `ten-light`) | Quick actions, device settings, notification history |
| 5 | ChromeOS (`chromeos`) | Hierarchical Settings and actual XFCE notification history |
| 6 | Frutiger Aero (`frutiger`) | Distinct control-center controls with shared hardware results |
| 7 | macOS (`night`, `day`, `aqua`) | MacBar/Control Center and native notification presentation |

**XP checkpoint (4 November 2026):** XP Luna's taskbar status, audio
volume/mute and output selection, Wi-Fi scan/connect/disconnect/radio,
Bluetooth power/device connections, power profiles, brightness and safe desktop
shortcut management are now wired through riceSpice/ricePlate and a per-shell
bounded worker. The existing XP Control Panel can still open native XFCE
tools for unsupported advanced tasks. XFCE Notifyd remains the owner of
third-party notifications; XP's local hardware-event balloons are not yet
a ricePop notification-history consumer. This is **not** physical hardware
acceptance or completion of all XP Control Panel applets.

**Windows 7 checkpoint (4 November 2026):** Aero's own vertically arranged
volume flyout, Wi-Fi/Bluetooth/battery UI, taskbar status and Linux
device controls in the Control Panel now consume the same bounded riceSpice
worker as XP; opt-in Win7 desktop shortcuts use ricePlate. Aero's glass
Superbar, calendar, SNI tray and native Control Panel navigation remain visually and
structurally distinct. Third-party notifications stay with XFCE and deeper
Control Panel tasks provide the same native Power/Network/Sound/Bluetooth
flyouts alongside advanced Linux tools. Aero's small Action Center flyout reads
XFCE's real notification history via `ricePop`, allows explicitly marking it
read, and uses a separate, quiet-mode-aware balloon only for observed local
device events. It does not replace XFCE Notifyd or replay third-party actions.
Physical hardware and
full seven-rice switch testing are not claimed.

**Windows 98 SE checkpoint (4 November 2026):** Classic taskbar hardware
status, volume and mute use a per-shell bounded riceSpice worker instead of
private unbounded hardware threads. Classic square/beveled tray and native
Control Panel applets expose verified Wi-Fi radio/scan/connect/disconnect,
Bluetooth power and paired-device connections, sound output selection,
brightness and supported power profiles. Failed writes never claim success;
unavailable backends explain missing controls and advanced tools remain
reachable. A read-only desktop icon inspector obtains real file metadata
through ricePlate without taking XFDesktop ownership or changing user files.
The rice is labeled Windows 98 SE; a different Windows 2000 preset is not yet
provided. Physical hardware acceptance, deeper Control Panel tabs and classic
desktop special folders are still open.

**Windows 10 checkpoint (4 November 2026):** The flat Win10 taskbar now
receives its device status from `riceSpice`, and Action Center volume/mute
mutations use verified shared readback rather than new ad-hoc threads. The
distinct Win10 dark Action Center renders XFCE's real `ricePop` notification
history, explicit per-item dismiss and mark-unread-as-read controls, plus
independently read and verified Wi-Fi/Bluetooth/Focus Assist switches. Missing
providers disable controls honestly; all blocking work is dispatched through
one bounded, closeable per-shell worker and notification content is discarded
when the flyout closes. Other settings tiles remain advanced-tool launchers,
not fake toggles. This is **a migration checkpoint**, not full Windows 10
22H2 or physical Mint acceptance: the network list, complete Settings app,
Airplane/VPN/Project modes, Explorer UI, touch/scaling and multi-monitor gates
remain open.

**Windows 10 next-stage checkpoint:** Native Settings, network flyout and
Task View now consume the same Riceware/XFCE contracts. Settings is an
independent renderer with real category navigation; a missing Linux tool is
disabled, not simulated. NetworkManager owns Wi-Fi connections, with explicit
user actions, verified readback and honest saved-credential errors. Task View
uses existing libwnck/XFCE workspaces and never creates its own desktop owner.
An installed RiceExplorer binary is offered as an opt-in `win10` launcher only;
Thunar and default MIME handlers are left untouched. Advanced Settings and
physical-hardware acceptance are still open gates.

**ChromeOS checkpoint (4 November 2026):** The Material You Shelf now polls
hardware status through one per-shell bounded riceSpice runner; Quick Settings
volume/mute and device subpages share verified reads and mutations with the
separately navigable ChromeOS Settings app. Those pages cover real Wi-Fi
radio/SSID connections, Bluetooth adapter and paired-device links, sound
output/microphone, brightness, battery and supported power profiles. The
existing Chrome-only visual styles and Linux utility deep links remain.
XFCE notification history, unread badge, individual dismissal, marking read
and Do Not Disturb reuse ricePop over the existing notifyd service, without
starting a second daemon or saving private notification content. Hidden
device pages discard late callbacks; the shared runner and D-Bus observer
close on session shutdown. Hardware/suspend acceptance and the broader
Material You fidelity checklist remain open.

The family mapping changes **selection only**; per-rice windows, menu flows,
icons, keyboard shortcuts, layouts and styling must remain independent.
Do not substitute a generic themed Settings page for any of the seven.
`riceWine` app registrations may appear in any rice's own Start/app menu,
but are entirely optional. Never silently create a prefix when switching rice.

For **each** phase, migrate one feature (e.g. audio) before the next:

1. Locate the existing renderer entry point and current working control. Keep
   the fallback path and user-customized data intact.
2. Wire its read through a per-window request runner; render loading,
   unavailable, denied/error and actual-value states distinctly.
3. Wire write actions explicitly, use `spice.action_specs()` to constrain the
   UI, and show success only after verified readback. Avoid duplicate writes.
4. Wire notification, desktop or Wine data **only where already requested by
   that renderer**; close observers/workers on navigation or window removal.
5. Test first, second and third clicks; Esc/back, scroll at 800x600, focus,
   keyboard activation, rapid toggles, resume and missing backend.
6. Run targeted Python tests and virtual X11 smoke tests. On Mint XFCE/X11,
   verify real hardware, no duplicate tray/notification owner, idle resources
   and full switch-out/switch-back to the prior rice.
7. Only then remove that renderer's duplicate hardware glue. Do not change
   default file associations, autostart services or XFDesktop ownership.

### Acceptance checklist per rice

- [ ] Every enabled control is backed by a real provider; missing capabilities
  produce a truthful state and do not invent success.
- [ ] Rapid open/close and stale-result sequences cannot update destroyed UI.
- [ ] Audio, network, Bluetooth, brightness and power work on supported
  physical hardware, including offline/denied/missing-device cases.
- [ ] Native notification delivery/history persists across rice switches;
  no double delivery, stale third-party actions or competing D-Bus owner.
- [ ] XFDesktop icons, file associations, user shortcuts and in-flight file
  operations survive switching, logout/login and failed backends.
- [ ] Optional Wine app entry works with a deliberately registered test app;
  failed prefix init, missing Wine and an invalid app are recoverable.
- [ ] One full cycle through all seven rices preserves shell/session state.
- [ ] Screenshot and keyboard/visual acceptance on target hardware recorded.

## Diagnostics, rollback and release boundaries

Use the opt-in CLI to inspect without opening a renderer:

```bash
python3 -m macrice riceware manifest
python3 -m macrice riceware spice status
python3 -m macrice riceware pop status
python3 -m macrice riceware plate status
python3 -m macrice riceware wine status
python3 -m macrice riceware wine apps
```

On a regression, switch that rice's feature flag/adapter call back to its
existing supported backend and rerun its smoke test. No Riceware API import
applies system state by itself. Do not delete Wine prefixes or notification
logs as a rollback. Use RiceBowl's existing session apply/restore mechanism
when changing shell processes. Do not replace Thunar with riceExplorer until
its separately verified safe handoff is accepted.

**Release rule:** API contract 1.0 may be used for incremental implementation;
app-wide RiceBowl 1.0, full Wine compatibility and all-rice migration remain
separate, unverified release gates. See [the ecosystem roadmap](RICE_ECOSYSTEM_ROADMAP.md)
and [backend reference](RICEWARE_FOUNDATIONS.md).
