# Application theming: cross-rice contract

RiceBowl styles the *session* and the surfaces it owns. A matching GTK/XFWM
theme is helpful, but does not give RiceBowl authority over arbitrary apps'
client-drawn interiors. The goal is integrated native software without
changing another application's profile or installing browser CSS implicitly.

| Surface | Supported approach | Still needs device verification |
| --- | --- | --- |
| XFWM4 server-side window decorations | Active rice's XFWM4 theme, with normal managed top-level windows | WM state, titlebar actions, decorations under each rice |
| GTK3 app widgets | Apply matching supported GTK theme and icons to new GTK processes | Which apps actually use GTK widgets vs. drawing their own chrome |
| Qt applications | Respect their existing QPA/theme integration; no forced runtime plugin | Toolkit/version and installed compatible Qt style |
| Firefox/Thunderbird | XFWM4 border only if they expose one; their own browser chrome is app-owned | Thunderbird build, CSD/titlebar preference, before/after screenshot |
| PhotoCraft and other custom editors | WM border if compatible; app interior is not automatically recolored | Its binary/toolkit, WM_CLASS, CSD and installed package version |
| Electron and web-rendered UIs | Treat their client-side chrome as independent; opt-in app themes only | Whether the app exposes a supported theming API |

## Task Manager: planned shared rice-owned application

- One lightweight, on-demand native process viewer (future `riceTask`, not a
  resident daemon) with strictly bounded `/proc` scans, memory/CPU snapshots,
  process search and honest permission/error states.
- A single functional backend; independent XP/7/10/98/ChromeOS/Aqua visual
  variants. Never silently replace `xfce4-taskmanager`, system shortcuts or
  file associations.
- Process termination, signals and privilege elevation are a separate,
  explicitly confirmed security phase; default viewer is read-only.
- Startup, refresh intervals, high-process-count scalability and GUI theme
  fidelity need native X11 testing before an advertised release.

## Evidence required for app-specific fixes

Record `WM_CLASS`, `_NET_WM_WINDOW_TYPE`, whether the application uses its own
titlebar, the current XFWM/GTK rice and a screenshot. Inspect without saving
personal application profiles or collecting file contents:

```bash
xprop WM_CLASS _NET_WM_WINDOW_TYPE _GTK_FRAME_EXTENTS
xfconf-query -c xfwm4 -p /general/theme
xfconf-query -c xsettings -p /Net/ThemeName
```

`xprop` prompts you to click the *affected window*; run it once per program.
These results tell us whether a window-border change can help or whether an
opt-in application-specific integration is necessary. No Thunderbird or
PhotoCraft user files are modified by this workstream.

**Dependency boundary:** riceExplorer remains decoupled until its own 1.0
release. macOS Aurora remains outside this UI refactor.
