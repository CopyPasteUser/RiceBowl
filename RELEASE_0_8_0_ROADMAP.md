# RiceBowl 0.8.0 — Quality and Identity Release

This milestone addresses reported failures on a real Linux Mint XFCE laptop. **No macOS profile redesign.** Implementation is staged behind the existing reversible XFCE session engine.

| Priority | Workstream | Acceptance criteria |
| --- | --- | --- |
| P0 | Safe theme upgrades | Existing unchanged 0.6/0.7 assets recognized by trusted Git hashes and upgraded with backup. Unrecognized edits are blocked, with an explicit repair action that always preserves originals; reject symlinks/unmanaged paths. |
| P0 | Real taskbar status | Battery from sysfs (AC-only and multi-battery safe), Wi-Fi vs Ethernet based on current routing, audio from wpctl/pactl with timeouts, distinct tray visuals and accurate tooltips; no fake states. |
| P1 | Distinctive identities | Six non-macOS rice profiles use different handcrafted folder/file-manager/settings/browser/icon art, launcher structure and per-profile taskbar controls; no duplicated placeholder SVGs. |
| P1 | User experience | ChromeOS launcher differs structurally from Windows 10; XP and Classic keep appropriate menu hierarchy; responsive taskbar and controls, keyboard navigation and error states. |
| P0 | Regression / publication | Pure-Python tests for migration and status edge cases, GTK virtual-X11 smoke/capture, tests for SVG uniqueness and reversible switching; README/CHANGELOG updated and tagged 0.8.0 release only after green CI. |

## Design language

- **Windows 7 Aero:** glass blue, silver highlights, circular start button, compact notification area.
- **Windows 10:** square geometry, flat dark/light tiles, sharp accent, modern Action Center.
- **Windows XP Luna:** saturated blue beveled surfaces, green Start, warm yellow folders, categorical controls.
- **Windows 98/2000 Classic:** hard square borders, pixel motifs, monochrome beige/gray, pressed controls.
- **ChromeOS:** spacious rounded shelf, centered launcher and pill-style device cluster, primary colors.
- **Frutiger Aero:** luminous aqua/green, bubbles, reflective highlights and organic rounded edges.

## Rollout / recovery

Update user-local installation with `bash install.sh` without sudo. Applying a rice remains opt-in. Historical assets are migrated with backups, never overwritten without provenance or explicit user repair. `macrice rice restore` restores desktop settings. Hardware acceptance requires Mint XFCE tests for battery, Wi-Fi, Plank autostart, multiple monitors and switching repeatedly.
