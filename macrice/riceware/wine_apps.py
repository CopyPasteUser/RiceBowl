"""Safe Wine application catalog shared by all RiceBowl launchers.

Only metadata in riceWine-owned private prefixes is changed. No Windows
installer, system MIME handler or application binary is modified.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from . import wine


APP_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,47}\Z")
ICON_NAME = re.compile(r"[a-zA-Z0-9_.-]{1,128}\Z")
CATALOG = ".ricewine-apps.json"
LOCK = ".ricewine-apps.lock"
MAX_APPS = 128
MAX_CATALOG_BYTES = 128 * 1024


@dataclass(frozen=True)
class WineApplication:
    prefix: str
    identifier: str
    title: str
    executable: str
    arguments: tuple[str, ...] = ()
    icon: str | None = None


@dataclass(frozen=True)
class CatalogSnapshot:
    applications: tuple[WineApplication, ...]
    issues: tuple[str, ...] = ()


def _validate(app: WineApplication) -> None:
    wine._name(app.prefix)
    if not isinstance(app.identifier, str) or not APP_ID.fullmatch(app.identifier):
        raise ValueError("Invalid application ID")
    if (not isinstance(app.title, str) or not app.title.strip() or
            len(app.title) > 120 or not app.title.isprintable()):
        raise ValueError("Application title must be printable and 1–120 characters")
    if (not isinstance(app.executable, str) or not app.executable or
            app.executable.startswith("-") or len(app.executable) > 1024 or
            "\x00" in app.executable):
        raise ValueError("Select a valid explicit Windows executable")
    if (not isinstance(app.arguments, tuple) or len(app.arguments) > 32 or
            any(not isinstance(arg, str) or len(arg) > 1024 or "\x00" in arg
                for arg in app.arguments)):
        raise ValueError("Invalid application arguments")
    if app.icon is not None and (not isinstance(app.icon, str) or
                                 not ICON_NAME.fullmatch(app.icon)):
        raise ValueError("Icon must be a safe theme icon name")


def _prefix(name: str, store: Path | None) -> Path:
    wine._name(name)
    path = wine._store(store) / name
    wine._check_dir(path)
    if not wine._is_ready(path):
        raise RuntimeError("Wine prefix is not initialized")
    return path


def _load(prefix: Path) -> list[WineApplication]:
    path = prefix / CATALOG
    if path.is_symlink():
        raise RuntimeError("Refusing a symlinked Wine app catalog")
    if not path.exists():
        return []
    try:
        with os.fdopen(wine._private_file(path, os.O_RDONLY), "rb") as source:
            if source.seek(0, os.SEEK_END) > MAX_CATALOG_BYTES:
                raise ValueError("Wine application catalog exceeds size limit")
            source.seek(0)
            payload = json.load(source)
        if (not isinstance(payload, dict) or payload.get("schema") != 1 or
                not isinstance(payload.get("apps"), list) or len(payload["apps"]) > MAX_APPS):
            raise ValueError("Unsupported or malformed Wine application catalog")
        apps = []
        for row in payload["apps"]:
            if not isinstance(row, dict) or set(row) != {
                    "prefix", "identifier", "title", "executable", "arguments", "icon"}:
                raise ValueError("Malformed application record")
            if not isinstance(row["arguments"], list):
                raise ValueError("Malformed application arguments")
            app = WineApplication(row["prefix"], row["identifier"], row["title"],
                                  row["executable"], tuple(row["arguments"]), row["icon"])
            _validate(app)
            if app.prefix != prefix.name or app.identifier in {item.identifier for item in apps}:
                raise ValueError("Invalid prefix or duplicate application ID")
            apps.append(app)
        return apps
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Cannot read Wine application catalog for {prefix.name}") from exc


def _save(prefix: Path, apps: list[WineApplication]) -> None:
    path = prefix / CATALOG
    if path.is_symlink():
        raise RuntimeError("Refusing to overwrite a symlinked catalog")
    payload = json.dumps({"schema": 1, "apps": [asdict(item) for item in apps]},
                         ensure_ascii=False, separators=(",", ":"))
    if len(payload.encode("utf-8")) > MAX_CATALOG_BYTES:
        raise RuntimeError("Wine application catalog size limit exceeded")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=prefix,
                                         prefix=".ricewine-apps-", delete=False) as output:
            temporary = Path(output.name)
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        directory = os.open(prefix, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _modify(prefix: Path, operation):
    with os.fdopen(wine._private_file(prefix / LOCK, os.O_CREAT | os.O_RDWR), "rb+") as guard:
        try:
            fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Wine application catalog is busy") from exc
        apps = _load(prefix)
        result = operation(apps)
        _save(prefix, apps)
        return result


def register(prefix: str, identifier: str, title: str, executable: str,
             arguments: tuple[str, ...] = (), icon: str | None = None, *,
             store: Path | None = None) -> WineApplication:
    app = WineApplication(prefix, identifier, title, executable, arguments, icon)
    _validate(app)
    target = _prefix(prefix, store)

    def add(apps):
        existing = next((item for item in apps if item.identifier == identifier), None)
        if existing is not None:
            if existing != app:
                raise ValueError("App ID already exists; unregister it explicitly first")
            return existing
        if len(apps) >= MAX_APPS:
            raise RuntimeError("Wine application catalog is full")
        apps.append(app)
        return app

    return _modify(target, add)


def unregister(prefix: str, identifier: str, *, store: Path | None = None) -> None:
    if not isinstance(identifier, str) or not APP_ID.fullmatch(identifier):
        raise ValueError("Invalid application ID")
    target = _prefix(prefix, store)

    def remove(apps):
        kept = [item for item in apps if item.identifier != identifier]
        if len(kept) == len(apps):
            raise ValueError("Application registration not found")
        apps[:] = kept

    _modify(target, remove)


def list_apps(*, store: Path | None = None) -> CatalogSnapshot:
    apps, issues = [], []
    for prefix in wine.list_prefixes(store=store):
        if prefix.issue:
            issues.append(prefix.issue)
        elif prefix.ready:
            try:
                apps.extend(_load(Path(prefix.path)))
            except RuntimeError as exc:
                issues.append(str(exc))
    return CatalogSnapshot(tuple(sorted(apps, key=lambda item: (
        item.title.casefold(), item.prefix, item.identifier))), tuple(issues))


def launch_app(prefix: str, identifier: str, *, store: Path | None = None) -> int:
    target = _prefix(prefix, store)
    app = next((item for item in _load(target) if item.identifier == identifier), None)
    if app is None:
        raise ValueError("Application registration not found")
    return wine.launch(prefix, app.executable, app.arguments, store=store)
