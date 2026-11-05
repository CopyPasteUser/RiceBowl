# RiceBowl DE — Wayland/labwc transition

**Status (November 2026): architecture and read-only preflight in progress.**
RiceBowl 0.9.x is still an XFCE/X11 rice manager; the Wayland desktop is not
shipped, installed or enabled by default.

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

- [ ] Add a versioned RiceSession lifecycle contract with explicit startup,
  crash/exit behavior and logs bounded to user-owned paths.
- [ ] Install a Wayland session entry **only by explicit opt-in** after checks.
- [ ] Launch labwc with isolated XDG configuration; do not overwrite the user's
  existing `~/.config/labwc` or global login-manager settings.
- [ ] Integrate D-Bus activation environment and systemd user-session lifecycle.
- [ ] Validate XWayland, portals (screencast/file picker), policy agent,
  input methods, clipboard and legacy applications.
- [ ] Preserve separate selectable XFCE/X11 session and a safe logout path.

**Done when:** a user can log into and out of an opt-in RiceBowl labwc session
without affecting the existing XFCE desktop, including failed-session recovery.

### 2 — RicePlate Wayland shell

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

## Phase 0 interface contract

- `macrice de check [--json]` probes installed tools and the current session
  without starting processes, reading private network data or changing files.
- The existing `ricebowl` launcher will forward `de` directly to this CLI
  without changing its default Hub action.
- A successful **tool** preflight does **not** certify a working RiceBowl
  Wayland desktop. The result explicitly reports that the new shell/session
  implementation is still pending.
- The first Wayland session installer must be opt-in, preserve user config,
  and have a reversible uninstall and independent XFCE fallback.

## References

- [labwc getting started](https://labwc.github.io/getting-started.html)
- [labwc desktop integration and protocols](https://labwc.github.io/integration.html)
- [XDG Desktop Portal documentation](https://flatpak.github.io/xdg-desktop-portal/docs/)
- [Current XFCE service ownership](XFCE_RESOURCE_BOUNDARIES.md)
- [RicePlate X11 preview and gates](RICEPLATE_DESKTOP_ROADMAP.md)
