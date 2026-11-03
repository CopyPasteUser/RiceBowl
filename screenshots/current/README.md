# Current RiceBowl screenshot gallery

Only the last verified **actual** virtual-X11 captures are retained in this directory.
Each `*-start.webp`, `*-controls.webp` and `*-workspace.webp` image was captured
from one successful Linux/Xvfb GitHub Actions run of the
`review/cross-rice-fidelity-20261103` branch on 3 November 2026
(workflow run `41666644729`, source `c3406bc572f6f314d3acacb1f5572c6b08c5508d`).
Images are WebP-optimized from the **1600×900** screenshots; the original
uncompressed PNGs remain in that CI run's screenshot artifact.

The 3 November second-pass Windows 7 Control Panel/Superbar code is **newer**
than `aero-start.webp`, `aero-controls.webp` and `aero-workspace.webp`. These
images are historical for that rice until a new green native XFWM4 capture
is inspected and checked in. The other five non-macOS rices are unchanged.

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
