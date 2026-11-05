# XFCE resource boundaries — toward a lean RiceBowl desktop

RiceBowl currently runs **on XFCE/X11**, not as a complete desktop environment.
Its six non-macOS taskbars replace the XFCE panel; the macOS variant uses
MacBar and the user's Plank. The safest resource-saving strategy is to run
**one panel implementation at a time** and keep the shared session services
that still deliver real features.

## Current ownership

| Running component | Classification | RiceBowl policy |
| --- | --- | --- |
| `xfce4-panel` | Replaceable | Gracefully quit **after** the chosen RiceBowl shell is ready and shortcuts are installed; restart on failure or return to the stock rice. |
| RiceBowl taskbar (Windows 98, XP, 7, 10, ChromeOS, Frutiger) | RiceBowl | Exactly one active non-macOS shell. Quit others during switching. |
| `macbar` and `plank` | Mac dock/bar | Only expected for macOS rice; retained as user-owned, never edit the user's Plank autostart. |
| `xfwm4` | Core | Window placement, decoration and task/window controls rely on the existing X11 window manager. Keep. |
| `xfsettingsd`, `xfconfd` | Core | GTK/XSettings, icon, font and theme settings; required for correct rice appearance. Keep. |
| `xfdesktop` | Core | Existing wallpaper, desktop icons, XFCE settings and recovery. Keep until ricePlate becomes a supported replacement. |
| `xfce4-session` | Core | Session/logout, startup and restore. Keep. |
| `xfce4-power-manager` | Shared | Suspend/lid/backlight and battery policy. The RiceBowl power UI **is not** a replacement. Keep. |
| `xfce4-notifyd` | Shared | Delivery/history for real desktop notifications; ricePop reads and displays this data. Keep. |
| `xfce4-screensaver` | Shared | Locking/security; keep unless a verified alternative is in place. |
| `xfce4-clipman`, `tumblerd`, `xfce4-appfinder` | Shared / optional | Can serve other user applications; inventory only. User can separately review their own XFCE autostart preferences. |

This list is **not a service-disable script**. In particular, stopping the XFCE
power manager, notification server, or screen locker to save a few MiB can
silently remove important functionality and security. No global service,
systemd unit, XFCE configuration or user autostart entry is disabled by this
work. The stock panel stays available as a fallback.

## Measure the actual desktop

```bash
macrice performance desktop --samples 5
macrice performance desktop --samples 5 --json
macrice performance report --samples 5  # Previous RiceBowl-only report
```

The **desktop** report inspects current-user `/proc` processes on demand and
categorizes recognized XFCE and RiceBowl services. It prints proportional set
size (PSS), short CPU samples, thread counts and warnings for duplicate
panels, non-macOS shells with Plank/MacBar, or multiple RiceBowl taskbars.
It never prints process arguments, window titles, credentials or device names.
Unavailable counters remain `unavailable` / `null`; they are not guessed as
zero. The separate `XFCE sampled PSS` total avoids counting RiceBowl processes
as XFCE. CPU percent is a **per-core** snapshot, not sustained usage. Neither
command installs a daemon or changes the session. The RiceBowl Hub's
**Performance → Measure now** now also includes the recognized XFCE processes.

On your Mint XFCE/X11 laptop, compare these states *after the UI settles*:

1. Stock XFCE session (`xfce4-panel` present, no RiceBowl taskbar).
2. Each non-macOS RiceBowl rice (exactly one RiceBowl taskbar, no XFCE panel,
   MacBar or Plank).
3. macOS rice (MacBar and Plank, but no XFCE panel).
4. Return to stock XFCE and confirm the original panel and shortcuts recover.
5. Repeat after logout/login and suspend/resume, including any missing backends.

Because this environment is **not your Mint desktop**, no real saved RAM,
idle CPU reduction or successful physical service shutdown is claimed yet.

## What the code now saves

When reconciling a rice, RiceBowl previously spawned up to six Python/GTK
`--quit` helper processes for shells that often weren't running. It now checks
the exact GApplication D-Bus owner first, then the user's `/proc` for an
in-flight RiceBowl shell. Only when both prove the shell absent is the helper
startup skipped. A broken/unknown D-Bus state uses the existing, conservative
quit path. This reduces **transient startup/CPU work**, not six resident shells:
the quit helpers already exited quickly before this change.

## Longer-term XFCE reduction

Actual removal of `xfwm4`, `xfdesktop`, `xfsettingsd` or XFCE session ownership
requires separately validated replacements for window management, decorations,
multi-monitor behavior, keyboard shortcuts, desktop icons, settings, power,
lock screen, notifications and crash recovery. That is an architectural
milestone—not a safe background-service toggle. Integrations with ricePlate,
ricePop and riceExplorer should reduce these dependencies only when those
programs pass real hardware acceptance. No new background service is proposed
for the resource report.
