"""riceWine: minimal, opt-in, unprivileged Wine prefix management.

No package installation, system MIME edits, downloads, prefix deletion, or
background process. This foundation is deliberately independent of rice themes.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path


NAME = re.compile(r"[a-z0-9][a-z0-9_-]{0,47}\Z")
MARKER = ".ricewine-ready"


@dataclass(frozen=True)
class Prefix:
    name: str
    path: str
    ready: bool


def default_store() -> Path:
    data = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    return data / "ricebowl" / "wine-prefixes"


def _name(name: str) -> str:
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise ValueError("Prefix names must be 1–48 lowercase letters, digits, _ or -")
    return name


def _check_dir(path: Path) -> None:
    if path.is_symlink() or not path.is_dir():
        raise RuntimeError(f"Unsafe Wine directory: {path}")
    info = path.stat()
    if info.st_uid != os.getuid() or info.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise RuntimeError(f"Wine directory must be private and owned by you: {path}")


def _store(store: Path | None, *, create: bool = False) -> Path:
    path = store if store is not None else default_store()
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise RuntimeError("Wine prefix store is not a safe directory")
    if create and not path.exists():
        path.mkdir(parents=True, mode=0o700)
    if path.exists():
        _check_dir(path)
    return path


def list_prefixes(*, store: Path | None = None) -> tuple[Prefix, ...]:
    folder = _store(store)
    if not folder.exists():
        return ()
    prefixes = []
    for entry in sorted(folder.iterdir(), key=lambda item: item.name):
        if not NAME.fullmatch(entry.name) or entry.is_symlink() or not entry.is_dir():
            continue
        _check_dir(entry)
        prefixes.append(Prefix(entry.name, str(entry), (entry / MARKER).is_file()
                               and not (entry / MARKER).is_symlink()))
    return tuple(prefixes)


def wine_version() -> str | None:
    command = shutil.which("wine")
    if command is None:
        return None
    try:
        result = subprocess.run([command, "--version"], capture_output=True,
                                text=True, timeout=4, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip()[:120] if result.returncode == 0 else None


def create_prefix(name: str, *, store: Path | None = None, timeout: float = 120) -> Prefix:
    """Initialize one new managed prefix. Failed attempts remain for diagnosis.

    Never adopt or overwrite a user-owned Wine prefix, even when incomplete.
    """
    _name(name)
    if os.geteuid() == 0:
        raise RuntimeError("Do not initialize Wine prefixes as root")
    wineboot = shutil.which("wineboot")
    if wineboot is None:
        raise RuntimeError("wineboot is not installed; install Wine first")
    folder = _store(store, create=True)
    prefix = folder / name
    try:
        prefix.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise RuntimeError("Prefix already exists; it will not be overwritten") from exc
    environment = os.environ.copy()
    environment["WINEPREFIX"] = str(prefix.absolute())
    log = prefix / ".ricewine-init.log"
    try:
        with log.open("xb") as output:
            os.chmod(log, 0o600)
            result = subprocess.run([wineboot, "--init"], env=environment,
                                    stdout=output, stderr=subprocess.STDOUT,
                                    timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"Wine initialization failed; inspect {log}") from exc
    if result.returncode:
        raise RuntimeError(f"Wine initialization exited {result.returncode}; inspect {log}")
    marker = prefix / MARKER
    with marker.open("x", encoding="utf-8") as output:
        output.write("Managed by riceWine; initialization completed.\n")
    os.chmod(marker, 0o600)
    return Prefix(name, str(prefix), True)


def launch(name: str, executable: str, arguments: tuple[str, ...] = (), *,
           store: Path | None = None) -> int:
    """Launch an explicitly selected program; return its PID, never wait for GUI exit."""
    _name(name)
    if os.geteuid() == 0:
        raise RuntimeError("Do not launch Wine as root")
    if not isinstance(executable, str) or not executable or executable.startswith("-"):
        raise ValueError("Select an executable, not a Wine command-line option")
    if any(not isinstance(arg, str) or "\x00" in arg for arg in (executable, *arguments)):
        raise ValueError("Invalid executable or argument")
    wine = shutil.which("wine")
    if wine is None:
        raise RuntimeError("wine is not installed")
    prefix = _store(store) / name
    _check_dir(prefix)
    marker = prefix / MARKER
    if marker.is_symlink() or not marker.is_file():
        raise RuntimeError("Prefix is not initialized by riceWine; refusing to launch")
    environment = os.environ.copy()
    environment["WINEPREFIX"] = str(prefix.absolute())
    try:
        process = subprocess.Popen([wine, executable, *arguments], env=environment,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, close_fds=True,
                                   start_new_session=True)
    except OSError as exc:
        raise RuntimeError("Could not start Wine") from exc
    return process.pid
