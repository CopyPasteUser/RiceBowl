# RiceBowl 0.9.1 — XP Luna geometry and resilient taskbar switching

This maintenance pre-release follows the owner's acceptance of the seven desktop personalities in 0.9.0, with one remaining visual defect: the XP Luna Start menu overlapped its taskbar slightly.

## What's fixed

- **XP Luna Start:** the menu now follows its actual GTK-allocated height rather than assuming the requested 560 px was honored. Its installed-app list can contract when needed, and the menu is re-anchored above the bottom taskbar.
- **Safer desktop transitions:** a new local GTK application action advertises when the replacement taskbar is mapped. The session coordinator waits for that signal before removing XFCE Panel.
- **Failure recovery:** if the new bar does not become ready, RiceBowl closes the incomplete shell and attempts to restore XFCE Panel and saved keyboard shortcuts. Existing user-owned Plank configuration is untouched.
- **Responsive Hub:** post-apply and post-restore taskbar reconciliation runs in the background, so a delayed startup does not freeze the GTK interface.

## Verification

The release pipeline runs the Python regression suite, GTK shell smoke checks, native X11 window-lifecycle test, and captures 12 fresh 1600×900 screenshots of six non-macOS Start menus and settings panels. The capture fails if a popup extends into the taskbar area. It also validates the settings views contain meaningful rendered content, not just a title strip. Release publication requires the CI tests to pass.

The owner's physical Mint XFCE acceptance of 0.9.0 covered the desktop appearance and functionality except this XP issue. **The 0.9.1 fix still needs confirmation on the actual laptop**, particularly at smaller resolutions and with an external display. RiceBowl remains a pre-release until the 1.0 hardware matrix is complete.

## Update

```bash
cd RiceBowl
git pull --ff-only
bash install.sh --dry-run
bash install.sh
ricebowl
```

Install as your normal desktop user, not root. Existing restore snapshots, RiceHub compatibility identifiers, and user-managed Plank preferences are preserved.

Repository: https://github.com/CopyPasteUser/RiceBowl
