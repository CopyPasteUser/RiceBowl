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

from .environment import bin_home, data_home
from .installer import project_root

SHELLS = {"aero": "aero-shell", "ten": "windows10-shell"}
MAC_THEMES = ("WhiteSur-Dark", "WhiteSur-Light")
MACBAR_APP_ID = "io.github.macbar.panel"


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
                    (proc / "cmdline").read_bytes().split(b"\0") if part]
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


def _component_executable(name: str) -> str | None:
    """Find RiceHub-managed binaries even when XFCE starts the hub with a minimal PATH."""
    if name == "macbar":
        local = bin_home() / "macbar"
        if local.is_file() and os.access(local, os.X_OK):
            return str(local)
    return shutil.which(name)


def _macbar_bus_owned() -> bool | None:
    """Check the actual Gtk.Application bus owner, not only the process name.

    None means the session bus could not be queried; it does not mean absent.
    """
    try:
        import gi

        gi.require_version("Gio", "2.0")
        from gi.repository import Gio, GLib

        connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        response = connection.call_sync(
            "org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus",
            "NameHasOwner", GLib.Variant("(s)", (MACBAR_APP_ID,)), GLib.VariantType("(b)"),
            Gio.DBusCallFlags.NONE, 1500, None,
        )
        return bool(response.unpack()[0])
    except Exception:
        # PyGObject raises GLib.Error for an unavailable or closing session bus.
        # Treat this as unknown rather than incorrectly declaring MacBar absent.
        return None


def _macbar_owner_pid() -> int | None:
    """Resolve MacBar's D-Bus primary to a verified current-user process."""
    try:
        import gi

        gi.require_version("Gio", "2.0")
        from gi.repository import Gio, GLib

        connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        response = connection.call_sync(
            "org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus",
            "GetConnectionUnixProcessID", GLib.Variant("(s)", (MACBAR_APP_ID,)),
            GLib.VariantType("(u)"), Gio.DBusCallFlags.NONE, 1500, None,
        )
        pid = int(response.unpack()[0])
        proc = Path(f"/proc/{pid}")
        if pid != os.getpid() and proc.stat().st_uid == os.getuid():
            args = [part.decode("utf-8", "replace") for part in
                    (proc / "cmdline").read_bytes().split(b"\0") if part]
            if any(Path(arg).name == "macbar.py" for arg in args[1:]):
                return pid
    except Exception:
        # Bus/owner may disappear during reconciliation; never guess a PID.
        return None
    return None


def _managed_macbar_pids() -> list[int]:
    """Identify only the installed MacBar script, never arbitrary Python apps."""
    expected = str(data_home() / "macbar/macbar.py")
    pids = []
    for proc in Path("/proc").glob("[0-9]*"):
        try:
            if proc.stat().st_uid != os.getuid():
                continue
            args = [part.decode("utf-8", "replace") for part in
                    (proc / "cmdline").read_bytes().split(b"\0") if part]
            if expected in args[1:] and int(proc.name) != os.getpid():
                pids.append(int(proc.name))
        except (OSError, ValueError):
            continue
    return pids


def _stop_macbar() -> list[str]:
    """Stop only verified MacBar PIDs; gapplication has no `quit` command."""
    active = _macbar_bus_owned()
    process_active = _macbar_running()
    if active is not True and not process_active:
        return []
    targets = set(_managed_macbar_pids())
    if active is True:
        owner_pid = _macbar_owner_pid()
        if owner_pid is not None:
            targets.add(owner_pid)
    if not targets:
        return ["MacBar is running but RiceHub could not verify its user-owned PID"]
    errors = []
    for pid in sorted(targets):
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            continue
        except PermissionError as exc:
            errors.append(f"MacBar PID {pid}: {exc}")
    if errors:
        return errors
    for _ in range(20):
        if not _macbar_running() and _macbar_bus_owned() is not True:
            return []
        time.sleep(0.1)
    return ["MacBar is still running after SIGTERM"]


def _stop_xfce_panel() -> list[str]:
    """Gracefully quit XFCE's stock panel after the replacement is running."""
    if not _processes("xfce4-panel"):
        return []
    executable = shutil.which("xfce4-panel")
    if not executable:
        return ["XFCE panel is running but its executable is unavailable"]
    try:
        result = subprocess.run([executable, "--quit"], capture_output=True, text=True,
                                timeout=4, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [f"XFCE panel quit failed: {exc}"]
    if result.returncode:
        return [f"XFCE panel quit rejected: {result.stderr.strip()[:160]}"]
    for _ in range(20):
        if not _processes("xfce4-panel"):
            return []
        time.sleep(0.1)
    return ["XFCE panel did not exit after --quit"]


def _activate_session_controls(theme: str) -> list[str]:
    """Install recoverable shortcuts, then retire the stock XFCE panel."""
    from .session_shortcuts import install_bindings
    try:
        warnings = list(install_bindings(theme))
    except (OSError, ValueError, RuntimeError) as exc:
        return [f"RiceHub shortcuts: {exc}"]
    if warnings:
        return warnings
    return _stop_xfce_panel()


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
        # Keep real GTK/X11 errors available when a taskbar exits later.
        # No watchdog or extra resident process is needed.
        root = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "ricehub"
        if root.is_symlink() or (root.exists() and (not root.is_dir() or root.stat().st_uid != os.getuid())):
            return ["Unmanaged RiceHub diagnostic log location"]
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        log = root / f"{profile}-shell.log"
        if log.is_symlink() or (log.exists() and (not log.is_file() or log.stat().st_uid != os.getuid())):
            return ["Unmanaged RiceHub taskbar log"]
        if log.exists() and log.stat().st_size > 256 * 1024:
            log.write_text("", encoding="utf-8")
        with log.open("ab") as output:
            os.chmod(log, 0o600)
            subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=output,
                             stderr=subprocess.STDOUT, close_fds=True, start_new_session=True)
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
        # MacBar runs under python3, so process-name matching is not enough.
        warnings.extend(_stop_macbar())
        if not warnings:
            warnings.extend(_shell(desired, False))
    elif mac:
        for name in ("plank", "macbar"):
            executable = _component_executable(name)
            if executable:
                warnings.extend(_start(name, [executable]))
            else:
                warnings.append(f"{name} executable not found")
    if not warnings and (desired or mac):
        warnings.extend(_activate_session_controls(theme))
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
