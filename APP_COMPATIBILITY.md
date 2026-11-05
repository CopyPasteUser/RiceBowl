# Application theme compatibility · owner QA-01 / QA-04 / QA-06

RiceBowl styles the **XFCE/X11 desktop session**, its own GTK interfaces,
GTK-compatible applications, and the XFWM4 **server-side window frame**.
The active rice does not automatically rewrite every application's internal
interface. The distinction matters most for PhotoCraft and Thunderbird.

## Diagnose one actual window on the Mint/XFCE laptop

```bash
macrice rice plan winxp  # Optional: verify the target style before applying
macrice app-compat --select
```

Select the PhotoCraft or Thunderbird window with the mouse. To inspect a known
X11 ID non-interactively, use `macrice app-compat --window-id 0x12345 --json`.
The command reads only the selected window's class and three decoration/type
hints plus the active XFConf GTK/XFWM theme names. It **never** requests the
window title, arguments, credentials, file paths, or profile settings. No
settings are changed; the interactive selection times out after 25 seconds.
Missing `xprop` is resolved by installing the system's `x11-utils` package.
This command supports X11 only, not Wayland.

An `_GTK_FRAME_EXTENTS` hint may indicate GTK client-side decorations but is
**not** definitive. The presence of `_MOTIF_WM_HINTS` alone also does not
prove that a visible XFWM border exists. The final check must be visual.

## What can be themed?

| Window technology | RiceBowl-controlled scope | What remains app-controlled |
| --- | --- | --- |
| Traditional GTK3 + server-side decoration | XFConf GTK theme; XFWM frame | Widget-specific styling, hard-coded app CSS |
| GTK client-side decoration (CSD) | GTK theme, to the extent the app uses it | App-owned header/title bar; XFWM cannot paint it |
| Qt / KDE | XFWM frame when server-side | Qt widget palette and app-specific styles; not the GTK theme |
| Electron / browser-like | XFWM frame when server-side | HTML/CSS/browser chrome; not the GTK theme |
| egui, wgpu, OpenGL and custom-drawn | XFWM frame if the app requests system decorations | All pixels drawn by the application's rendering engine |

### PhotoCraft (QA-04)

PhotoCraft has a custom Rust **egui/wgpu** renderer and a supported
**Preferences → Interface → System Title Bar** setting. Turn that setting on
inside PhotoCraft, then close and reopen the app if the frame does not update.
XP Luna's XFWM frame can then appear around the app; its egui contents will
still look like PhotoCraft. RiceBowl deliberately does not rewrite PhotoCraft
preferences or inject unsupported styles.

### Thunderbird (QA-06)

Thunderbird provides **Settings → General → Language & Appearance →
Hide system window titlebar**. Disable that setting so XFWM can provide
the active rice's frame. Thunderbird's tabs, toolbar and mail UI remain
primarily application-controlled. `userChrome.css` is unsupported by RiceBowl;
automatically changing Thunderbird profiles could overwrite owner styles and
is not part of this workstream.

### A consistent Task Manager (QA-01)

Existing rice integrations already prefer the installed `xfce4-taskmanager`
and fall back to `gnome-system-monitor` in supported settings menus; the
Windows 7 taskbar also provides a native **Start Task Manager** action. Those
launch genuine OS process managers, not a fake shell. With the GTK-compatible
XFCE task manager, GTK theme and XFWM frame provide the closest low-overhead
match. A fully reimplemented Windows-like process manager would be a separate
product and must not displace the user's trusted system tool automatically.

## On-device acceptance still required

1. Capture the current rice and X11 session: `macrice doctor`.
2. With XP Luna active, run `macrice app-compat --select` and select each app.
3. Enable the **app-owned** system-titlebar option above *only if you want to*.
4. Reopen both windows and verify the expected XFWM border, resize, Alt-Tab,
   focus and taskbar presence; test after switching between two rices.
5. Confirm the interiors remain usable, and record any discrepancy. Tests of
   parsing and invocation do **not** count as physical theme acceptance.

Source pointers: [PhotoCraft app](https://github.com/storytold/photocraft)
and [Thunderbird Support](https://support.mozilla.org/).
