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
from functools import partial
from pathlib import Path

from .aero import (AUTOSTART_MARKER, AeroAssetError, THEME as AERO_THEME,
                   autostart_content, install as install_aero, preflight as preflight_aero,
                   read_autostart, write_autostart)
from . import ten
from . import heritage
from .environment import config_home, data_home, private_state_root
from .installer import project_root
from .plank import DOCK_SCHEMA
from .themes import CONFIG_FILES, _read_preferences, preset_values, set_theme_values
from .thunar import (END as CSS_END, START as CSS_START,
                     MANAGED_PREFERENCES as THUNAR_PREFS, _read_css,
                     preference_type, preferences_for, plan_css, write_css)


class RiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class RiceStyle:
    name: str
    gtk: str
    xfwm: str
    wallpaper: str
    app_preset: str
    bar_theme: str
    plank_theme: str
    icon_theme: str = "WhiteSur-light"
    cursor_theme: str = "Bibata-Original-Classic"
    font: str = "Inter 10"
    title_font: str = "Inter Bold 10"
    button_layout: str = "O|HMC"
    plank_icon_size: str = "60"
    plank_alignment: str = "'center'"
    plank_zoom: str = "true"
    plank_hide: str = "'intelligent'"
    plank_position: str = "'bottom'"


STYLES = {
    "night": RiceStyle("Aurora Night", "WhiteSur-Dark", "WhiteSur-Dark", "aurora-night.jpg", "Midnight", "light", "MacRice-Frost-Glass"),
    "day": RiceStyle("Aurora Day", "WhiteSur-Light", "WhiteSur-Light", "aurora-day.jpg", "Light", "dark", "MacRice-Obsidian-Glass"),
    "aqua": RiceStyle("Classic Aqua", "WhiteSur-Light", "WhiteSur-Light", "aurora-day.jpg", "Classic Aqua", "aqua", "MacRice-Frost-Glass"),
    "aero-meadow": RiceStyle("Aero Seven Blue", AERO_THEME, AERO_THEME, "aero-seven-blue.jpg", "Light", "dark", "RiceHub-Aero-Glass",
                              icon_theme=AERO_THEME, cursor_theme="Adwaita", font="DejaVu Sans 10",
                              title_font="DejaVu Sans Bold 10", plank_icon_size="48", plank_alignment="'center'",
                              plank_zoom="false", plank_hide="'auto'", plank_position="'left'"),
    "aero-cascade": RiceStyle("Aero Seven Night", AERO_THEME, AERO_THEME, "aero-seven-night.jpg", "Light", "dark", "RiceHub-Aero-Glass",
                               icon_theme=AERO_THEME, cursor_theme="Adwaita", font="DejaVu Sans 10",
                               title_font="DejaVu Sans Bold 10", plank_icon_size="48", plank_alignment="'center'",
                               plank_zoom="false", plank_hide="'auto'", plank_position="'left'"),
    "ten-dark": RiceStyle("Windows 10 · Midnight", "RiceHub-Ten-Dark", "RiceHub-Ten-Dark", "ten-midnight.jpg",
                           "Midnight", "light", "RiceHub-Ten-Flat", icon_theme=ten.ICON_THEME,
                           cursor_theme="Adwaita", font="DejaVu Sans 10", title_font="DejaVu Sans Bold 10",
                           plank_icon_size="40", plank_zoom="false", plank_hide="'auto'",
                           plank_position="'left'"),
    "ten-light": RiceStyle("Windows 10 · Blue", "RiceHub-Ten-Light", "RiceHub-Ten-Light", "ten-blue.jpg",
                            "Light", "dark", "RiceHub-Ten-Flat", icon_theme=ten.ICON_THEME,
                            cursor_theme="Adwaita", font="DejaVu Sans 10", title_font="DejaVu Sans Bold 10",
                            plank_icon_size="40", plank_zoom="false", plank_hide="'auto'",
                            plank_position="'left'"),
}

