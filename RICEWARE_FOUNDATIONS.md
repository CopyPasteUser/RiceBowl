# Riceware backend foundations

These four lightweight Python modules expose a **functional starting point**
for future RiceBowl renderers. They are not new applications, resident daemons,
or complete reimplementations of XFCE/Wine. No rice changes its visual layout
or native service ownership merely because these modules are installed.

| Import path | Current contract | Intentionally deferred |
| --- | --- | --- |
| `macrice.riceware.spice` | `snapshot()`, `read(name)`, `change(action, value)` returning verified `Result` with serialized in-process writes | Asynchronous GTK binding, seven rice renderer migration, real-device acceptance |
| `macrice.riceware.pop` | XFCE `status()`/history/unread/DND/mark/dismiss/clear and explicit native `send()` | A new notification host, cross-app action replay, separate history DB |
| `macrice.riceware.plate` | Bounded/truncation-aware `snapshot()` and safe `manage_shortcuts(profile, action)` for XP/Win7 | Custom icon compositor, multi-monitor DnD, filesystem mutation |
| `macrice.riceware.wine` | `wine_version()`, `list_prefixes()`, `create_prefix(name)`, `resume_prefix(name)`, `read_init_log(name)`, `launch(name, executable, args)` | Installer downloads, prefix import/deletion, game compatibility claims |

All APIs are importable without GTK or any resident service. Hardware mutations
delegate to `macrice.hardware_status`; native notification history delegates to
`macrice.chrome_notification_backend`. XFDesktop and Thunar stay in charge.

## Manual CLI checks

From a checkout (or use `macrice` after the normal RiceBowl update):

```bash
python3 -m macrice riceware spice status             # On-demand real hardware state
python3 -m macrice riceware spice get wifi          # Read without changing it
python3 -m macrice riceware pop list                # Existing XFCE log, if exposed
python3 -m macrice riceware plate status            # Inventory; no file edits
python3 -m macrice riceware wine status             # Wine version and managed prefixes
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
