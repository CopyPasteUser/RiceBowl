"""Windows 98 taskbar preferences.

Only RiceBowl-owned widgets are changed. XFCE's panel, WM and global shortcuts
remain untouched, and malformed configuration falls back to visible controls.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

DEFAULTS = {"show_clock": True, "show_quick_launch": True}
MAX_FILE = 4096


def settings_path() -> Path:
    config = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    return config / "ricebowl" / "classic98-taskbar.json"


def load_settings(path: Path | None = None) -> dict[str, bool]:
    source = path if path is not None else settings_path()
    try:
        if source.stat().st_size > MAX_FILE or source.is_symlink():
            return dict(DEFAULTS)
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return dict(DEFAULTS)
    if not isinstance(data, dict):
        return dict(DEFAULTS)
    return {key: value if isinstance((value := data.get(key)), bool) else default
            for key, default in DEFAULTS.items()}


def save_settings(settings: dict[str, bool], path: Path | None = None) -> None:
    """Atomic owner-only settings file; refuse symlinks or invalid input."""
    if set(settings) != set(DEFAULTS) or any(not isinstance(v, bool) for v in settings.values()):
        raise ValueError("Invalid taskbar settings")
    target = path if path is not None else settings_path()
    if target.is_symlink() or target.parent.is_symlink():
        raise ValueError("Refusing symlinked taskbar configuration")
    if target.exists() and not target.is_file():
        raise ValueError("Taskbar config is not a regular file")
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".classic98-taskbar-", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(settings, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, target)
    finally:
        Path(tmp).unlink(missing_ok=True)


def apply_settings(shell, values: dict[str, bool]) -> None:
    """Apply independent visibility flags to known Classic widgets only."""
    shell.classic98_clock_button.set_visible(values["show_clock"])
    shell.classic98_quick_launch.set_visible(values["show_quick_launch"])


def show_properties(shell, Gtk) -> None:
    """Small functional Taskbar Properties dialog, without fake options."""
    values = load_settings()
    dialog = Gtk.Dialog(title="Taskbar Properties", transient_for=shell.bar,
                        flags=Gtk.DialogFlags.MODAL)
    dialog.set_default_size(360, 215)
    dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
    dialog.add_button("Apply", Gtk.ResponseType.APPLY)
    dialog.add_button("OK", Gtk.ResponseType.OK)
    body = dialog.get_content_area()
    body.set_spacing(10)
    body.set_margin_top(14)
    body.set_margin_bottom(14)
    body.set_margin_start(16)
    body.set_margin_end(16)
    heading = Gtk.Label(label="Taskbar Options", xalign=0)
    body.pack_start(heading, False, False, 0)
    clock = Gtk.CheckButton(label="Show clock")
    clock.set_active(values["show_clock"])
    quick = Gtk.CheckButton(label="Show Quick Launch toolbar")
    quick.set_active(values["show_quick_launch"])
    body.pack_start(clock, False, False, 0)
    body.pack_start(quick, False, False, 0)
    detail = Gtk.Label(label="Applies to Windows 98 only. Other RiceBowl styles are unchanged.",
                       xalign=0)
    detail.set_line_wrap(True)
    body.pack_start(detail, False, False, 0)
    dialog.show_all()
    try:
        while True:
            response = dialog.run()
            if response not in (Gtk.ResponseType.APPLY, Gtk.ResponseType.OK):
                break
            candidate = {"show_clock": clock.get_active(),
                         "show_quick_launch": quick.get_active()}
            try:
                save_settings(candidate)
            except (OSError, ValueError) as exc:
                detail.set_text("Could not save settings: " + str(exc))
                continue
            apply_settings(shell, candidate)
            if response == Gtk.ResponseType.OK:
                break
    finally:
        dialog.destroy()
