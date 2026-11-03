# Current RiceBowl screenshot gallery

Only the latest **actual** virtual-X11 captures are retained in this directory.
Each `*-start.webp` and `*-controls.webp` image was captured from the same
successful GitHub Actions Linux/Xvfb CI run of the `feature/aero-seven-linux-identity`
branch on 3 November 2026 (workflow run `41611087985`, source `472f7ce6c5d41eca5431dbe4921b20e8e3de43c4`).
Images were lossily optimized to WebP at their original **1600×900** resolution
for a smaller checkout and a fast README preview. The original uncompressed PNG
captures are available in that CI run's screenshot artifact.

These are real GTK3 screenshots from Xvfb, not edited mockups or evidence of
physical Linux Mint hardware acceptance. The `macOS` rice is intentionally absent
from this gallery because no new matching macOS screenshot was generated in the
same CI run; a stale image would misrepresent the current state. Historical
screenshots remain recoverable from Git history, not in the live gallery.

The branch also exercises 1024×768 captures of XP Luna and Windows 7 Aero,
but those compact-resolution test images are CI artifacts rather than gallery
duplicates.
