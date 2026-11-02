"""Coordinate RiceHub taskbars and opt-in, RiceHub-owned dock processes.

Only terminate processes recorded with their PID and Linux /proc start time.
External user docks/panels are never killed. X11 session only.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

from .installer import project_root

SHELLS = {"aero": "aero-shell", "ten": "windows10-shell"}
STATE = Path("macrice-state/session-processes.json")


def _start_time(pid: int) -> str | None:
    try:
        # /proc/<pid>/stat comm may contain spaces and parentheses.
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]
    except (OSError, IndexError):
        return None


def _state_path() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / STATE


def _read_state() -> dict:
    path = _state_path()
    try:
        if path.is_symlink() or path.stat().st_size > 8192:
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_state(state: dict) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    if path.is_symlink():
        raise OSError("Refusing symlinked session state")
    import tempfile
    fd, name = tempfile.mkstemp(prefix=".session-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(name, 0o600)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def _stop_managed(name: str, state: dict) -> str | None:
    entry = state.pop(name, None)
    if not isinstance(entry, dict):
        return None
    pid, stamp = entry.get("pid"), entry.get("start")
    if not isinstance(pid, int) or pid <= 1 or not isinstance(stamp, str):
        return None
    if _start_time(pid) != stamp:
        return None
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(20):
            if _start_time(pid) != stamp:
                return None
            time.sleep(0.05)
        return f"{name} did not exit after SIGTERM"
    except ProcessLookupError:
        return None
    except PermissionError as exc:
        return f"Cannot stop {name}: {exc}"


def _start_managed(name: str, argv: list[str], state: dict) -> str | None:
    entry = state.get(name)
    if isinstance(entry, dict) and _start_time(entry.get("pid", -1)) == entry.get("start"):
        return None
    try:
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        stamp = _start_time(proc.pid)
        if stamp is None:
            return f"{name} exited immediately"
        state[name] = {"pid": proc.pid, "start": stamp}
    except OSError as exc:
        return f"Cannot start {name}: {exc}"
    return None


def sync_theme(theme: str) -> tuple[str, ...]:
    if not os.environ.get("DISPLAY"):
        return ()
    desired = "aero" if theme == "RiceHub-Aero" else "ten" if theme in (
        "RiceHub-Ten-Dark", "RiceHub-Ten-Light") else None
    state = _read_state()
    warnings: list[str] = []

    # Always stop RiceHub-owned components before launching a conflicting shell.
    for name in ("plank", "macbar") if desired else ():
        warning = _stop_managed(name, state)
        if warning:
            warnings.append(warning)

    for profile, command in SHELLS.items():
        if profile == desired:
            continue
        argv = [sys.executable, str(project_root() / "launcher.py"), command, "--quit"]
        try:
            result = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.PIPE, text=True, timeout=4, check=False)
            if result.returncode:
                warnings.append(f"{profile} taskbar did not quit: {result.stderr.strip()[:160]}")
        except (OSError, subprocess.TimeoutExpired) as exc:
            warnings.append(f"{profile} taskbar did not quit: {exc}")

    if not warnings and desired is not None:
        try:
            subprocess.Popen([sys.executable, str(project_root() / "launcher.py"), SHELLS[desired]],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError as exc:
            warnings.append(f"Could not start {desired} taskbar: {exc}")
    elif not warnings:
        # Never change XFCE panel or externally started instances.
        # MacBar and Plank are launched only if RiceHub can locate the executables.
        for name, executable in (("macbar", "macbar"), ("plank", "plank")):
            binary = shutil.which(executable)
            if binary is None:
                warnings.append(f"{name} not installed; cannot restore macOS desktop")
                continue
            warning = _start_managed(name, [binary], state)
            if warning:
                warnings.append(warning)
    try:
        _write_state(state)
    except OSError as exc:
        warnings.append(f"Could not persist managed session: {exc}")
    return tuple(warnings)