for _key, _profile in heritage.PROFILES.items():
    STYLES[_key] = RiceStyle(
        _profile.name, _profile.theme, _profile.theme, _profile.wallpaper,
        "Light", "dark", "RiceHub-Aero-Glass", icon_theme=_profile.icon_theme,
        cursor_theme="Adwaita", font="DejaVu Sans 10", title_font="DejaVu Sans Bold 10",
        button_layout="O|HMC" if _key == "chromeos" else "O|HMC",
        plank_icon_size="40", plank_zoom="false", plank_hide="'auto'", plank_position="'left'",
    )


def _thunar_palette(style_name: str) -> str:
    if style_name in heritage.PROFILES:
        return style_name
    if style_name.startswith("aero-"):
        return "aero"
    if style_name.startswith("ten-"):
        return style_name
    return "night" if style_name in ("night",) else "day"

# GTK, XFWM, Thunar, Plank and XFCE wallpaper are the external settings touched.
XFCONF = (
    ("xsettings", "/Net/ThemeName", "gtk"),
    ("xsettings", "/Net/IconThemeName", "icon_theme"),
    ("xsettings", "/Gtk/CursorThemeName", "cursor_theme"),
    ("xsettings", "/Gtk/CursorThemeSize", "24"),
    ("xsettings", "/Gtk/FontName", "font"),
    ("xfwm4", "/general/theme", "xfwm"),
    ("xfwm4", "/general/title_font", "title_font"),
    ("xfwm4", "/general/button_layout", "button_layout"),
)
PLANK = (
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

    def get_optional(self, kind: str, channel: str, key: str) -> str | None:
        try:
            return self.get(kind, channel, key)
        except RiceError as exc:
            if kind == "xfconf" and channel == "thunar" and "does not exist" in str(exc).lower():
                return None
            raise

    def set(self, kind: str, channel: str, key: str, value: str, *, create: bool = False) -> None:
        if kind == "xfconf":
            kind_name = preference_type(key) if channel == "thunar" else "string"
            args = ("-n", "-t", kind_name) if create else ()
            self._run("xfconf-query", "-c", channel, "-p", key, *args, "-s", value)
        else:
            self._run("gsettings", "set", DOCK_SCHEMA, key, value)
        if self.get(kind, channel, key) != value:
            raise RiceError(f"Desktop setting {key} did not keep the requested value")

    def reset(self, kind: str, channel: str, key: str) -> None:
        if (kind, channel, key) not in {("xfconf", "thunar", k) for k, _ in THUNAR_PREFS}:
            raise RiceError("Refusing to reset an unmanaged desktop preference")
        self._run("xfconf-query", "-c", channel, "-p", key, "-r")
        if self.get_optional(kind, channel, key) is not None:
            raise RiceError(f"Could not reset {key}")

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


def _plank_theme_target(style: RiceStyle, data_root: Path, source_root: Path) -> tuple[Path, Path]:
    source = source_root / "assets/plank-themes" / style.plank_theme / "dock.theme"
    target = data_root / "plank/themes" / style.plank_theme / "dock.theme"
    if not source.is_file() or source.is_symlink():
        raise RiceError(f"Missing bundled Plank theme: {style.plank_theme}")
    contents = source.read_bytes()
    if len(contents) > 64 * 1024:
        raise RiceError("Bundled Plank theme is unexpectedly large")
    if any(parent.is_symlink() for parent in (target.parent.parent, target.parent.parent.parent)):
        raise RiceError("Unmanaged Plank theme directory; no settings changed")
    def usable(path: Path) -> bool:
        if path.parent.is_symlink() or path.is_symlink():
            return False
        if not path.parent.exists():
            return True  # New, isolated theme directory.
        return (path.parent.is_dir() and path.is_file() and
                path.stat().st_size <= 64 * 1024 and path.read_bytes() == contents)

    if usable(target):
        return source, target
    digest = hashlib.sha256(contents).hexdigest()[:12]
    # Never overwrite a previous version, even when its versioned name was
    # customized. Reuse the first matching copy or reserve an empty sibling.
    # ponytail: 32 slots bound preflight; expand only if real users exhaust them.
    for number in range(33):
        suffix = "" if number == 0 else f"-{number}"
        candidate = target.parent.parent / f"{style.plank_theme}-{digest}{suffix}" / "dock.theme"
        if usable(candidate):
            return source, candidate
    raise RiceError(f"No free Plank theme name for {style.plank_theme}; existing themes were preserved")


def _save_plank_theme(source: Path, target: Path) -> None:
    if target.exists():
        if (target.is_symlink() or not target.is_file() or target.stat().st_size > 64 * 1024 or
                target.read_bytes() != source.read_bytes()):
            raise RiceError("Plank theme changed during apply; no theme overwritten")
        return
    # Preflight chooses only an absent folder or an already matching file.
    # A newly appearing folder belongs to another process: do not enter it.
    target.parent.mkdir(mode=0o755, parents=True, exist_ok=False)
    fd, temp = tempfile.mkstemp(prefix=".macrice-dock-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as output, source.open("rb") as original:
            shutil.copyfileobj(original, output)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temp, 0o644)
        # Link only if absent, never replace a theme another process created.
        try:
            os.link(temp, target)
        except FileExistsError:
            if target.is_symlink() or not target.is_file() or target.read_bytes() != source.read_bytes():
                raise RiceError("Plank theme changed during apply; no theme overwritten")
    finally:
        Path(temp).unlink(missing_ok=True)


def _app_values(style: RiceStyle) -> dict[str, str]:
    values = preset_values(style.app_preset).copy()
    values["MacBar"] = style.bar_theme
    return values


def _changes(style: RiceStyle, backend: XfceBackend, target: Path, plank_theme: str) -> list[dict]:
    changes = []
    for channel, key, value in XFCONF:
        value = getattr(style, value, value)
        changes.append({"kind": "xfconf", "channel": channel, "key": key,
                        "before": backend.get("xfconf", channel, key), "after": value})
    for key, value in (("theme", f"'{plank_theme}'"),
                       ("position", style.plank_position), ("icon-size", style.plank_icon_size),
                       ("hide-mode", style.plank_hide), ("alignment", style.plank_alignment),
                       ("zoom-enabled", style.plank_zoom)):
        changes.append({"kind": "gsettings", "channel": "plank", "key": key,
                        "before": backend.get("gsettings", "plank", key), "after": value})
    # Keep the hidden Windows 7 menu bar from persisting after a rice switch.
    for key, value in preferences_for("aero" if style.gtk == AERO_THEME else "day"):
        changes.append({"kind": "xfconf", "channel": "thunar", "key": key,
                        "before": backend.get_optional("xfconf", "thunar", key), "after": value})
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
        ("icons", styles.icon_theme, "xsettings", "/Net/IconThemeName"),
        ("cursor", styles.cursor_theme, "xsettings", "/Gtk/CursorThemeName"),
    )
    before_by_key = {(c["channel"], c["key"]): c["before"] for c in changes}
    for kind, theme, channel, key in required:
        current = before_by_key[(channel, key)].strip("'")
        bundled = (theme == AERO_THEME or theme in (*ten.THEMES, ten.ICON_THEME,
                    *heritage.BY_THEME, *(p.icon_theme for p in heritage.PROFILES.values()))) and kind in ("gtk", "xfwm", "icons")
        if current != theme and not bundled and not backend.available(kind, theme):
            raise RiceError(f"Required {kind} theme '{theme}' is missing. Install it first; no settings changed.")
    family = styles.font.rsplit(" ", 1)[0]
    if not (before_by_key[("xsettings", "/Gtk/FontName")].startswith(family + " ") or
            backend.available("font", family)):
        raise RiceError(f"{family} font is missing. Install it before applying the full rice.")


