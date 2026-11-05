# Windows 10 22H2 rice · Mint/XFCE acceptance

These tests are **not** considered passed by headless CI. Run them on the
physical Linux Mint XFCE/X11 computer, preferably at 1600×900 and 1024×768.
Everything in this rice must use real Linux state and independently created
artwork, never Microsoft icons, fonts, wallpaper or executable files.

Before beginning:

1. Update RiceBowl from `main` and run the installer's documented `--dry-run`
   before the normal install. Keep the existing desktop restore snapshot.
2. In the RiceBowl Hub, select Windows 10. Check that only **one** RiceBowl
   taskbar is running, without a second XFCE panel covering it.
3. Keep an open terminal for recovery. Do not remove XFWM4, XFCE session,
   NetworkManager, BlueZ, PipeWire/PulseAudio or any desktop files.
4. Mark each item **Pass / Fail / Not applicable** and record the screen size,
   installed hardware and any error message. A photo or screenshot of a failure
   is more useful than a subjective percentage.

## 1. Taskbar and Start

- [ ] At 1600×900, taskbar has left Start, a readable search box, Task View,
  pinned/running apps, right-side tray, two-line clock and Show Desktop strip;
  there is no clipping or Windows 7 gloss.
- [ ] Taskbar right-click **Search**: Hidden / icon / box each works and survives
  restart. At 1024×768 the box automatically contracts to an icon.
- [ ] Taskbar right-click toggles Task View; pinned icons can be dragged left
  and right, or reordered using context-menu commands. Reorder survives restart.
- [ ] Start opens at the bottom left, and its rail, A–Z app list and independent
  scrollable tile groups all fit without overlapping the taskbar.
- [ ] A–Z jump, application launch, Start search and Enter/Down/Escape work with
  keyboard alone. Searching “volume” opens native Sound Settings; searching
  “Downloads” shows the real folder shortcut if it exists.
- [ ] Right-click any app → **Pin to Start**, **Pin to taskbar**: verify these
  are separate pins. Unpin from one must not silently remove the other.
- [ ] Right-click Start tile → resize Small / Medium / Wide / Large. Small tiles
  stay launchable; text and icons are not cropped in the others.
- [ ] Drag a tile before/after another and between groups; use the edit icon to
  rename a group (Enter saves, Escape discards). Restart RiceBowl and verify
  names, sizes, pins and ordering persist. No other rice is modified.
- [ ] Start user-folder links, Settings and power/session actions open real
  destinations, not blank pages. Close Start via outside click and Escape.

## 2. Hardware flyouts and notification center

- [ ] Click tray speaker: Win10-styled volume flyout appears directly above
  taskbar. Change volume, toggle mute, switch output if available, use volume
  keys. Readback agrees with the Linux sound mixer.
- [ ] Click wireless: enumerate actual SSIDs, security and signal. Connect and
  disconnect a saved network; try an unknown secured network and verify
  NetworkManager's credential handoff. Disabling Wi-Fi is visibly reflected.
- [ ] Click Bluetooth with adapter present: enable/disable, verify known
  devices and pairing handoff, then repeat with adapter absent or blocked.
- [ ] Click battery on a laptop: correct percentage and charging label, real
  power profiles/brightness where supported. On a desktop with no battery,
  the taskbar must not invent one.
- [ ] Click clock/date: calendar opens, shows correct local date/month and
  time, and remains fully inside 1024×768. Test month navigation.
- [ ] Opening a second flyout closes the first; opening Start/Settings/Task
  View hides all flyouts. Escape and focus loss dismiss them.
- [ ] Send a genuine desktop notification, open Action Center and verify
  icon, sender, content, read/dismiss, grouped list and timestamps. Test
  Focus Assist/Do Not Disturb and **Clear all** cancel/confirm separately.
- [ ] Toggle Wi-Fi, Bluetooth, sound and Focus Assist outside RiceBowl and
  verify the shell refreshes the *actual* state, never a speculative toggle.

## 3. Settings and window management

- [ ] Settings home shows 12 usable categories. Search, Back, Ctrl+F,
  Escape, sidebar and deep links navigate correctly, without blank pages.
- [ ] System → Sound, Display, Notifications: sliders/switches stay disabled
  if the Linux provider is absent. A failed change must show an error and
  must not visually claim success.
- [ ] System → Storage: measured capacity matches the user's home filesystem;
  Power & sleep shows truthful battery status, even on desktop hardware.
- [ ] Apps → Apps & features: type part of a real installed app name, open
  it, and use Show more. It must not pretend to uninstall an app.
- [ ] Network, Bluetooth, Personalization, privacy and updates link to real
  Linux controls or explicitly disable unavailable tools. No Windows Update
  or Defender status should be invented.
- [ ] Task View shows *real* windows with app icons in two columns, marks the
  active window, activates one by click, and changes XFCE desktops.
- [ ] Create a second desktop, move a chosen window there, return to it and
  close only that window using the card's ×. Removing an occupied desktop
  must be prevented; no unrelated application is closed.
- [ ] Open a GTK app, Thunderbird, browser and RiceExplorer/Thunar. Verify
  consistent Win10-like window decoration where supported, correct Linux app
  content, focus, minimize/maximize, resizing, Alt+Tab and no crashes.

## 4. Resolution, recovery and performance

- [ ] Repeat Start, Settings, tray, Action Center and Task View at 1024×768;
  check no offscreen controls or unusable scroll regions. Check 125% and
  150% UI scaling if available.
- [ ] If a second monitor exists: move active window and disconnect/reconnect
  display; flyouts remain attached to their taskbar and do not cover another
  monitor. Also verify fullscreen app behavior.
- [ ] Logout/login: one active RiceBowl shell, no duplicate tray/sidebar,
  persisted Start/taskbar settings, real hardware state, no runaway CPU.
- [ ] Switch from Windows 10 → XP/7/ChromeOS → Windows 10 and back to the
  original desktop. Confirm wallpapers, panels, file associations and
  keyboard shortcuts recover from the existing RiceBowl session snapshot.
- [ ] Test optional `rice-explorer --theme win10` **only if installed**; it
  must not replace system-wide Thunar/MIME defaults. Full ribbon, file
  operation and NAS acceptance are tracked in the separate RiceExplorer repo.
- [ ] After 10 minutes idle plus repeated flyout open/close, inspect process
  RAM/CPU and responsiveness. No growing resident worker count or extra XFCE
  background services should appear because of the selected rice.

## Failure report

Copy these **read-only** diagnostics (omit private file paths or SSIDs before
sharing):

```bash
printf 'Session: %s / %s\n' "$XDG_CURRENT_DESKTOP" "$XDG_SESSION_TYPE"
pgrep -af 'ricebowl|ricehub|xfce4-panel|xfwm4|thunar' | head -30
free -h
```

For each failed checkbox include: resolution/scaling, exact click path, expected
vs. actual result, relevant screenshot, and whether it reproduces after
restarting only the rice shell. **Do not** delete XFCE configuration or run
global reset commands as a troubleshooting step.
