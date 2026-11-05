# RiceBowl 1.0 release acceptance · owner-run test sheet

**Release hold:** Virtual tests are useful, but a stable 1.0 cannot be declared
until the owner runs the hardware gates below on Linux Mint XFCE/X11. The
macOS Aurora implementation is frozen; no Aurora redesign is part of this pass.

## 1. Safe environment and recovery preflight

On the intended laptop, in a normal user terminal (never `sudo`):

```bash
echo "${XDG_CURRENT_DESKTOP:-unknown} / ${XDG_SESSION_TYPE:-unknown} / ${DISPLAY:-no-display}"
macrice doctor
macrice doctor --json
macrice performance report --samples 5 --json
macrice update check --refresh
```

Expected: XFCE/X11 and managed launchers healthy. An absent Bluetooth device,
`powerprofilesctl` or Plank is optional; note it rather than pretending it
exists. A warning about a missing shortcut recovery file is expected *before*
the first managed session. The doctor never changes settings or prints SSIDs,
private shortcut commands or passwords. Save only redacted diagnostics.

**Recoverability:** Before updating, verify the existing RiceBowl Recovery
page lists snapshots; keep copies of personal XFCE keyboard bindings and
wallpaper selections. `macrice update apply --yes` is a *manual* fast-forward
update from official `origin/main`, with staged install and best-effort rollback
to the previous archived bundle. It rejects dirty/divergent checkouts. It is
not a signed release verifier and cannot guarantee atomic rollback of every
external component. If it reports a failed automatic reinstall, stop; inspect
`~/.local/share/macrice-versions` before touching anything else.

## 2. Seven-rice session matrix

Test every transition in order: **XP Luna → Windows 7 → Windows 10 → ChromeOS
→ Windows 98 SE → Frutiger Aero → macOS Aurora → stock XFCE**. Then reverse
the order and repeat once after logout/login.

For each rice, record pass/fail for:

- Exactly one taskbar and launcher is active; no ghost MacBar or duplicate
  XFCE panel remains; Plank is present only where configured.
- Super toggles the launcher twice; Right Ctrl opens the correct native
  controls. App launch, window focus, pin/unpin and close all still work.
- Mouse clicks, keyboard navigation, popup edges, date/status and deep settings
  stay visible at **1024×768** and the laptop's native resolution.
- Switching back to stock XFCE restores its panel, original shortcuts and
  editable personal settings; user-owned Plank autostart is intact.

**Failure drill:** In a disposable session, simulate a shell that fails to
launch (or use a legitimately failing dependency) and confirm that the stock
XFCE panel and shortcuts are recovered. Never kill arbitrary system processes
to manufacture the failure.

## 3. Device controls (Frutiger P0 and cross-rice)

| Probe | Acceptance condition |
| --- | --- |
| Wi-Fi | Visible SSIDs and signal are real; saved connect/disconnect works, password entry uses a masked single-use field, a wrong password yields an error, enterprise Wi-Fi defers to the system editor, and radio-off requires confirmation. |
| Bluetooth | The nine-second on-demand BlueZ scan discovers real nearby devices, releases its session on finish or popover close and does not interfere with other discovery clients. Pairing uses the registered BlueZ default agent for PIN/confirmation (or fails honestly); verify actual paired/connected state, radio-off confirmation, and missing-agent behavior on the laptop. |
| Sound | Output volume, mute and device switching are verified after write; missing audio backend explains itself. |
| Power/display | Real battery and charging, brightness and supported profiles; Aqua reads the X11 output geometry, primary screen and offered modes without writes. Test real HDMI connect/disconnect, monitor ordering/scaling and suspend/resume. Writable display layout must have confirmed rollback before being implemented; no fictitious control success. |
| Notifications | XFCE remains the daemon; native history and Do Not Disturb update honestly; no duplicate notification process. |
| Calendar | Aqua clock opens a real local GTK calendar; selecting today works, without network/calendar-sync claims. |
| USB/files/media | The Aqua mounted-locations popup lists genuine Gio mounts and asks before asynchronous unmount; the audio flyout reads the session's MPRIS player and sends supported playback actions. Test busy-device errors, disappearing media players, hotplug, actual file operations and correct cleanup. **Physical-device acceptance and an Aqua riceExplorer renderer are still open.** |

## 4. Performance and stability

At a settled idle desktop and after opening/closing each native menu, capture:

```bash
macrice performance report --samples 7 --json
```

The report returns per-process **proportional set size (PSS)** in KiB, CPU as
percentage of one CPU core, and thread count; unavailable counters remain
`null`. Record cold-start latency, settled CPU, seven-rice PSS and battery
impact **on the physical ThinkPad** and compare before/after revisions. Do not
invent an absolute memory budget without baseline measurements. Repeat after
HDMI hotplug and suspend/resume. Check for growing process counts, leftover
shell instances, unresponsive controls and stale popovers.

## 5. Gate decision

- **Automated:** complete Python suite, native GTK/X11 constructor and small-
  screen captures, per-rice process-switch simulations, and updater rollback
  security contracts all pass in a single release candidate.
- **Hardware:** all applicable physical Mint/XFCE checks above pass. Unsupported
  optional hardware is explicitly *N/A*, never silently marked passing.
- **Release hygiene:** README, changelog, screenshots/manifest from **the same
  revision**, package checksum, and an explicitly chosen version/tag are ready.
- **Known gaps:** any incomplete Frutiger P0 feature (full Bluetooth discovery,
  advanced monitor layout, riceExplorer Aqua integration) must be completed or
  deliberately scoped *out* before naming the build 1.0.

Until the matrix is signed off, the correct status is **development snapshot,
not stable RiceBowl 1.0**.
