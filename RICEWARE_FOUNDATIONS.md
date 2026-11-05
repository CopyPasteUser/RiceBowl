# Riceware migration API 1.0

The supported Python integration contract is `macrice.riceware.API_VERSION =
"1.0"`. Its four Linux backends are importable without starting services,
changing desktops or probing hardware. This is an **API release for gradual
UI migration**, not a claim that RiceBowl, standalone ricePlate or riceWine
has passed full physical 1.0 acceptance.

| Import path | Current contract | Intentionally deferred |
| --- | --- | --- |
| `macrice.riceware.spice` | `snapshot()`, `read(name)`, `change(action, value)`, typed `action_specs()` and verified `Result` | Real-hardware sign-off and actual renderer migration |
| `macrice.riceware.pop` | XFCE status/history/actions, native `send()`, event-driven `watch()` with `close()` | Separate notification host, third-party action replay |
| `macrice.riceware.plate` | Bounded snapshot, safe XP/Win7 shortcuts, per-rice appearance and optional native-GTK desktop preview | Real desktop takeover, multi-monitor icon DnD |
| `macrice.riceware.wine` | Private prefix create/resume/status/launch and log inspection | Downloads, arbitrary existing-prefix adoption, compatibility promises |
| `macrice.riceware.wine_apps` | Safe per-prefix Windows-app catalog (`register`, `list_apps`, `launch_app`, `unregister`) | Automatic Windows program scanning and installer execution |
| `macrice.riceware.worker` | `LatestRequestRunner(GLib.idle_add)` to keep GUI reads/writes off GTK thread and drop stale responses | One global resident polling daemon |
| `macrice.riceware.profiles` | `family(style_key)` for all seven rice UI families | Reusing a single visual layout across rices |

All APIs are importable without GTK or any resident service. Hardware mutations
delegate to `macrice.hardware_status`; native notification history delegates to
`macrice.chrome_notification_backend`. XFDesktop and Thunar stay in charge.

## Manual CLI checks

From a checkout (or use `macrice` after the normal RiceBowl update):

```bash
python3 -m macrice riceware manifest                 # Stable renderer API without I/O
python3 -m macrice riceware spice status             # On-demand real hardware state
python3 -m macrice riceware spice get wifi          # Read without changing it
python3 -m macrice riceware pop list                # Existing XFCE log, if exposed
python3 -m macrice riceware plate status            # Inventory; no file edits
python3 -m macrice riceware plate preview --style winxp  # Normal GTK window; no XFDesktop takeover
python3 -m macrice riceware wine status             # Wine version and managed prefixes
python3 -m macrice riceware wine apps               # Registered Windows app starters
```

Actions always require an explicit command:

```bash
python3 -m macrice riceware spice set audio_volume 35
python3 -m macrice riceware spice set wifi off
python3 -m macrice riceware pop send "RiceBowl test" "Native notification"
python3 -m macrice riceware pop quiet on
python3 -m macrice riceware pop clear --yes             # Irreversible! Explicit opt-in
python3 -m macrice riceware plate install --profile xp
python3 -m macrice riceware plate remove --profile xp
python3 -m macrice riceware wine create demo
python3 -m macrice riceware wine resume demo           # Only after failed initialization
python3 -m macrice riceware wine log demo              # Private init-log tail
python3 -m macrice riceware wine run demo /absolute/path/to/user-selected.exe
python3 -m macrice riceware wine register demo editor "My Editor" /path/to/editor.exe
python3 -m macrice riceware wine run-app demo editor
python3 -m macrice riceware wine unregister demo editor --yes
```

Only use device-changing examples when you intend that change. The notification
log depends on XFCE notifyd exposing the supported history interface; a missing
provider is reported, never synthesized. Desktop shortcut removal preserves
modified or preexisting files. riceWine requires an existing Wine installation;
all managed prefixes live under `$XDG_DATA_HOME/ricebowl/wine-prefixes` (or
`~/.local/share/ricebowl/wine-prefixes`). Each prefix must be private and
user-owned. Creating one runs `wineboot --init` with a per-prefix lock, waits
for a real Wine registry, writes a private diagnostic log and leaves an
incomplete prefix untouched on failure. `resume` retries that prefix after
failure without deleting it; `log` shows only a bounded, sanitized tail. `run`
reports an immediately failed Wine process but returns a started process ID,
**not** proof that the selected Windows app runs correctly. No prefix is
automatically deleted or migrated.

Registered Wine application launchers are held in an atomic, locked private
catalog inside each ready prefix. Unregistering removes only metadata; it
never removes the Wine application, its files or its prefix. Malformed catalogs
are preserved and reported as explicit issues. `riceware wine apps` can supply
the same applications to every distinct RiceBowl launcher.

## Rendering contract

- The common backends own real Linux reads/actions. The active rice controls
  visuals, icon assets, layout, navigation, error text and interaction design.
- The versioned manifest (`from macrice.riceware import manifest`) is read-only.
- Never run synchronous hardware or notification calls on GTK's main thread.
  `LatestRequestRunner` owns at most 1–6 workers and 64 outstanding request keys;
  it schedules callbacks through
  an injected UI dispatcher such as `GLib.idle_add`. Close it with its window.
- ricePop watches real XFCE signals; close each `NotificationWatch` when its UI
  is destroyed. No new `org.freedesktop.Notifications` bus owner is started.
- A missing provider yields an honest unavailable state. Keep XFCE/Thunar
  fallbacks and preserve user MIME defaults, desktop files and pending jobs.

See the [incremental migration guide](RICEWARE_MIGRATION_GUIDE.md) for working
API examples and per-rice acceptance gates.

## Checks and next gate

```bash
/usr/bin/python3 -m unittest tests.test_riceware -v
/usr/bin/python3 -m unittest discover -s tests -q
```

Before rerouting any existing UI: test adapters on the owner's Mint XFCE/X11
hardware (audio, Wi-Fi, Bluetooth, brightness, power, real notifyd, XFDesktop,
optional Wine), then migrate one renderer at a time with fallbacks. See
[S0–S6 roadmap](RICE_ECOSYSTEM_ROADMAP.md). No new repository is required for
these initial foundations.

The [ricePlate desktop plan](RICEPLATE_DESKTOP_ROADMAP.md) tracks its preview
canvas and the separately gated real-desktop owner transition. Preview layout
preferences live in the user's XDG configuration, never inside the source
checkout, and do not alter any XFCE system setting.

### Acceptance gates still open

- [ ] riceSpice: physical Wi-Fi connect/disconnect, Bluetooth pairing/power,
  audio input/output/mute, battery, brightness and suspend/resume with readback
  on the owner's Linux Mint machine; verify GUI worker-thread and stale-result handling.
- [ ] ricePop: third-party notification history/actions, DND and privacy on
  an actual supported XFCE Notifyd version, including service absence/restart.
- [ ] ricePlate: XFDesktop re-login, file changes during shortcut operations,
  multi-monitor, hotplug, drag/drop and safe recovery on physical X11.
- [ ] riceWine: successful real Wine prefix init/retry and Windows GUI launch;
  disk-full, missing Wine, timeout, damaged registry and existing-prefix cases.
- [ ] All seven rice renderers migrated without new background daemons,
  default-file-manager changes, loss of in-flight file jobs or session regressions.
