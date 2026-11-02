# Four new RiceHub rices · 0.6 release roadmap

The four additional installable desktop styles are Windows XP Luna, Windows
98/2000 Classic, ChromeOS and Y2K / Frutiger Aero. They are original XFCE/X11
interpretations, not copies of proprietary OS assets, trademarks or logos.
Their optional GTK concept dialogs remain read-only and are intentionally
separate from the live installable versions.

## Implementation snapshot (2 November 2026, 0.6.0)

- macOS Aurora Night/Day/Aqua, Windows 7 Aero and Windows 10 Ten remain the
  existing installable families. Unfinished Liquid Glass styles and Windows 11
  are **not** in the planned set.
- `main` already coordinates Plank, MacBar and Windows shells, has delayed
  XFCE login reconciliation, and handles the MacBar `GApplication` quit path.
  Every future rice must use this switching/recovery foundation, not launch a
  second competing panel or mutate Plank autostart on its own.
- All four now have generated original GTK3, XFWM4 and icon themes, distinct
  full-HD wallpapers, dedicated live taskbar CSS and genuine Gio application
  menus, persistent pins, Wnck task switching and quick settings.
- `macrice rice plan/apply/restore <key>` uses the shared transactional engine.
  Schema 5 snapshots include all six native taskbar autostart entries. Old
  schema 1–4 restore points remain readable.
- `Super_L`, `Control_R`, login reconciliation and XFCE panel handoff route
  through the same coordinator as Aero/Ten; no new daemon is added.
- Four separate GTK3 previews remain strictly *read-only*. Their sample app
  search and sample file manager do not change the desktop.

## Style studies

| Family | Identity | Live features | Remaining acceptance risk |
| --- | --- | --- | --- |
| Windows XP Luna | Blue Luna taskbar, green Start and sunlit meadow | Live Start search, window buttons, app pins, control panel | Contrast and small-screen keyboard use on real Mint |
| Windows 98 / 2000 | Teal desktop, dense gray controls and square chrome | Classic Start, real apps, live taskbar, system tools | Dense menu ergonomics and XFWM consistency |
| ChromeOS | Pastel wallpaper, light bottom shelf | Real search, app tiles, shelf pins, quick settings | Launcher sizing on narrow displays |
| Y2K / Frutiger Aero | Cyan glass-inspired panels, original green landscape | Searchable launcher, live taskbar, system tools | Fallback appearance without a GPU compositor |

## Development roadmap

### P0 — Design validation (completed in the concept stage)

- [x] Initially include the four families in RiceHub Discover as **Prototype only** before their 0.6 promotion.
- [x] Create a distinct themed GTK3 teaser for each family.
- [x] Provide an interactive, no-write desktop preview with launcher, search,
  empty-results state, sample file-manager window and task buttons.
- [x] Keep the preview stage free of `STYLES`, CLI apply and backup writes; replace this limitation with guarded installable styles in 0.6.
- [ ] Review each prototype's visual balance and keyboard/focus on real Mint XFCE.
- [ ] Collect feedback on density, icon style, taskbar behavior and wallpapers.

### P1 — Shared desktop shell foundation

- [x] Reuse *proven* common behavior from Ten/Aero shells: application
  discovery, task switching, tray, desktop workarea and launch-safe actions.
- [x] Retain the single session coordinator for Plank, MacBar, Aero/Ten and
  future shells. Make transitions reversible and idempotent after relogin.
- [x] Verify XFCE themes, bundled icons, font and wallpaper before applying;
  document optional Wnck and compositor requirements.
- [ ] Benchmark launch time, idle PSS and CPU on Mint XFCE before adding effects.

### P2 — Installable XP and Classic candidates

- [x] Package wholly original GTK3, XFWM4, icon and wallpaper artwork, with
  the existing Adwaita cursor as a standard fallback.
- [x] Implement genuine Gio launchers and event-driven Wnck window buttons.
- [x] Support keyboard search, Escape and focus dismissal, tray coexistence,
  Show Desktop, multi-monitor positioning and accessibility labels.
- [x] Add explicit plan/apply/restore with snapshot and failure rollback.
- [x] Capture real GTK/X11 screenshots and run isolated virtual-session smoke
  for every new shell and its search/quick settings.
- [ ] Conduct physical Mint XFCE login/apply/restore tests.

### P3 — Installable ChromeOS and Y2K candidates

- [x] Build the shelf/app drawer and aqua taskbar on the shared shell backend.
- [x] Provide a flat/low-effects fallback; no dependency on blur or shaders.
- [x] Ensure the four new rices never fight Plank or the managed session panel.
- [ ] Repeat restore, update, relogin, screen-size and low-memory validation.

### Release gate

The `0.6.0` functional release requires side-effect-free `plan`, snapshots
before `apply`, guarded failure rollback, an isolated restore test, working
search and keyboard actions, original artwork and GTK/X11 integration smoke.
Those automated gates pass. The **1.0 hardware-stable** milestone additionally
requires logout/reboot persistence, compositor and multi-monitor testing,
repeat switching on physical Mint XFCE/X11, and documented resource budgets.

CI covers isolated GTK smoke checks for all four new shells, including genuine
Start/quick-setting screenshots, plus the original Wnck window-close crash
integration test. Screenshot and automated-review evidence accompanies `0.6.0`;
real Linux Mint XFCE/X11 acceptance is the outstanding 1.0 gate.

## Try the full rices and previews

Open `ricehub` → **Discover rices** → choose a family → **Check requirements**
→ **Apply rice**. Alternatively, use `macrice rice plan winxp` before applying
from the terminal. The **Explore read-only preview** button opens a separate,
non-installing illustration; preview sample windows still never launch apps.

On the owner's Mint/XFCE machine, check in order: apply each of the four rices;
open/close menus with `Super_L` and `Control_R`; launch and close CADCraft or
another GTK app repeatedly; switch through macOS, Aero, Ten and back; log out
and in; verify no stray taskbars or XFCE panels; perform a complete restore.
Record any real-hardware failures before marking the 1.0 milestone accepted.
