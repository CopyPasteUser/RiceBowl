# ChromeOS · Native Material You fidelity roadmap

This is an original XFCE/X11 desktop inspired by current ChromeOS. It is a
Linux application, not ChromeOS or a Chromium fork. All controls launch real
Linux applications or act on verified device state; no Google binaries or
pretend connectivity toggles are included.

## Seven acceptance gates

- [ ] 1. **Baseline and references:** audit the native ChromeOS shell and
  1600×900 Xvfb screenshots against the modern launcher, shelf, system tray and
  Quick Settings; keep the existing identity distinct from macOS and Windows.
- [ ] 2. **Original visual assets:** build a ChromeOS-like *original* Material
  You wallpaper, rounded 3D-aware XFWM button states, coordinated GTK3/Thunar
  controls and material blue/lavender icon surfaces.
- [ ] 3. **Shelf:** lightweight 56px shell, consistent circle app icons with
  real running-window indicator, proper launcher mark, stable centered app row,
  truthful network/audio/battery pill and reachable show-desktop command.
- [ ] 4. **Launcher:** compact rounded bottom-left panel with actual installed
  Gio applications, icon grid and bounded scroll, search, favorites, keyboard
  focus, real settings action and pin/unpin context menus. No mock apps.
- [ ] 5. **Quick Settings:** native bottom-right Material You panel with an
  accessible clock/date header, truthful network/Bluetooth/settings actions,
  verified volume/mute, battery status, disabled missing utilities and Escape.
- [ ] 6. **Regression and safety:** ensure popup bounds at 1600×900 and
  1024×768, Xvfb smoke and all-rice test suite, backup-backed upgrade of
  byte-identical historical Chrome assets, no changes to other selected Rices.
- [ ] 7. **Release:** current-only real screenshots from the same green CI run,
  English README/design/changelog updates, GitHub PR and merge to `main`.
  Preserve the existing historical `v0.9.1` release tag.

## Reference principles

- Modern ChromeOS uses a Launcher for search/apps and an independently
  configurable, pinnable shelf. See Google Chromebook Help:
  [Launcher](https://support.google.com/chromebook/answer/15470775?hl=en),
  [Shelf](https://support.google.com/chromebook/answer/3113576?hl=en) and
  [Find & organize apps](https://support.google.com/chromebook/answer/6206362?hl=en).
- Materials: muted lavender `#e7e9f8`, warm-white `#f9f9ff`, ink `#262a40`,
  iris accent `#4b66d7`, clear elevated surfaces and gently curved corners.
- The shell remains GTK3; CSS themes live in the existing per-Rice contract.
  Use Pillow only as a **development-time** art generator (no runtime cost).
- Document differences honestly: notifications belong to XFCE, unavailable
  wireless controls are navigation actions, and no Chromebook-only Android or
  Google services are emulated.
