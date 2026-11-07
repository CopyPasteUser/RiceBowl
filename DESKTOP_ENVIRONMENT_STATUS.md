# RiceBowl Desktop Environment — implementation status

**As of 7 November 2026 · Experimental, opt-in · Not ready for 1.0**

RiceBowl's target is a lightweight **floating Wayland desktop based on upstream
labwc**, with a reusable recipe engine capable of distinct OS-inspired designs
and AI-assisted original desktop mockups. The proven XFCE/X11 rices remain the
supported default. New Wayland services must not silently replace XFCE or
modify global session settings.

## What really works

| Component | Verified implementation | Important gap |
| --- | --- | --- |
| Session / compositor | Opt-in labwc session, nested preview, Waybar fallback, startup supervision and cleanup | Physical login/relogin, recovery and power-use acceptance |
| RicePlate panel | Native Rust layer-shell, per-output panels, window discovery and grouped task activation, launcher, menu, calendar, keyboard task navigation, compact layouts | Native StatusNotifier tray; full accessibility and real-world focus QA |
| Desktop shortcuts | Schema-v5 native shortcut surfaces, drag repositioning, owner-private **per-named-output positions**, independent multi-output reflow, hotplug, Tab/Shift-Tab | Cross-monitor drag semantics, output identity without stable names and mixed-DPI/device tests |
| Wallpaper / appearances | Original bundled wallpapers, composable panel groups, labels, gaps, tokens, original example rices | Full desktop widgets, rich layout primitives, complete cross-app window decorations |
| Hardware indicators | Kernel-backed battery; NetworkManager connectivity and WirePlumber sink status on a bounded worker | Device picker, Bluetooth status, event subscriptions and finer status detail |
| RiceSpice controls | Allowlisted native-menu Wi-Fi toggle, volume ±5%, mute; asynchronous result feedback | Full settings for displays, input, network, audio, Bluetooth, accessibility, time and power |
| RicePop notifications | On-demand `de notifications --json` reads active/history entries from the existing Mako host | Native notification center, OSD, interaction/history UI, non-Mako backends |
| Session safety | Opt-in session, user polkit agent when installed, optional Mako/swayidle/swaylock, compositor exit cleanup | Complete suspend/resume and hardware recovery acceptance |
| Creator authoring | Schema-v1–v5 validation, offline private draft edits, component catalog and API inventory, nested native render/capture and visual comparisons | Broad desktop composition, complete action/state bindings, high-fidelity mockup conversion |
| RicePack exchange | Deterministic v2 recipe archives, SHA-256-pinned bundled wallpaper, provenance and v1 read compatibility; explicit next-login staging and one-level rollback | Packaged external assets, multi-component live apply and transactional active-session rollback |

**Native here means running in the experimental labwc session**, not the
existing Python/GTK XFCE experience. A declarative menu/indicator is not a
working settings page. The network/audio *status labels* are intentionally
non-clickable; the separate validated native-menu actions perform changes.

## Implementation boundaries

- **labwc** owns floating windows and compositing. RiceBowl does not fork it.
- **RicePlate** is the resident native Rust shell renderer; one process renders
  all panels, popups and supported desktop shortcut surfaces.
- **RiceSpice** delegates ordinary controls to NetworkManager and WirePlumber
  through fixed arguments. No custom recipe commands or privileged daemon.
- **RicePop** currently delegates delivery to the installed Mako host and only
  reads its history on request; it does not own the notification bus name.
- **Creator** is optional, on demand and offline. It never needs a model at
  runtime and must require an explicit user choice before an active desktop
  change. Current stage/rollback affects the *next* opt-in login only.
- **Waybar** remains an intentionally supported recovery/fallback panel.

## Inspect or try without replacing XFCE

```bash
ricebowl de check --json
ricebowl de catalog --json
ricebowl de creator-api --json

# Explicit nested preview; native binary and labwc prerequisites required:
ricebowl de start --nested --panel native

# Optional example with real Wi-Fi/audio quick actions; import never applies it:
ricebowl de recipe-import --recipe "$PWD/examples/wayland/quick-controls.json"
ricebowl de start --nested --panel native --recipe quick-controls

# Only inside a Wayland session with the Mako notification host:
ricebowl de notifications --json
```

Wi-Fi toggling can disconnect the current session. Notification JSON may
contain private messages. The nested preview does not change your current
desktop. See [Wayland preview instructions](WAYLAND_SESSION.md) for detailed
dependencies, screen captures and rollback behavior.

## Verification and 1.0 gates

The latest code merged through [PR #141](https://github.com/CopyPasteUser/Ricebowl/pull/141).
Local automated suites most recently passed **897 Python tests** (16 skipped
for session/hardware constraints) and **51 native Rust tests** on the relevant
native-change milestone. GitHub's `Tests`, `Native RicePlate prototype` and
`Wayland session preview` workflows passed on the latest native/notification
changes. Native CI renders actual screenshots under headless labwc, including
two-output icon/menu/calendar hotplug coverage; this is *not* physical device
signoff, a performance benchmark or proof of historical-OS visual fidelity.

The next substantial release gates, in recommended order:

1. Real native SNI tray, correct item ownership/actions and per-output focus;
   complete panel keyboard/accessibility behavior.
2. Reusable native RiceSpice settings pages with hardware service adapters,
   device selectors, permission handling and recovery, including suspend/lock.
3. RicePop notification presentation, OSD and a usable history interface
   without a duplicate owner or private-message replay.
4. Complete safe RicePacks with licensed asset manifests, broader composition,
   reproducible visual/functional QA and **explicit transactional live
   apply/restore** across all affected components.
5. Actual multi-monitor/mixed-DPI/input/assistive QA on Linux Mint and
   representative Wayland setups; measure idle PSS/RSS/CPU and launch time.

Detailed tasks and gate conditions live in
[the canonical Wayland DE roadmap](RICEBOWL_DE_ROADMAP.md). Do not call the
desktop 1.0 until those functional and physical gates are met.
