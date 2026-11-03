# Current RiceBowl screenshot gallery

Only the latest verified **actual** virtual-X11 captures are retained in this directory.
All are WebP-optimized from genuine **1600×900** GTK/XFWM4 captures, not mockups.

Capture provenance (3 November 2026):

- **Windows 7 Aero workspace (`aero-workspace.webp`)**: passing native
  XFWM4/Thunar GitHub Actions run
  [`41686544328`](https://github.com/CopyPasteUser/RiceBowl/actions/runs/41686544328),
  branch `feat/win7-explorer-fidelity`, source
  `3392f0c50a8e134d388cef28a51c3271f6864d7a`. This shows the **new**
  Seven Explorer Thunar CSS and MIME-icon refinements. The same passing run
  also captured a real 1024×768 Thunar workspace in its artifact.
- **Windows 7 Aero Start and Control Panel (`aero-start.webp`,
  `aero-controls.webp`)**: passing GitHub Actions run
  [`41678284256`](https://github.com/CopyPasteUser/RiceBowl/actions/runs/41678284256),
  branch `feat/win7-fidelity-round2`, source
  `6bb1b6d0c6546a698efdc8207da7394941b4ecd7`. This includes the actual
  48px Superbar, new category Control Panel and all eight original Aero icons.
- **Windows XP Luna Start, Control Panel and real XFWM4/Thunar**
  (`winxp-start.webp`, `winxp-controls.webp`, `winxp-workspace.webp`): passing
  GitHub Actions run [`41691336596`](https://github.com/CopyPasteUser/RiceBowl/actions/runs/41691336596),
  source `6e8fea9c6dccf3b03348bca07150205ee8698ea0`. The rebuilt category
  panel, XDG-aware Start links, warm Explorer command bar and exact applied
  three-button XFWM4 layout are represented. The same artifact includes all
  three XP views at **1024×768**, including an actual Thunar process.
- **Windows 10, Classic 98, ChromeOS and Frutiger**: passing Actions run
  [`41666644729`](https://github.com/CopyPasteUser/RiceBowl/actions/runs/41666644729),
  source `c3406bc572f6f314d3acacb1f5572c6b08c5508d`.

Uncompressed PNG sources, including the 1024×768 tests, remain in their
respective CI run artifacts. No other desktop family was cosmetically changed
by the XP review.

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
Windows 7 and XP artifacts additionally include 1024×768 genuine Thunar windows.
