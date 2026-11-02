"""Coordinate RiceHub taskbars, Plank and MacBar in an X11 session.

Plank is user-owned: never change its launchers or its autostart file.
Instead a RiceHub login reconciler corrects the chosen session after login.
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from .installer import project_root

SHELLS = {"aero": "aero-shell", "ten": "windows10-shell"}
MAC_THEMES = ("WhiteSur-Dark", "WhiteSur-Light")


def _processes(name: str) -> list[int]:
    """Exact executable-name match, restricted to the current UID."""
    try:
        result = subprocess.run(["pgrep", "-x", "-u", str(os.getuid()), name],
                                capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode not in (0, 1):
        return []
    return [int(p) for p in result.stdout.split() if p.isdecimal() and int(p) != os.getpid()]


def _macbar_running() -> bool:
    """Find only the Python MacBar entrypoint, not arbitrary Python apps."""
    for proc in Path("/proc").glob("[0-9]*"):
        try:
            if proc.stat().st_uid != os.getuid():
                continue
            args = [part.decode("utf-8", "replace") for part in
                    (proc / "cmdline").read_bytes().split(b"\\0") if part]
            if any(Path(arg).name == "macbar.py" for arg in args[1:]):
                return True
        except (OSError, ValueError):
            continue
    return False


def _stop(name: str) -> list[str]:
    errors = []
    for pid in _processes(name):
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            continue
        except PermissionError as exc:
            errors.append(f"{name} PID {pid}: {exc}")
    if not errors:
        for _ in range(15):
            if not _processes(name):
                break
            time.sleep(0.1)
        else:
            errors.append(f"{name} did not exit")
    return errors


def _start(name: str, argv: list[str]) -> list[str]:
    if (_macbar_running() if name == "macbar" else bool(_processes(name))):
        return []
    try:
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        time.sleep(0.08)
        if proc.poll() is not None and proc.returncode != 0:
            return [f"{name} exited with status {proc.returncode}"]
    except OSError as exc:
        return [f"Cannot start {name}: {exc}"]
    return []


def _shell(profile: str, quit: bool) -> list[str]:
    argv = [sys.executable, str(project_root() / "launcher.py"), SHELLS[profile]]
    if quit:
        argv.append("--quit")
        try:
            result = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.PIPE, text=True, timeout=4, check=False)
            return [] if result.returncode == 0 else [f"{profile} taskbar: {result.stderr.strip()[:160]}"]
        except (OSError, subprocess.TimeoutExpired) as exc:
            return [f"{profile} taskbar: {exc}"]
    try:
        subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
        return []
    except OSError as exc:
        return [f"{profile} taskbar: {exc}"]


def sync_theme(theme: str) -> tuple[str, ...]:
    """Reconcile the live session; no process or desktop changes without DISPLAY."""
    if not os.environ.get("DISPLAY"):
        return ()
    desired = "aero" if theme == "RiceHub-Aero" else "ten" if theme in (
        "RiceHub-Ten-Dark", "RiceHub-Ten-Light") else None
    mac = theme in MAC_THEMES
    warnings = []
    # Exit inactive GTK shells before launching the replacement.
    for profile in SHELLS:
        if profile != desired:
            warnings.extend(_shell(profile, True))
    if warnings:
        return tuple(warnings)
    if desired:
        # Plank may have been started by XFCE autostart, not by RiceHub.
        warnings.extend(_stop("plank"))
        # MacBar often runs as python3; use its GTK application ID.
        if shutil.which("gapplication"):
            try:
                result = subprocess.run(
                    ["gapplication", "quit", "io.github.macbar.panel"],
                    capture_output=True, text=True, timeout=4, check=False,
                )
                if result.returncode and _macbar_running():
                    warnings.append("MacBar could not quit: " + result.stderr.strip()[:120])
            except (OSError, subprocess.TimeoutExpired) as exc:
                warnings.append(f"MacBar quit request failed: {exc}")
        else:
            warnings.extend(_stop("macbar"))
        if not warnings:
            warnings.extend(_shell(desired, False))
    elif mac:
        for name in ("plank", "macbar"):
            executable = shutil.which(name)
            if executable:
                warnings.extend(_start(name, [executable]))
            else:
                warnings.append(f"{name} executable not found")
    return tuple(warnings)


def login_reconcile() -> tuple[str, ...]:
    """Run after XFCE autostart; user's Plank autostart remains unchanged."""
    if not os.environ.get("DISPLAY"):
        return ()
    try:
        result = subprocess.run(["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName"],
                                capture_output=True, text=True, timeout=4, check=False)
        if result.returncode:
            return (f"Cannot detect selected theme: {result.stderr.strip()[:160]}",)
        return sync_theme(result.stdout.strip())
    except (OSError, subprocess.TimeoutExpired) as exc:
        return (f"Cannot inspect session: {exc}",)

def install_login_reconciler(config_root: Path | None = None) -> None:
    """Opt-in user-local late autostart. Preserve all existing user entries."""
    from .environment import config_home, bin_home
    root = config_root or config_home()
    target = root / "autostart/ricehub-session-sync.desktop"
    command = bin_home() / "macrice"
    content = ("[Desktop Entry]\\nType=Application\\nName=RiceHub Session Reconcile\\n"
               f"Exec={command} session-sync\\n"
               "OnlyShowIn=XFCE;\\nTerminal=false\\n"
               "X-XFCE-Autostart-Delay=12\\n"
               "# RiceHub managed session reconcile\\n")
    content = content.replace("\\n", "\n")
    if target.is_symlink() or target.parent.is_symlink():
        raise OSError("Unmanaged session autostart symlink")
    if target.exists() and target.read_text(encoding="utf-8") != content:
        raise OSError("Existing session autostart was customized; refusing overwrite")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        with target.open("x", encoding="utf-8") as f:
            f.write(content)
