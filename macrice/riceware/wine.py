"""riceWine: minimal, opt-in, unprivileged Wine prefix management.

No package installation, system MIME edits, downloads, prefix deletion, or
background process. This foundation is deliberately independent of rice themes.
"""

from __future__ import annotations

import fcntl
import os
import re
import shutil
import signal
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path


NAME = re.compile(r"[a-z0-9][a-z0-9_-]{0,47}\Z")
MARKER = ".ricewine-ready"
INIT_LOG = ".ricewine-init.log"
INIT_LOCK = ".ricewine-init.lock"


@dataclass(frozen=True)
class Prefix:
    name: str
    path: str
    ready: bool
    issue: str | None = None


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
        try:
            _check_dir(entry)
        except RuntimeError as exc:
            prefixes.append(Prefix(entry.name, str(entry), False, str(exc)))
            continue
        prefixes.append(Prefix(entry.name, str(entry), _is_ready(entry)))
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


def _is_ready(prefix: Path) -> bool:
    marker, registry = prefix / MARKER, prefix / "system.reg"
    try:
        return (not marker.is_symlink() and marker.is_file() and
                not registry.is_symlink() and registry.is_file() and
                registry.stat().st_size > 0)
    except OSError:
        return False


def _private_file(path: Path, flags: int) -> int:
    """Open only an owned, private regular file; never follow a symlink."""
    fd = os.open(path, flags | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    info = os.fstat(fd)
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or
            info.st_mode & (stat.S_IRWXG | stat.S_IRWXO)):
        os.close(fd)
        raise RuntimeError(f"Unsafe riceWine managed file: {path}")
    return fd


def _validate_timeout(timeout: float) -> None:
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 5 <= timeout <= 600:
        raise ValueError("Wine initialization timeout must be 5–600 seconds")


def _initialize(prefix: Path, wineboot: str, timeout: float) -> Prefix:
    lock = prefix / INIT_LOCK
    log = prefix / INIT_LOG
    with os.fdopen(_private_file(lock, os.O_CREAT | os.O_RDWR), "rb+") as guard:
        try:
            fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Wine prefix initialization is already running") from exc
        if _is_ready(prefix):
            raise RuntimeError("Prefix is already initialized")
        environment = os.environ.copy()
        environment["WINEPREFIX"] = str(prefix.absolute())
        with os.fdopen(_private_file(log, os.O_CREAT | os.O_WRONLY | os.O_APPEND), "ab") as output:
            try:
                process = subprocess.Popen([wineboot, "--init"], env=environment,
                                           stdin=subprocess.DEVNULL, stdout=output,
                                           stderr=subprocess.STDOUT, close_fds=True,
                                           start_new_session=True)
                try:
                    code = process.wait(timeout=timeout)
                except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
                    # Kill only the process group we started, never another Wine prefix.
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait(timeout=5)
                    if isinstance(exc, KeyboardInterrupt):
                        raise RuntimeError(f"Wine initialization cancelled; inspect {log}") from exc
                    raise RuntimeError(f"Wine initialization timed out; inspect {log}") from exc
            except OSError as exc:
                raise RuntimeError(f"Wine initialization failed; inspect {log}") from exc
        if code:
            raise RuntimeError(f"Wine initialization exited {code}; inspect {log}")
        # A zero exit code is not proof that Wine actually initialized a prefix.
        registry = prefix / "system.reg"
        if registry.is_symlink() or not registry.is_file() or registry.stat().st_size == 0:
            raise RuntimeError(f"Wine returned success but created no registry; inspect {log}")
        marker = prefix / MARKER
        with os.fdopen(_private_file(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY),
                       "w", encoding="utf-8") as output:
            output.write("Managed by riceWine; initialization completed.\n")
    return Prefix(prefix.name, str(prefix), True)


def create_prefix(name: str, *, store: Path | None = None, timeout: float = 120) -> Prefix:
    """Create only a new prefix; leave any failed initialization available for repair."""
    _name(name)
    _validate_timeout(timeout)
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
    return _initialize(prefix, wineboot, timeout)


def resume_prefix(name: str, *, store: Path | None = None, timeout: float = 120) -> Prefix:
    """Retry only an incomplete prefix previously started by riceWine."""
    _name(name)
    _validate_timeout(timeout)
    if os.geteuid() == 0:
        raise RuntimeError("Do not initialize Wine prefixes as root")
    wineboot = shutil.which("wineboot")
    if wineboot is None:
        raise RuntimeError("wineboot is not installed; install Wine first")
    prefix = _store(store) / name
    _check_dir(prefix)
    log = prefix / INIT_LOG
    if log.is_symlink() or not log.is_file() or (prefix / MARKER).exists():
        raise RuntimeError("This is not an incomplete riceWine-managed prefix")
    return _initialize(prefix, wineboot, timeout)


def read_init_log(name: str, *, store: Path | None = None, limit: int = 4096) -> str:
    """Read a bounded diagnostic tail; never expose the log automatically."""
    _name(name)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 65536:
        raise ValueError("Diagnostic limit must be 1–65536 bytes")
    prefix = _store(store) / name
    _check_dir(prefix)
    with os.fdopen(_private_file(prefix / INIT_LOG, os.O_RDONLY), "rb") as source:
        source.seek(0, os.SEEK_END)
        source.seek(max(0, source.tell() - limit))
        content = source.read().decode("utf-8", errors="replace")
        return "".join(char for char in content if char.isprintable() or char in "\n\t")


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
    if not _is_ready(prefix):
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
    try:
        code = process.wait(timeout=0.15)
    except subprocess.TimeoutExpired:
        return process.pid
    if code != 0:
        raise RuntimeError(f"Wine exited immediately with status {code}")
    # Zero only confirms that the Wine launcher exited, not the GUI app's health.
    return process.pid
