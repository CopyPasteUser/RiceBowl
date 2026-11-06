# RiceBowl DE — Wayland/labwc transition

**Status (November 2026): opt-in labwc session preview implemented;
physical acceptance outstanding.** RiceBowl 0.9.x is still an XFCE/X11
rice manager. The separate Wayland login-session package requires explicit
installation and is not yet a finished desktop environment.

## The product

RiceBowl will be a lightweight, modular **floating** desktop environment on
Wayland. We use upstream [labwc](https://labwc.github.io/) as the compositor,
not a RiceBowl compositor fork. Each rice may substantially change the layout,
controls, wallpaper, icons, window chrome and behavior of our own components.
Running third-party GTK/Qt apps cannot be forced into arbitrary client-side
window decorations; use supported platform theming and preserve functionality.

## Desktop creation as a first-class workflow

**North star:** the same lightweight functional desktop core must make it easy
to build both a convincing OS-inspired rice and a completely new rice from an
AI-generated UI mockup. Authors should spend most of their time defining the
experience, not writing another shell, panel, device backend or window manager.

A rice is **more than a color theme**: it can choose and arrange shell
components, navigation, menus, panels, desktop behavior, widgets, typography,
artwork, transitions and available interactions. Shared RiceBowl components
supply the real Linux behavior, state and recovery underneath.

The intended authoring path is:

1. Analyze a screenshot/mockup into regions, components, visual tokens,
   responsive rules, interactive states and required Linux capabilities.
2. Map it to reusable primitives and a **versioned declarative rice recipe**
   with original or properly licensed assets. Extend the shared primitives
   when necessary, rather than cloning the entire shell.
3. Preview the full shell at multiple sizes, inspect differences and test
   keyboard/focus, accessibility, live controls and real application windows.
4. Validate and import the rice safely, then apply/switch/restore without
   overwriting personal desktop settings.

An AI agent may assist with steps 1–2, but **RiceBowl itself must not require
AI inference or an online service**. Arbitrary images are not promised to
become fully functional one-click conversions; unfamiliar controls require
explicitly implemented behavior. Packs must never execute arbitrary generated
scripts. Third-party GTK/Qt application decorations and Wayland protocol
limits remain real constraints on cross-app fidelity.

### Repository and process ownership

| Owner | Responsibility | Boundary |
| --- | --- | --- |
| RiceBowl / RiceSession | Login session, startup, shutdown, recovery | A Wayland path separate from the current XFCE session |
| RiceBowl / RicePlate | Desktop icons, wallpaper, panels, menus, taskbar | One active shell; no competing XFDesktop process under Wayland |
| RiceBowl / RiceSpice | Settings, quick actions, hardware state | Reuse NetworkManager, BlueZ, PipeWire, UPower and logind |
| RiceBowl / RicePop | Notifications, OSD and optional history | One notification owner, no redundant daemon |
| RiceBowl / RicePack | Appearance profiles and UI layout contracts | Validated config, no arbitrary third-party code execution |
| [RiceField](https://github.com/CopyPasteUser/Ricefield) | Independent Rust file manager | 1.0 hardware sign-off before replacing Thunar by choice |
| [Taskotto](https://github.com/CopyPasteUser/Taskotto) | Independent Rust process manager | Separate optional app, currently planning only |
| labwc, XWayland, portals | Compositing, legacy apps and sandbox integration | Upstream dependencies, not new RiceBowl repositories |

The current `macrice/` namespace and commands remain for upgrade/rollback
compatibility. New desktop-environment code starts in an isolated `macrice/de/`
namespace and must not silently call XFCE-specific paths.

## Delivery gates

### 0 — Prep and non-invasive diagnostics

- [x] Choose labwc as the Wayland floating compositor without forking.
- [x] Retain RicePlate, RiceSpice and RicePop in the main repo.
- [x] Keep RiceField and Taskotto as independent applications.
- [x] Add an environment-only `ricebowl de check` preflight.
- [x] Keep the historical XFCE path working with existing automated tests.
- [ ] Establish measured X11 baseline on real hardware; no guessed RAM claims.

**Done when:** the preflight detects missing prerequisites without starting,
installing, replacing or disabling anything; unit and installer tests pass.

### 1 — Optional labwc login session

- [x] Add a versioned RiceSession lifecycle with a supervised temporary native
  Waybar shell, explicit exit, crash termination and ordinary session logs.
- [x] Provide a separately built **opt-in** Debian session entry package.
- [x] Launch labwc through bundled `--config-dir`, preserving the user's
  own labwc files and XFCE preferences.
- [x] Add Mint 22 / labwc 0.7.1-compatible D-Bus activation import and a
  RiceBowl-specific systemd user target; nested sessions do neither.
- [x] Package RiceBowl-specific wlroots/GTK portal selection, XWayland
  dependency recommendation, lock/launcher keybindings and optional agents.
- [x] Keep the XFCE/X11 login path independently available and provide
  explicit package removal and failure recovery instructions.
- [ ] Validate actual login-manager discovery, compositor boot, XWayland,
  portal screencast/file picker, polkit, input methods, clipboard, lock and
  multi-monitor behavior on physical Mint hardware.

**Done when:** the [device acceptance checklist](WAYLAND_SESSION.md) proves
that users can enter and leave the opt-in RiceBowl labwc session without
affecting XFCE, including a failed-session recovery. **Not yet signed off.**

### 2 — RicePlate Wayland shell

- [x] Establish a non-executable versioned panel-layout recipe and an isolated,
  temporary Waybar adapter with two distinct compositional layouts; validate
  custom manifests and clean up generated session files. This is a stepping
  stone, **not** the native RicePlate renderer.
- [x] Introduce an **opt-in native Rust layer-shell surface prototype** with
  software rendering, a visible fixed-action launcher and event-driven idle.
  It is independently testable and does not replace Waybar until parity.
- [x] Add experimental protocol-backed native window discovery and activation
  with bounded task labels and click hit-testing; full taskbar parity remains
  open (grouping, minimize, outputs, keyboard interactions).
- [x] Consume the two bundled schema-v1 panel recipes from native Rust for
  geometry, placement and visual tokens, without pretending unimplemented
  system indicators are functional native widgets.
- [x] Add a real local-time clock with minute-boundary event-loop wakeups,
  non-clickable until a calendar exists, plus activate/minimize task clicks.
  A complete taskbar (grouping, tray, keyboard controls) remains outstanding.
- [x] Support owner-private, bounded custom schema-v1 JSON recipes in native
  RicePlate, and position implemented widgets from ordered start/center/end
  sections with matching hit testing and small-display overflow behavior.
  Full arbitrary mockup conversion and missing widget backends remain open.
- [x] Provide a CLI-only opt-in to run native RicePlate as the single panel in
  an isolated labwc session, and restore Waybar on failed native start/crash.
  Explicit shutdown does not restart the fallback. The login-manager default
  remains Waybar while native functional parity is incomplete.
- [ ] Build a Wayland-native panel through `wlr-layer-shell`.
- [ ] Populate tasks/windows through a supported foreign-toplevel protocol.
- [ ] Implement launchers, task groups, tray, calendar, menus and keyboard
  navigation; avoid invisible or fake controls.
- [ ] Expose reusable, composable shell primitives and stable interaction/state
  bindings so substantially different rice layouts share core behavior.
- [ ] Render wallpapers and desktop icons with correct layer, focus, hit tests,
  drag/drop, multimonitor geometry and hotplug behavior.
- [ ] Support one selected rice at a time and restore the previous shell if a
  switch fails.

**Done when:** the desktop remains functional without xfdesktop or xfce4-panel.

### 3 — RiceSpice and RicePop

- [ ] Implement usable native settings for screens, input, network, audio,
  Bluetooth, accessibility, power, timezone and user preferences.
- [ ] Delegate privileged actions to polkit/system services; never add a
  privileged always-on RiceBowl daemon by default.
- [ ] Provide consistent quick actions, notifications, OSD and history,
  including disabled/error/permission states.
- [ ] Integrate a secure lock screen, idle policy and suspend/resume.

**Done when:** common desktop settings and recovery workflows no longer
depend on the XFCE session.

### 4 — The Rice ecosystem

- [ ] Define a small versioned profile contract between RiceBowl, RiceField
  and Taskotto. External applications work without RiceBowl installed.
- [ ] Support rice-specific structure, spacing, colors and components with
  validated settings, not an unsafe arbitrary runtime plugin mechanism.
- [ ] Specify a versioned, schema-validated rice recipe format for composable
  panel, menu, desktop, widget and settings layouts, visual tokens, assets,
  responsive behavior and explicit supported system-action bindings.
- [ ] Provide a documented mockup-to-rice authoring workflow, editable
  templates, isolated preview and safe pack import/export. An AI-generated
  reference must be usable without any required AI/cloud runtime.
- [ ] Validate malformed/oversized recipes, missing assets, unsupported
  widgets/actions, keyboard/focus semantics and rollback before applying.
- [ ] Port all seven styles individually while preserving names, legacy
  backup IDs and original assets.
- [ ] Coordinate RiceField default-file-manager integration after its 1.0
  acceptance. No forced global default application change.

**Done when:** switching a rice consistently updates every supported desktop
component, and incompatible clients degrade gracefully.

**Authoring acceptance (not yet implemented):**

- [ ] Build one high-fidelity existing-OS-inspired rice **through the shared
  recipe/component contract**, without a parallel bespoke shell or duplicate
  hardware backend.
- [ ] Build a second, visually distinct rice from an AI-generated or original
  static mockup using documented steps; record unsupported interactions and
  the code needed for any new reusable primitive.
- [ ] Show install, preview, multi-resolution real-shell captures,
  application-window interaction, keyboard navigation, live system actions,
  switch and rollback for both rices.
- [ ] Confirm the authoring and daily-use path works entirely offline once
  the required packages/assets are present and does not load unused rices.

### 5 — Efficient, testable 1.0

- [x] Add a read-only package/CLI version consistency check and a candidate
  source-artifact gate; do not publish stable 1.0 without explicit device QA
  evidence (see `RELEASE_1_0_GATES.md`). Binary packaging remains open.
- [ ] Measure cold start, settled PSS/RSS, CPU wakeups, relogin, long-running
  memory and mixed-DPI behavior for X11 and Wayland on actual devices.
- [ ] Remove redundant processes only after their responsibilities have been
  replaced, with comparison and rollback evidence.
- [ ] Port performance-critical resident components to Rust where profiling
  demonstrates benefit; no speculative full rewrite.
- [ ] Ship reproducible packages, uninstall/rollback, docs, CI and device QA.
- [ ] Test fresh login, corrupted config, missing backend, locked screen,
  sleeping/waking, low-memory and disconnected network cases.
- [ ] Gate 1.0 authoring claims on the two demonstrator rices and validated
  recipe migration, recovery, responsiveness and runtime resource measurements.

**Done when:** RiceBowl is independently installable, fully usable and
recoverable as a desktop environment. RAM targets are measured, not promised.

## Phase 0–1 interface contract

- `macrice de check [--json]` probes installed tools and the current session
  without starting processes, reading private network data or changing files.
- The existing `ricebowl` launcher will forward `de` directly to this CLI
  without changing its default Hub action.
- A successful **tool** preflight does **not** certify a working RiceBowl
  Wayland desktop. The result distinguishes the optional preview login session
  from the unfinished RicePlate/RiceSpice/RicePop environment.
- The Wayland session installer is opt-in, preserves user configuration,
  and has a reversible uninstall and independent XFCE fallback.

## References

- [labwc getting started](https://labwc.github.io/getting-started.html)
- [labwc desktop integration and protocols](https://labwc.github.io/integration.html)
- [XDG Desktop Portal documentation](https://flatpak.github.io/xdg-desktop-portal/docs/)
- [Current XFCE service ownership](XFCE_RESOURCE_BOUNDARIES.md)
- [RicePlate X11 preview and gates](RICEPLATE_DESKTOP_ROADMAP.md)
