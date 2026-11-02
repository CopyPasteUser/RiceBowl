# Four next RiceHub rices · concept plan

The next four *prototypes* are Windows XP Luna, Windows 98/2000 Classic,
ChromeOS and Y2K / Frutiger Aero. These are original XFCE interpretations;
they do not reproduce proprietary OS assets, trademarks or logos.

## Current baseline (2 November 2026)

- macOS Aurora Night/Day/Aqua, Windows 7 Aero and Windows 10 Ten remain the
  existing installable families. Unfinished Liquid Glass styles and Windows 11
  are **not** in the planned set.
- `main` already coordinates Plank, MacBar and Windows shells, has delayed
  XFCE login reconciliation, and handles the MacBar `GApplication` quit path.
  Every future rice must use this switching/recovery foundation, not launch a
  second competing panel or mutate Plank autostart on its own.
- Four GTK3 previews are intentionally *read-only*. Launcher, sample app
  search, task buttons and sample file manager work inside a temporary dialog.
  They do not call `rice.apply`, run commands or change user settings.

## Style studies

| Family | Identity | Prototype interaction | Biggest implementation risk |
| --- | --- | --- | --- |
| Windows XP Luna | Blue Luna taskbar, green Start, friendly meadow, rounded titlebars | Start search, task buttons, file manager mock window | Original themed assets without copyrighted XP resources |
| Windows 98 / 2000 | Teal desktop, high-density gray controls, square windows | Classic launcher, sample app list, file manager | Keyboard navigation with tiny visual density |
| ChromeOS | Pastel background, centered app drawer, light bottom shelf | App search, shelf buttons, sample file manager | XFCE workspace/panel integration without extra daemons |
| Y2K / Frutiger Aero | Bright turquoise glass, nature-inspired wallpaper, playful dock | App search, aqua taskbar, sample file manager | Glass appearance at low compositor capability and without expensive blur |

## Development roadmap

### P0 — Design validation (current)

- [x] Include the four families in RiceHub Discover as **Prototype only**.
- [x] Create a distinct themed GTK3 teaser for each family.
- [x] Provide an interactive, no-write desktop preview with launcher, search,
  empty-results state, sample file-manager window and task buttons.
- [x] Keep the four families absent from `STYLES`, CLI apply and backup manifests.
- [ ] Review each prototype's visual balance and keyboard/focus on real Mint XFCE.
- [ ] Collect feedback on density, icon style, taskbar behavior and wallpapers.

### P1 — Shared desktop shell foundation

- [ ] Extract *proven* reusable behavior from Ten/Aero shells: application
  discovery, task switching, tray, desktop workarea and launch-safe actions.
- [ ] Retain the single session coordinator for Plank, MacBar, Aero/Ten and
  future shells. Make transitions reversible and idempotent after relogin.
- [ ] Add preflight diagnostics for X11, XFCE, Wnck, icon themes and compositor.
- [ ] Benchmark launch time, idle PSS and CPU on Mint XFCE before adding effects.

### P2 — Installable XP and Classic candidates

- [ ] Package wholly original GTK3, XFWM4, icon, cursor and wallpaper artwork.
- [ ] Implement genuine Gio launchers and event-driven Wnck window buttons.
- [ ] Support keyboard search, Escape and focus dismissal, tray coexistence,
  Show Desktop, multi-monitor positioning and accessibility labels.
- [ ] Add explicit plan/apply/restore with snapshot and failure rollback.
- [ ] Capture real GTK/X11 screenshots, run isolated virtual-session smoke and
  conduct physical Mint XFCE login/apply/restore tests.

### P3 — Installable ChromeOS and Y2K candidates

- [ ] Build the shelf/app drawer and aqua taskbar on the shared shell backend.
- [ ] Provide a flat/low-effects fallback; no dependency on blur or shaders.
- [ ] Ensure the four new rices never fight Plank or the managed session panel.
- [ ] Repeat restore, update, relogin, screen-size and low-memory validation.

### Release gate

An entry becomes **Installable** only after `plan` has no side effects; `apply`
has recovery snapshots and full failure handling; `restore` reliably returns
the previous active rice; shell switching survives logout/reboot; keyboard
and real task switching work; desktop changes are verified on supported
Mint XFCE/X11 hardware; and original-artwork licensing is checked.

No estimated date or claim of completion is attached to P1–P3 yet.

## Try the four prototypes

Open `ricehub` → **Discover rices** → choose a family → **Explore desktop
prototype**. The new designs have *no Apply button*. The sample windows and
apps show what a full shell could look and feel like; nothing launches.