def repair_assets(style_name: str, *, data_root: Path | None = None,
                  source_root: Path | None = None) -> tuple[Path, ...]:
    """Explicit, backed-up replacement of selected non-macOS managed assets.

    Does not change XFCE settings; the user must separately apply the rice.
    """
    if os.geteuid() == 0:
        raise RiceError("Repair RiceBowl assets as your desktop user, never with sudo")
    if style_name not in STYLES or style_name in ("night", "day"):
        raise RiceError("Asset repair is available only for a non-macOS rice")
    data_root = data_root or data_home()
    source_root = source_root or project_root()
    style = STYLES[style_name]
    if style.gtk == AERO_THEME:
        from .aero import BUNDLES as aero_bundles
        bundles = aero_bundles
    elif style.gtk in ten.THEMES:
        # Ten Dark and Ten Light share an icon pack, not their GTK themes.
        # Explicit repair of one variant must not replace edits in the other.
        bundles = tuple(pair for pair in ten.BUNDLES
                        if pair[1] == f"themes/{style.gtk}"
                        or pair[1] == f"icons/{ten.ICON_THEME}")
    else:
        bundles = heritage.bundles(style_name)
    packages = [(source_root / relative, data_root / destination)
                for relative, destination in bundles]
    try:
        from .aero import repair as repair_bundles
        return repair_bundles(packages)
    except (OSError, ValueError) as exc:
        raise RiceError(f"Asset repair failed safely: {exc}") from exc


