# Current RiceBowl screenshot gallery

Only the latest verified **actual** virtual-X11 captures are retained in this directory.
All are WebP-optimized from genuine **1600×900** GTK/XFWM4 captures, not mockups.

Capture provenance (3 November 2026):

- **Windows 7 Aero workspace (`aero-workspace.webp`)**: passing native
  XFWM4/Thunar GitHub Actions run
  [`41685514010`](https://github.com/CopyPasteUser/RiceBowl/actions/runs/41685514010),
  branch `feat/win7-explorer-fidelity`, source
  `b600b96c179c1caf33868441d082c1269540c935`. This shows the **new**
  Seven Explorer Thunar CSS and MIME-icon refinements.
- **Windows 7 Aero Start and Control Panel (`aero-start.webp`,
  `aero-controls.webp`)**: passing GitHub Actions run
  [`41678284256`](https://github.com/CopyPasteUser/RiceBowl/actions/runs/41678284256),
  branch `feat/win7-fidelity-round2`, source
  `6bb1b6d0c6546a698efdc8207da7394941b4ecd7`. This includes the actual
  48px Superbar, new category Control Panel and all eight original Aero icons.
- **Windows 10, XP, Classic 98, ChromeOS and Frutiger**: passing Actions run
  [`41666644729`](https://github.com/CopyPasteUser/RiceBowl/actions/runs/41666644729),
  source `c3406bc572f6f314d3acacb1f5572c6b08c5508d`.

Uncompressed PNG sources, including the 1024×768 tests, remain in their
respective CI run artifacts. The other five rices were not cosmetically changed
by the Windows 7 review.

The `workspace` images display a real Thunar process under a real XFWM4 window
manager, using the same GTK/icon theme and Thunar view preferences that RiceBowl
applies. It opens a disposable folder with five sample directories and a text
file; no user's files or desktop settings are read or changed for capture.
These images are neither mockups nor proof of physical Linux Mint hardware
acceptance. The `macOS` rice is intentionally absent: its MacBar/Plank composite
has not yet been freshly captured under an equivalent test. Stale images remain
recoverable from Git history, not in the current gallery.

CI also verifies **1024×768** Start and settings capture for XP Luna, Windows 7,
Frutiger Aero, Classic 98, Windows 10 and ChromeOS; the compact test screenshots
remain CI artifacts rather than duplicates in this gallery.
