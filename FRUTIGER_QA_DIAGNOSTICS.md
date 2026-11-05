# Frutiger Aero taskbar · on-device interaction evidence (QA-11)

The owner reported Frutiger Aero taskbar icons sometimes **do nothing** on
Linux Mint/XFCE. Existing virtual-X11 pointer tests click Start, app pins,
device controls, drives, notifications and calendar, but **do not reproduce the
owner's issue**. A passing CI run is not physical acceptance.

To locate the failing event boundary without changing system settings,
RiceBowl has an **explicitly opt-in** trace on the live Frutiger shell:

```bash
macrice frutiger-shell --trace-actions
# Click Start, a taskbar app pin, Wi-Fi, audio, battery, Bluetooth,
# drives, notifications and the clock, including the allegedly inert icons.
macrice frutiger-shell --trace-stop
tail -n 45 "$(macrice frutiger-shell --trace-path)"
```

- The trace records only time, one fixed UI target label and the event phase
  (`click`, `result`, `dispatch`). `visible` is a Boolean for popups/menus.
  The app-pin **dispatch** phase only proves its handler ran, *not* that the
  launched application successfully opened.
- Recording is **off by default**, with no background timer. A running Frutiger
  shell accepts the start/stop commands through its existing GTK application
  command channel; they do not apply a rice, restart the shell, touch devices
  or launch any target application by themselves.
- The private `ricebowl/frutiger-interactions.jsonl` file under the user's
  XDG cache is owner-only (0700 directory, 0600 file), bounded to 64 KiB,
  and overwritten from the beginning when full. It never records app IDs,
  names, window titles, SSIDs, passphrases, commands or file contents. A
  symlink or a publicly readable destination is rejected.
- If `--trace-actions` refuses to start, inspect the RiceBowl cache directory's
  permissions. Never loosen them globally. The trace can also be interrupted
  by restarting the shell; it never survives restart automatically.

## Interpret the result

| Evidence | Likely boundary to investigate next |
| --- | --- |
| `click` absent for a physically pressed icon | X11 hit-testing, other overlapping window, click not reaching GTK target, disabled widget or stale shell |
| `click` present, `result` absent | Callback crashed, failed construction or blocked during popup creation; inspect the application's stderr/journal |
| `result` has `"visible": false` | GTK popover was hidden, unmapped or immediately dismissed; inspect focus/lifecycle |
| `result` has `"visible": true` but nothing appears | Visibility versus map/geometry, off-screen anchor, compositor/WM stacking |
| `app-pin` `dispatch` present | GTK dispatched the action; check the *target app's* actual launch outcome separately |

Compare behavior after a fresh login and after switching from XP or Windows 7
to Frutiger. Record the installed SHA (`git -C "$HOME/RiceBowl" rev-parse --short HEAD`),
session type (`echo "$XDG_SESSION_TYPE"`) and which icons fail; do not paste
entire private process logs. **No underlying QA-11 fix is claimed until the
on-device boundary is observed and confirmed.**