def plan(style_name: str, *, backend: XfceBackend | None = None,
         data_root: Path | None = None, source_root: Path | None = None,
         config_root: Path | None = None) -> tuple[list[dict], dict[str, str | None], Path, Path]:
    if style_name not in STYLES:
        raise RiceError("Choose one of the available RiceBowl desktop styles")
    backend = backend or XfceBackend()
    data_root = data_root or data_home()
    source_root = source_root or project_root()
    config_root = config_root or config_home()
    source, target = _wallpaper_target(STYLES[style_name], data_root, source_root)
    _, dock_target = _plank_theme_target(STYLES[style_name], data_root, source_root)
    if STYLES[style_name].gtk == AERO_THEME:
        try:
            preflight_aero(source_root, data_root)
        except AeroAssetError as exc:
            raise RiceError(str(exc)) from exc
    if STYLES[style_name].gtk in ten.THEMES:
        try:
            ten.preflight(source_root, data_root)
        except AeroAssetError as exc:
            raise RiceError(str(exc)) from exc
    if style_name in heritage.PROFILES:
        try:
            heritage.preflight(style_name, source_root, data_root)
        except AeroAssetError as exc:
            raise RiceError(str(exc)) from exc
    try:
        plan_css(_thunar_palette(style_name), config_root)
        read_autostart(config_root)
        ten.read_autostart(config_root)
        for key in heritage.PROFILES:
            heritage.read_autostart(key, config_root)
    except (OSError, UnicodeError, ValueError) as exc:
        raise RiceError(f"Theme and session preflight failed: {exc}") from exc
    changes = _changes(STYLES[style_name], backend, target, dock_target.parent.name)
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
            kind, channel, key = change["kind"], change["channel"], change["key"]
            current = backend.get_optional(kind, channel, key)
            expected = change[field]
            if current == expected:
                continue
            if expected is None:
                backend.reset(kind, channel, key)
            else:
                backend.set(kind, channel, key, expected, create=current is None)
        except (RiceError, OSError) as exc:
            errors.append(f"{change['key']}: {exc}")
    return errors


