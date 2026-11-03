# RiceBowl · Project identity and compatibility

RiceBowl 0.7.1 is the public-facing successor to RiceHub 0.6. It manages seven reversible XFCE/X11 desktop families, including the unchanged macOS implementation.

## Highlights

- Distinct native control panels for Windows XP, Windows 98/2000, ChromeOS, and Frutiger Aero, plus the existing Aero 7 and Windows 10 settings surfaces.
- Profile-specific, scoped Thunar GTK styling and safer migration from legacy 0.6 CSS blocks.
- Original scalable rice-bowl application mark and a new user-local ricebowl launcher.
- Existing ricehub and macrice commands, settings, D-Bus application IDs, shortcuts, internal theme names and backups remain compatible.

## Installation and upgrade

Clone https://github.com/CopyPasteUser/RiceHub.git (the repository has not yet been renamed), then run the user-local installer: bash install.sh --dry-run; bash install.sh. Start the application with ricebowl. No sudo is needed and the installer does not apply a rice or terminate your existing panel. Use macrice rice restore to revert an applied theme.

See README.md for details, CHANGELOG.md for version history, RICEHUB.md for architecture and rollback notes.

Hardware validation of Mint XFCE switching, Plank coexistence, compositing and multi-monitor behavior is still pending. Old README screenshots document earlier releases, not a new 0.7 image capture.

## Source and project identity

The Python distribution is `ricebowl-xfce` (version 0.7.1); the GTK hub uses the RiceBowl name and rice-bowl icon. Existing user-controlled appearance and backup identifiers are not renamed automatically. The former `ricehub` command and historical documentation stay available solely for migration.
