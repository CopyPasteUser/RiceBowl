"""Opt-in, reversible XFCE + Plank + bundled-app appearance presets.

Never run from installation. All external writes follow a complete read-only
preflight and are journaled before the first desktop setting changes.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .environment import config_home, data_home, private_state_root
from .installer import project_root
from .plank import DOCK_SCHEMA
from .themes import CONFIG_FILES, _read_preferences, apply_preset, preset_values, set_theme_values


class RiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class RiceStyle:
    name: str
    gtk: str
    xfwm: str
    wallpaper: str
    app_preset: str


STYLES = {
    "night": RiceStyle("Aurora Night", "WhiteSur-Dark", "WhiteSur-Dark", "aurora-night.jpg", "Midnight"),
    "day": RiceStyle("Aurora Day", "WhiteSur-Light", "WhiteSur-Light", "aurora-day.jpg", "Light"),
}

# GTK, XFWM, Plank and XFCE wallpaper are the only external settings touched.
XFCONF = (
    ("xsettings", "/Net/ThemeName", "gtk"),
    ("xsettings", "/Net/IconThemeName", "WhiteSur-light"),
    ("xsettings", "/Gtk/CursorThemeName", "Bibata-Original-Classic"),
    ("xsettings", "/Gtk/CursorThemeSize", "24"),
    ("xsettings", "/Gtk/FontName", "Inter 10"),
    ("xfwm4", "/general/theme", "xfwm"),
    ("xfwm4", "/general/title_font", "Inter Bold 10"),
    ("xfwm4", "/general/button_layout", "CHM|"),
)
PLANK = (
    ("theme", "'WhiteSur'"),
    ("position", "'bottom'"),
    ("icon-size", "60"),
    ("hide-mode", "'intelligent'"),
    ("alignment", "'center'"),
    ("zoom-enabled", "true"),
)
WALLPAPER_KEY = re.compile(r"^/backdrop/screen\d+/monitor[^/]+/workspace\d+/last-image$")


class XfceBackend:
    """Bounded, argument-vector subprocess integration; no shell evaluation."""

    @staticmethod
    def _run(*args: str) -> str:
        try:
            result = subprocess.run(
                args, capture_output=True, text=True, timeout=3, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RiceError(f"Could not run {args[0]}: {exc}") from exc
        if result.returncode:
            raise RiceError(f"{args[0]} rejected {args[-1]}: {result.stderr.strip()[:180]}")
        return result.stdout.strip()

    def get(self, kind: str, channel: str, key: str) -> str:
        if kind == "xfconf":
            return self._run("xfconf-query", "-c", channel, "-p", key)
        return self._run("gsettings", "get", DOCK_SCHEMA, key)

    def set(self, kind: str, channel: str, key: str, value: str) -> None:
        if kind == "xfconf":
            self._run("xfconf-query", "-c", channel, "-p", key, "-s", value)
        else:
            self._run("gsettings", "set", DOCK_SCHEMA, key, value)
        if self.get(kind, channel, key) != value:
            raise RiceError(f"Desktop setting {key} did not keep the requested value")

    def wallpaper_keys(self) -> list[str]:
        keys = self._run("xfconf-query", "-c", "xfce4-desktop", "-l").splitlines()
        images = sorted(key for key in keys if WALLPAPER_KEY.fullmatch(key))
        if not images:
            raise RiceError("No XFCE wallpaper properties found. Choose a wallpaper once in Desktop Settings first.")
        for image in images:
            style = image.removesuffix("last-image") + "image-style"
            if style not in keys:
                raise RiceError(f"Missing XFCE image-style property for {image}; no changes made")
        return images

    @staticmethod
    def available(kind: str, name: str) -> bool:
        home = Path.home()
        data = data_home()
        if kind in ("gtk", "xfwm"):
            paths = (home / ".themes", data / "themes", Path("/usr/share/themes"),
                     Path("/usr/local/share/themes"))
            subdir = "gtk-3.0" if kind == "gtk" else "xfwm4"
            return any((root / name / subdir).is_dir() for root in paths)
        if kind in ("icons", "cursor"):
            paths = (home / ".icons", data / "icons", Path("/usr/share/icons"),
                     Path("/usr/local/share/icons"))
            return any((root / name).is_dir() for root in paths)
        if kind == "plank":
            paths = (data / "plank/themes", home / ".local/share/plank/themes",
                     Path("/usr/share/plank/themes"))
            return any((root / name).is_dir() for root in paths)
        if kind == "font":
            try:
                value = XfceBackend._run("fc-match", "-f", "%{family}", name)
            except RiceError:
                return False
            return name.lower() in (item.strip().lower() for item in value.split(","))
        return False


def _read_app_themes(config_root: Path) -> dict[str, str | None]:
    result = {}
    for name, relative in CONFIG_FILES.items():
        current = _read_preferences(config_root / relative)
        value = current.get("theme")
        if value is not None and not isinstance(value, str):
            raise RiceError(f"Unexpected theme setting for {name}; no changes made")
        result[name] = value
    return result


def _wallpaper_target(style: RiceStyle, data_root: Path, source_root: Path) -> tuple[Path, Path]:
    source = source_root / "assets/wallpapers" / style.wallpaper
    if not source.is_file() or source.is_symlink():
        raise RiceError(f"Missing bundled wallpaper: {style.wallpaper}")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:12]
    target = data_root / "macrice-state/wallpapers" / f"{style.name.lower().replace(' ', '-')}-{digest}.jpg"
    if target.is_symlink() or (target.exists() and (
        not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest()[:12] != digest
    )):
        raise RiceError(f"Unmanaged wallpaper at {target}; nothing replaced")
    return source, target


def _changes(style: RiceStyle, backend: XfceBackend, target: Path) -> list[dict[str, str]]:
    changes = []
    for channel, key, value in XFCONF:
        value = getattr(style, value) if value in ("gtk", "xfwm") else value
        changes.append({"kind": "xfconf", "channel": channel, "key": key,
                        "before": backend.get("xfconf", channel, key), "after": value})
    for key, value in PLANK:
        changes.append({"kind": "gsettings", "channel": "plank", "key": key,
                        "before": backend.get("gsettings", "plank", key), "after": value})
    for image in backend.wallpaper_keys():
        changes.append({"kind": "xfconf", "channel": "xfce4-desktop", "key": image,
                        "before": backend.get("xfconf", "xfce4-desktop", image), "after": str(target)})
        style_key = image.removesuffix("last-image") + "image-style"
        changes.append({"kind": "xfconf", "channel": "xfce4-desktop", "key": style_key,
                        "before": backend.get("xfconf", "xfce4-desktop", style_key), "after": "5"})
    return changes


def _preflight(styles: RiceStyle, changes: list[dict], backend: XfceBackend) -> None:
    required = (
        ("gtk", styles.gtk, "xsettings", "/Net/ThemeName"),
        ("xfwm", styles.xfwm, "xfwm4", "/general/theme"),
        ("icons", "WhiteSur-light", "xsettings", "/Net/IconThemeName"),
        ("cursor", "Bibata-Original-Classic", "xsettings", "/Gtk/CursorThemeName"),
        ("plank", "WhiteSur", "plank", "theme"),
    )
    before_by_key = {(c["channel"], c["key"]): c["before"] for c in changes}
    for kind, theme, channel, key in required:
        current = before_by_key[(channel, key)].strip("'")
        if current != theme and not backend.available(kind, theme):
            raise RiceError(f"Required {kind} theme '{theme}' is missing. Install it first; no settings changed.")
    if not (before_by_key[("xsettings", "/Gtk/FontName")].startswith("Inter ") or
            backend.available("font", "Inter")):
        raise RiceError("Inter font is missing. Install Inter before applying the full rice.")


def plan(style_name: str, *, backend: XfceBackend | None = None,
         data_root: Path | None = None, source_root: Path | None = None,
         config_root: Path | None = None) -> tuple[list[dict[str, str]], dict[str, str | None], Path, Path]:
    if style_name not in STYLES:
        raise RiceError("Choose night or day")
    backend = backend or XfceBackend()
    data_root = data_root or data_home()
    source_root = source_root or project_root()
    config_root = config_root or config_home()
    source, target = _wallpaper_target(STYLES[style_name], data_root, source_root)
    changes = _changes(STYLES[style_name], backend, target)
    _preflight(STYLES[style_name], changes, backend)
    return changes, _read_app_themes(config_root), source, target


def _save_wallpaper(source: Path, target: Path) -> None:
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if target.exists():
        return
    fd, tmp = tempfile.mkstemp(prefix=".macrice-wallpaper-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as stream, source.open("rb") as original:
            shutil.copyfileobj(original, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, target)
    finally:
        Path(tmp).unlink(missing_ok=True)


def _rollback(backend: XfceBackend, applied: list[dict], field: str) -> list[str]:
    errors = []
    for change in reversed(applied):
        try:
            if backend.get(change["kind"], change["channel"], change["key"]) == change[field]:
                continue
            backend.set(change["kind"], change["channel"], change["key"], change[field])
        except (RiceError, OSError) as exc:
            errors.append(f"{change['key']}: {exc}")
    return errors


def apply(style_name: str, *, backend: XfceBackend | None = None,
          data_root: Path | None = None, source_root: Path | None = None,
          config_root: Path | None = None) -> Path:
    """Preflight, journal, then apply. Revert all desktop values if a step fails."""
    if os.geteuid() == 0:
        raise RiceError("Apply Rice as your normal desktop user, never with sudo")
    backend = backend or XfceBackend()
    data_root = data_root or data_home()
    config_root = config_root or config_home()
    changes, previous, source, target = plan(
        style_name, backend=backend, data_root=data_root,
        source_root=source_root, config_root=config_root,
    )
    private_state_root(data_root)
    _save_wallpaper(source, target)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = data_root / "macrice-state/backups/rice" / stamp
    backup.mkdir(mode=0o700, parents=True, exist_ok=False)
    manifest = {
        "schema": 1, "style": style_name, "changes": changes,
        "app_before": previous, "app_after": preset_values(STYLES[style_name].app_preset),
    }
    out = backup / "manifest.json"
    fd = os.open(out, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, ensure_ascii=False)
        stream.flush()
        os.fsync(stream.fileno())

    written = []
    try:
        for change in changes:
            if change["before"] != change["after"]:
                written.append(change)
                backend.set(change["kind"], change["channel"], change["key"], change["after"])
        apply_preset(STYLES[style_name].app_preset, config_root=config_root, data_root=data_root)
    except Exception as exc:
        errors = _rollback(backend, written, "before")
        detail = f". Rollback incomplete: {'; '.join(errors)}" if errors else "; desktop changes rolled back"
        raise RiceError(f"Rice was not applied: {exc}{detail}") from exc
    return backup


def _latest_backup(data_root: Path) -> Path:
    root = data_root / "macrice-state/backups/rice"
    if not root.is_dir() or root.is_symlink():
        raise RiceError("No Rice backup found")
    candidates = sorted((p for p in root.iterdir() if p.is_dir() and not p.is_symlink()
                         and not (p / "restored").exists()), reverse=True)
    for path in candidates:
        if (path / "manifest.json").is_file() and not (path / "manifest.json").is_symlink():
            return path
    raise RiceError("No valid Rice backup found")


def restore(*, backend: XfceBackend | None = None, data_root: Path | None = None,
            config_root: Path | None = None) -> Path:
    """Restore the last applied desktop rice; refuse to overwrite later edits."""
    if os.geteuid() == 0:
        raise RiceError("Restore Rice as your normal desktop user, never with sudo")
    backend = backend or XfceBackend()
    data_root = data_root or data_home()
    config_root = config_root or config_home()
    backup = _latest_backup(data_root)
    manifest_path = backup / "manifest.json"
    if manifest_path.stat().st_size > 256 * 1024:
        raise RiceError("Rice backup manifest unexpectedly large")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        changes = manifest["changes"]
        old_apps = manifest["app_before"]
        new_apps = manifest["app_after"]
        if manifest["schema"] != 1 or set(old_apps) != set(CONFIG_FILES):
            raise ValueError("unexpected manifest schema")
        if set(new_apps) != set(CONFIG_FILES) or not isinstance(changes, list):
            raise ValueError("unexpected manifest fields")
    except (KeyError, ValueError, TypeError, OSError) as exc:
        raise RiceError("Invalid Rice backup; nothing changed") from exc

    # Do not honor arbitrary paths or channels from a modified manifest.
    allowed = {("xfconf", channel, key) for channel, key, _ in XFCONF}
    allowed.update({("gsettings", "plank", key) for key, _ in PLANK})
    for change in changes:
        try:
            item = (change["kind"], change["channel"], change["key"])
            if item not in allowed and not (
                item[0:2] == ("xfconf", "xfce4-desktop") and
                (WALLPAPER_KEY.fullmatch(item[2]) or
                 WALLPAPER_KEY.fullmatch(item[2].removesuffix("image-style") + "last-image"))
            ):
                raise ValueError("unexpected preference path")
            if not isinstance(change["before"], str) or not isinstance(change["after"], str):
                raise ValueError("invalid setting value")
            if backend.get(*item) != change["after"]:
                raise RiceError(f"{change['key']} changed since applying Rice; restore stopped to preserve your edits")
        except (KeyError, TypeError, ValueError) as exc:
            raise RiceError("Invalid Rice backup; nothing changed") from exc

    current_apps = _read_app_themes(config_root)
    if current_apps != new_apps:
        raise RiceError("App themes changed since applying Rice; restore stopped to preserve your edits")

    written = []
    try:
        for change in reversed(changes):
            if change["before"] != change["after"]:
                written.append(change)
                backend.set(change["kind"], change["channel"], change["key"], change["before"])
        set_theme_values(old_apps, config_root=config_root, data_root=data_root)
    except Exception as exc:
        errors = _rollback(backend, written, "after")
        detail = f"; rollback incomplete: {'; '.join(errors)}" if errors else "; previous Rice kept"
        raise RiceError(f"Restore failed: {exc}{detail}") from exc

    # A backup remains as an audit record, but is never silently replayed.
    (backup / "restored").write_text("Restored by MacRice\n", encoding="utf-8")
    return backup