def _shell_autostart_handlers():
    """One verified owner for every bundled autostart, including older backups."""
    handlers = {"aero": (read_autostart, write_autostart),
                "ten": (ten.read_autostart, ten.write_autostart)}
    for key in heritage.PROFILES:
        handlers[key] = (partial(heritage.read_autostart, key),
                         partial(heritage.write_autostart, key))
    return handlers


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
    style = STYLES[style_name]
    css = plan_css(_thunar_palette(style_name), config_root)
    shell_writers = _shell_autostart_handlers()
    shell_before = {key: reader(config_root) for key, (reader, _writer) in shell_writers.items()}
    shell_after = {
        "aero": autostart_content(source_root or project_root()) if style.gtk == AERO_THEME else None,
        "ten": ten.autostart_content(source_root or project_root()) if style.gtk in ten.THEMES else None,
    }
    shell_after.update({key: heritage.autostart_content(key) if style_name == key else None
                        for key in heritage.PROFILES})
    dock_source, dock_target = _plank_theme_target(style, data_root, source_root or project_root())
    if next(c["after"] for c in changes if c["kind"] == "gsettings" and c["key"] == "theme") != f"'{dock_target.parent.name}'":
        raise RiceError("Plank theme changed during preflight; retry without altering the desktop")
    dock_preexisting = dock_target.exists()
    private_state_root(data_root)
    _save_wallpaper(source, target)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = data_root / "macrice-state/backups/rice" / stamp
    backup.mkdir(mode=0o700, parents=True, exist_ok=False)
    manifest = {
        "schema": 5, "style": style_name, "changes": changes,
        "app_before": previous, "app_after": _app_values(style), "thunar_css": css,
        "shell_autostarts": {key: {"before": shell_before[key], "after": shell_after[key]}
                             for key in shell_writers},
    }
    out = backup / "manifest.json"
    fd = os.open(out, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, ensure_ascii=False)
        stream.flush()
        os.fsync(stream.fileno())

    written = []
    css_written = False
    try:
        if style.gtk == AERO_THEME:
            install_aero(preflight_aero(source_root or project_root(), data_root))
        elif style.gtk in ten.THEMES:
            install_aero(ten.preflight(source_root or project_root(), data_root))
        elif style_name in heritage.PROFILES:
            install_aero(heritage.preflight(style_name, source_root or project_root(), data_root))
        _save_plank_theme(dock_source, dock_target)
        if css["before"] != css["after"]:
            write_css(config_root, css["after"])
            css_written = True
        for change in changes:
            if change["before"] != change["after"]:
                written.append(change)
                backend.set(change["kind"], change["channel"], change["key"], change["after"],
                            create=change["before"] is None)
        for key, (_reader, writer) in shell_writers.items():
            if shell_before[key] != shell_after[key]:
                writer(config_root, shell_after[key])
        set_theme_values(_app_values(style), config_root=config_root, data_root=data_root)
    except Exception as exc:
        errors = _rollback(backend, written, "before")
        for key, (reader, writer) in shell_writers.items():
            try:
                if reader(config_root) == shell_after[key]:
                    writer(config_root, shell_before[key])
            except (AeroAssetError, OSError) as rollback_exc:
                errors.append(f"{key} autostart: {rollback_exc}")
        if css_written:
            try:
                write_css(config_root, css["before"])
            except (OSError, ValueError) as rollback_exc:
                errors.append(f"Thunar CSS: {rollback_exc}")
        if not dock_preexisting:
            try:
                if dock_target.is_file() and not dock_target.is_symlink() and dock_target.read_bytes() == dock_source.read_bytes():
                    dock_target.unlink()
                    dock_target.parent.rmdir()
            except OSError as rollback_exc:
                errors.append(f"Plank theme cleanup: {rollback_exc}")
        (backup / "failed").write_text("Application failed; see command output\n", encoding="utf-8")
        detail = f". Rollback incomplete: {'; '.join(errors)}" if errors else "; desktop changes rolled back"
        raise RiceError(f"Rice was not applied: {exc}{detail}") from exc
    return backup


def _latest_backup(data_root: Path) -> Path:
    root = data_root / "macrice-state/backups/rice"
    if not root.is_dir() or root.is_symlink():
        raise RiceError("No Rice backup found")
    candidates = sorted((p for p in root.iterdir() if p.is_dir() and not p.is_symlink()
                         and not (p / "restored").exists() and not (p / "failed").exists()), reverse=True)
    for path in candidates:
        if (path / "manifest.json").is_file() and not (path / "manifest.json").is_symlink():
            return path
    raise RiceError("No valid Rice backup found")


