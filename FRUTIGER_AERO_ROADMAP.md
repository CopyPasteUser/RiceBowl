# Frutiger Aero · Aqua World fidelity roadmap

Objective: bring the **actual installed Linux/XFCE GTK3 Frutiger Aero rice** close
to the selected Y2K mockup, rather than producing another static illustration.
The original water/sky/grass desktop and every functional Linux integration stay
intact. The Windows 7, XP, Classic, ChromeOS, Ten and macOS styles are outside
this visual change. Original art only; do not bundle third-party assets.

## Reference and design direction

- User-selected mockup: a luminous aqua launcher, nature/water desktop, glossy
  taskbar and coordinated icons; three functional **Apps / Places / Settings**
  views. Prior feedback specifically requested a larger application icon grid.
- [Consumer Aesthetics Research Institute — Frutiger Aero](https://cari.institute/aesthetics/frutiger-aero):
  glossy interface materials, humanist type, translucent surfaces, nature and
  a mid-2000s sense of technological optimism. This is research, not an asset
  source.
- Source of truth: `macrice/heritage_shell.py` for live Frutiger shell styles;
  `macrice/aero_shell.py` for native GTK structure/behavior;
  `scripts/build_heritage_assets.py` for original XFWM/GTK art;
  `macrice/rice.py` and `macrice/shell_session.py` for safe desktop transitions.

## Seven delivery steps

1. **[x] Freeze behavior and identify visual drift.** Preserve actual Gio app
   launching, pin management, Wnck task switching, hardware reporting, keyboard
   shortcuts and seven-style apply/restore. Capture the current Xvfb baseline.
2. **[x] Establish a signature Aqua material.** Distinct deep-water cyan, lime,
   pearlescent white, refraction-like highlights, controlled edge light and
   visible keyboard focus. Avoid Windows 7's dark cobalt steel glass.
3. **[x] Rebuild the native launcher composition.** Refine `Your World` header,
   glossy quick links, segmented Apps/Places/Settings and a two/three-column
   icon-first application grid with honest empty state and Show more. Search,
   context pinning, keyboard navigation and installed-program launching remain
   functional at 1600×900 and 1024×768.
4. **[x] Give the taskbar a dedicated Y2K silhouette.** Aqua lens Start orb,
   refractive task/pin capsules, distinct active/hover treatment and a compact
   notification cluster. No fake status or additional background services.
5. **[x] Complete window and application materials.** Upgrade only Frutiger
   XFWM title/buttons and GTK/Thunar controls. Keep the art generator scoped and
   deterministic, with old managed assets upgradeable and custom user files
   protected by RiceBowl's asset conflict checks.
6. **[x] Audit accessibility, performance and safety.** Keyboard focus,
   disabled tools, readable contrast, click targets, no clipped menu, no
   startup/background process regression, no cross-rice style leakage, safe
   restore and narrowly scoped changes.
7. **[x] Capture and release the implemented result.** Run Python tests,
   syntax and asset checks and native Xvfb screenshots; inspect them visually;
   update only the current screenshots and the English README/Design guide;
   merge into GitHub `main` after green CI. Owner's physical Mint XFCE
   acceptance remains separate.

## Product acceptance criteria

### Follow-up: Pearl Glass and native Thunar refinement (3 November 2026)

- **[x] Launcher relevance:** the initial native Gio grid is ordered by saved
  pins, then installed file manager/browser/terminal, then other programs.
  Search still covers every visible app; context pin menus still work.
- **[x] Better visual hierarchy:** the top hero, shortcut row, navigation
  tabs, Discover caption, app tiles and footer now use distinct pearl, mint,
  lagoon and lime treatments instead of one continuous turquoise gradient.
- **[x] Real folder behavior:** XDG-aware user folders and explicit creation
  confirmation remove hardcoded English folder paths and disabled shortcuts.
- **[x] Usable device controls:** Frutiger-only hero, larger readable captions,
  real status readings, volume and mute share the existing verified backend.
- **[x] Actual file-manager controls:** `FRUTIGER_EXPLORER_CSS` styles real
  Thunar widgets with a continuous breadcrumb surface, compact toolbar,
  pale-green navigation sidebar, white file canvas and subdued lime states.
  Replacing Thunar's *structure* remains a separate optional RiceExplorer
  project, never a fake GTK overlay.
- **[x] Recoverable installation:** the exact existing Frutiger GTK asset hash
  is in `trusted-ricebowl-frutiger-aqua-091.json`; historical managed Thunar
  blocks migrate, whereas modified/user-owned GTK CSS remains untouched.
- **[x] Automated QA:** unit and CSS parser tests, all-rice smoke capture and
  a new 1024×768 *actual Thunar* acceptance capture in isolated Xvfb.
  Owner's physical Mint/XFCE test is still required.


- Frutiger is recognizable without blur/compositor effects or a mocked panel.
- All three menu pages display real content and work with mouse and keyboard.
- App icons, titlebar, Thunar and taskbar read as one cohesive eco-glass family.
- All other six rice presets and their status/backup behavior are unchanged.
- No release tag is moved without explicit versioning decision. CI evidence
  does not claim hardware verification on the user's ThinkPad.
