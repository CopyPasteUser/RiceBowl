# Windows 10 · Native fidelity roadmap

The Windows 10 rice is an original Linux/XFCE interpretation of the **Windows
10 22H2 desktop**, not Windows 7 Aero, Windows 11, or a cosmetic preview.
It must remain recognizably Windows 10 even with the wallpaper hidden.

## Seven acceptance gates

- [ ] 1. **Reference and baseline:** audit the live GTK shell, dark/light GTK,
  XFWM, icons, taskbar, real system hooks and 1600×900 screenshot against
  period-appropriate Windows 10 Start, taskbar, Action Center and Explorer.
- [ ] 2. **Art and window surfaces:** replace the oversized mascot wallpaper
  with an original Windows-10-inspired blue four-pane light composition; refine
  the square XFWM titlebar buttons and complementary GTK/Thunar dark/light styles.
- [ ] 3. **Taskbar:** 40px flat charcoal bar, compact four-pane Linux Start mark,
  usable search, tight pinned/running app states, correctly labelled live tray,
  two-line date/time and right-edge desktop reveal.
- [ ] 4. **Start:** genuine three-zone rail / alphabetical real-app list / pinned
  tile groups, realistic Windows 10 proportions, productive default tiles from
  installed apps, search, context pinning, user paths, settings and logout.
- [ ] 5. **Action Center:** right-anchored tall panel with truthful notifications
  scope, real settings launchers, disabled missing tools, status from Linux,
  verified volume/mute controls and accessible focus/keyboard dismissal.
- [ ] 6. **Regression:** native GTK/Xvfb smoke, 1600×900 plus 1024×768 layout,
  focused unit tests, all seven rices' regression and safe upgrade/restore of
  existing user-local Ten assets.
- [ ] 7. **Documentation and GitHub:** update `DESIGN.md`, `README.md`,
  `CHANGELOG.md`, publish only the newest real X11 screenshots, CI green and
  merge implementation into `main` without moving the existing v0.9.1 tag.

## Design boundaries

- Use original RiceBowl artwork, not copyrighted Microsoft binaries/icons.
- Shell is GTK3/X11; menus discover genuine `Gio.AppInfo` applications and
  system actions use installed XFCE tools. Do not paint fake toggled states.
- The existing `macrice/aero_shell.py` owns native task/window/session behavior.
  Windows 10 rendering is isolated in `macrice/ten_shell.py` and scoped CSS.
- Retain independent identities for Windows 7, XP, Classic, Frutiger, ChromeOS
  and macOS. Preserve the backed-up, conflict-checked asset upgrade workflow.

## Visual references

- [Microsoft Support — Customize the Windows Start menu](https://support.microsoft.com/en-us/windows/experience/personalization/customize-the-windows-start-menu)
- [Microsoft Support — Customize the taskbar](https://support.microsoft.com/en-us/windows/experience/personalization/customize-the-taskbar-in-windows)
- [Microsoft Support — Personalize colors](https://support.microsoft.com/en-us/windows/experience/personalization/personalize-your-colors-in-windows)

These references inform the interaction and silhouette; the bundled assets
are independently drawn, Linux-specific, and do not imply Microsoft branding.