def _css_block(content: str | None) -> str | None:
    """Identify only the complete MacRice-owned block, never user CSS."""
    if content is None or content.count(CSS_START) != 1 or content.count(CSS_END) != 1:
        return None
    start = content.index(CSS_START)
    end = content.index(CSS_END) + len(CSS_END)
    if content[end:end + 1] == "\n":
        end += 1
    return content[start:end]


def _restored_css(before: str | None, after: str, current: str | None) -> tuple[str | None, bool]:
    """Restore our block while retaining CSS rules added outside it."""
    if current == after:
        return before, True
    if current == before:
        return current, True
    applied_block = _css_block(after)
    original_block = _css_block(before)
    if current is None or applied_block is None or _css_block(current) != applied_block:
        return current, False
    # Keep any user changes outside our exact, unmodified block.
    return current.replace(applied_block, original_block or "", 1), True


def restore(*, backend: XfceBackend | None = None, data_root: Path | None = None,
            config_root: Path | None = None) -> Path:
    """Restore managed settings; keep and report later user customizations."""
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
        schema = manifest["schema"]
        if schema not in (1, 2, 3, 4, 5) or set(old_apps) != set(CONFIG_FILES):
            raise ValueError("unexpected manifest schema")
        if set(new_apps) != set(CONFIG_FILES) or not isinstance(changes, list):
            raise ValueError("unexpected manifest fields")
        if any(v is not None and not isinstance(v, str) for v in (*old_apps.values(), *new_apps.values())):
            raise ValueError("invalid app theme")
        css = manifest.get("thunar_css") if schema >= 2 else None
        if schema >= 2 and (not isinstance(css, dict) or set(css) != {"before", "after"} or
                            not isinstance(css["after"], str) or
                            (css["before"] is not None and not isinstance(css["before"], str))):
            raise ValueError("invalid GTK CSS backup")
        aero_start = manifest.get("aero_autostart") if schema == 3 else None
        shell_starts = manifest.get("shell_autostarts") if schema in (4, 5) else None
        if schema == 3:
            if not isinstance(aero_start, dict) or set(aero_start) != {"before", "after"}:
                raise ValueError("invalid autostart backup")
            for content in aero_start.values():
                if content is not None and (not isinstance(content, str) or
                                            content != autostart_content(project_root())):
                    raise ValueError("invalid autostart backup contents")
        if schema in (4, 5):
            canonical_starts = {"aero": autostart_content(project_root()),
                                "ten": ten.autostart_content(project_root())}
            if schema == 5:
                canonical_starts.update({key: heritage.autostart_content(key) for key in heritage.PROFILES})
            if not isinstance(shell_starts, dict) or set(shell_starts) != set(canonical_starts):
                raise ValueError("invalid shell autostart backup")
            for key, canonical in canonical_starts.items():
                item = shell_starts[key]
                if not isinstance(item, dict) or set(item) != {"before", "after"}:
                    raise ValueError("invalid shell autostart item")
                for content in item.values():
                    if content is not None and content != canonical:
                        raise ValueError("invalid shell autostart contents")
    except (KeyError, ValueError, TypeError, OSError) as exc:
        raise RiceError("Invalid Rice backup; nothing changed") from exc

    # Do not honor arbitrary paths or channels from a modified manifest.
    allowed = {("xfconf", channel, key) for channel, key, _ in XFCONF}
    allowed.update({("gsettings", "plank", key) for key, _ in PLANK})
    allowed.add(("gsettings", "plank", "theme"))
    if schema >= 2:
        allowed.update({("xfconf", "thunar", key) for key, _ in THUNAR_PREFS})
    for change in changes:
        try:
            item = (change["kind"], change["channel"], change["key"])
            if item not in allowed and not (
                item[0:2] == ("xfconf", "xfce4-desktop") and
                (WALLPAPER_KEY.fullmatch(item[2]) or
                 WALLPAPER_KEY.fullmatch(item[2].removesuffix("image-style") + "last-image"))
            ):
                raise ValueError("unexpected preference path")
            if (change["before"] is None and item not in
                {("xfconf", "thunar", key) for key, _ in THUNAR_PREFS}):
                raise ValueError("unexpected unset setting")
            if (change["before"] is not None and not isinstance(change["before"], str)) or not isinstance(change["after"], str):
                raise ValueError("invalid setting value")
        except (KeyError, TypeError, ValueError) as exc:
            raise RiceError("Invalid Rice backup; nothing changed") from exc

    current_apps = _read_app_themes(config_root)
    skipped = []
    to_restore = []
    for change in changes:
        current = backend.get_optional(change["kind"], change["channel"], change["key"])
        if current == change["after"]:
            if change["before"] != change["after"]:
                to_restore.append(change)
        elif current != change["before"]:
            skipped.append(f"{change['channel']}:{change['key']}")

    desired_apps = current_apps.copy()
    for name, current in current_apps.items():
        if current == new_apps[name]:
            desired_apps[name] = old_apps[name]
        elif current != old_apps[name]:
            skipped.append(f"{name} theme")
    apps_changed = desired_apps != current_apps

    auto_changes = []
    if aero_start is not None:
        try:
            current_auto = read_autostart(config_root)
        except (AeroAssetError, OSError) as exc:
            raise RiceError(f"Aero autostart cannot be inspected: {exc}") from exc
        if current_auto == aero_start["after"]:
            if current_auto != aero_start["before"]:
                auto_changes.append(("aero", write_autostart, aero_start["before"], aero_start["after"]))
        elif current_auto != aero_start["before"]:
            skipped.append("Aero autostart (customized)")
    if shell_starts is not None:
        for key, (reader, writer) in _shell_autostart_handlers().items():
            if key not in shell_starts:  # v4 snapshots predate the four new rices.
                continue
            item = shell_starts[key]
            try:
                current_auto = reader(config_root)
            except (AeroAssetError, OSError) as exc:
                raise RiceError(f"{key} autostart cannot be inspected: {exc}") from exc
            if current_auto == item["after"]:
                if current_auto != item["before"]:
                    auto_changes.append((key, writer, item["before"], item["after"]))
            elif current_auto != item["before"]:
                skipped.append(f"{key} autostart (customized)")

    css_target = None
    css_changed = False
    if css is not None:
        try:
            current_css = _read_css(config_root / "gtk-3.0/gtk.css")
        except (OSError, ValueError) as exc:
            raise RiceError(f"Thunar CSS cannot be checked: {exc}") from exc
        css_target, css_safe = _restored_css(css["before"], css["after"], current_css)
        if not css_safe:
            skipped.append("Thunar CSS (customized MacRice block)")
        css_changed = css_safe and css_target != current_css

    written = []
    apps_restored = False
    try:
        if apps_changed:
            set_theme_values(desired_apps, config_root=config_root, data_root=data_root)
            apps_restored = True
        for change in reversed(to_restore):
            written.append(change)
            if change["before"] is None:
                backend.reset(change["kind"], change["channel"], change["key"])
            else:
                backend.set(change["kind"], change["channel"], change["key"], change["before"])
        for _key, writer, target_content, _old_content in auto_changes:
            writer(config_root, target_content)
        if css_changed:
            write_css(config_root, css_target)
    except Exception as exc:
        errors = _rollback(backend, written, "after")
        if apps_restored:
            try:
                set_theme_values(current_apps, config_root=config_root, data_root=data_root)
            except (OSError, ValueError) as rollback_exc:
                errors.append(f"App themes: {rollback_exc}")
        for key, writer, _target_content, applied_content in reversed(auto_changes):
            try:
                writer(config_root, applied_content)
            except (AeroAssetError, OSError) as rollback_exc:
                errors.append(f"{key} autostart: {rollback_exc}")
        detail = f"; rollback incomplete: {'; '.join(errors)}" if errors else "; previous Rice kept"
        raise RiceError(f"Restore failed: {exc}{detail}") from exc

    # A backup remains as an audit record, but is never silently replayed.
    if skipped:
        (backup / "skipped.json").write_text(
            json.dumps(skipped, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
        )
    (backup / "restored").write_text("Restored by MacRice\n", encoding="utf-8")
    return backup
