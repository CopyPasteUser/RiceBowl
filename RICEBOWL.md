# RiceBowl · Project identity and compatibility

RiceBowl 0.9.0 is the public-facing successor to RiceHub 0.6. It manages seven reversible XFCE/X11 desktop families, including the unchanged macOS implementation.

## Highlights

- Distinct native control panels for Windows XP, Windows 98/2000, ChromeOS, and Frutiger Aero, plus the existing Aero 7 and Windows 10 settings surfaces.
- Profile-specific, scoped Thunar GTK styling and safer migration from legacy 0.6 CSS blocks.
- Original scalable rice-bowl application mark and a new user-local ricebowl launcher.
- Existing ricehub and macrice commands, settings, D-Bus application IDs, shortcuts, internal theme names and backups remain compatible.

## 0.9 — Reference-driven native UI

This release implements the actual code for the four user-selected mockup directions, not screenshots as substitutes for software. XP Luna, Classic 98/2000, ChromeOS and Frutiger Aero have distinct menu structures, taskbar styling, functional volume/mute controls and differentiated Thunar GTK chrome. Thirty-six further icons cover named folders, desktop, disk and network. The reference images include custom file-manager layouts that stock Thunar does not implement; RiceBowl keeps the real Thunar application and skins only its supported GTK controls. Physical Mint acceptance is pending.

## 0.8 design and recovery additions

- Seven reversible desktop families; six non-macOS styles now have unique original app/places icons and profile-specific status artwork.
- ChromeOS uses a centered launcher; Frutiger Aero uses a distinct organic dashboard; Aero 7, Ten, Luna and Classic retain their own taskbar, menus and control surfaces.
- Battery, Wi-Fi/Ethernet and audio indicators are driven by real Linux status; missing or unknown values are never presented as successful actions.
- Official previous themes are migrated with full backups; customized themes remain protected. Select **Repair local theme assets…** or run `macrice rice repair-assets ten-dark` for a deliberate, backed-up replacement.
- Implementation details and acceptance checks: [0.8.0 engineering roadmap](RELEASE_0_8_0_ROADMAP.md). Physical Mint acceptance remains pending.

## Installation and upgrade

Clone https://github.com/CopyPasteUser/RiceBowl.git (the canonical repository name), then run the user-local installer: bash install.sh --dry-run; bash install.sh. Start the application with ricebowl. No sudo is needed and the installer does not apply a rice or terminate your existing panel. Use macrice rice restore to revert an applied theme.

See README.md for details, CHANGELOG.md for version history, RICEHUB.md for architecture and rollback notes.

Hardware validation of Mint XFCE switching, Plank coexistence, compositing and multi-monitor behavior is still pending. Old README screenshots document earlier releases, not a new 0.7 image capture.

## Source and project identity

The Python distribution is `ricebowl-xfce` (version 0.9.0); the GTK hub uses the RiceBowl name and rice-bowl icon. Existing user-controlled appearance and backup identifiers are not renamed automatically. The former `ricehub` command and historical documentation stay available solely for migration.
