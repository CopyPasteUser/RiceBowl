"""Rice-aware XFCE shortcuts. Preserve the user's previous key assignments."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

from .environment import bin_home, private_state_root


CHANNEL = "xfce4-keyboard-shortcuts"
KEY_COMMANDS = {"Super_L": "session-menu", "Control_R": "session-control"}
STATE_FILE = "session-shortcuts.json"


def command_for(action: str, theme: str) -> tuple[str, ...]:
    if action not in ("menu", "control"):
        raise ValueError("Unknown RiceHub shortcut action")
    if theme in ("RiceHub-Ten-Dark", "RiceHub-Ten-Light"):
        return ("macrice", "windows10-shell", "--toggle-menu" if action == "menu" else "--actions")
    if theme == "RiceHub-Aero":
        return ("macrice", "aero-shell", "--toggle-menu") if action == "menu" else (
            "macrice", "aero-shell", "--control")
    return ("macmenu", "--toggle") if action == "menu" else ("macos-control-center-toggle",)


def dispatch(action: str) -> None:
    result = subprocess.run(
        ["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName"],
        capture_output=True, text=True, timeout=3, check=False,
    )
    if result.returncode:
        raise RuntimeError("Could not read active XFCE theme for shortcut routing")
    command = command_for(action, result.stdout.strip())
    if command[0] in ("macrice", "macmenu", "macos-control-center-toggle"):
        executable = bin_home() / command[0]
        if not executable.is_file():
            raise RuntimeError(f"{command[0]} is not installed")
        argv = [str(executable), *command[1:]]
    else:
        executable = shutil.which(command[0])
        if executable is None:
            raise RuntimeError(f"{command[0]} is not installed")
        argv = [executable, *command[1:]]
    subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True)


def _property(key: str) -> str:
    if key not in KEY_COMMANDS:
        raise ValueError("Unknown RiceHub-managed key")
    return f"/commands/custom/{key}"


def _read(key: str) -> str | None:
    result = subprocess.run(["xfconf-query", "-c", CHANNEL, "-p", _property(key)],
                            capture_output=True, text=True, timeout=3, check=False)
    if result.returncode == 0:
        return result.stdout.rstrip("\n")
    if "does not exist" in result.stderr.lower():
        return None
    raise RuntimeError(f"Could not read shortcut {key}: {result.stderr.strip()[:150]}")


def _write(key: str, command: str | None) -> None:
    path = _property(key)
    if command is None:
        argv = ["xfconf-query", "-c", CHANNEL, "-p", path, "-r"]
    else:
        argv = ["xfconf-query", "-c", CHANNEL, "-p", path, "-n", "-t", "string", "-s", command]
    result = subprocess.run(argv, capture_output=True, text=True, timeout=3, check=False)
    if result.returncode:
        raise RuntimeError(f"Could not assign {key}: {result.stderr.strip()[:150]}")


def _state_path(state_dir: Path | None = None) -> Path:
    root = state_dir if state_dir is not None else private_state_root()
    path = root / STATE_FILE
    if path.is_symlink() or (path.exists() and (not path.is_file() or path.stat().st_uid != os.getuid())):
        raise RuntimeError("RiceHub shortcut recovery file is not a user-owned regular file")
    return path


def _save(path: Path, state: dict) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".ricehub-keys-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(state, stream, indent=2, sort_keys=True)
            stream.write("\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def _load(path: Path) -> dict | None:
    if not path.exists():
        return None
    state = json.loads(path.read_text(encoding="utf-8"))
    if (state.get("version") != 1 or set(state.get("original", {})) != set(KEY_COMMANDS)
            or set(state.get("managed", {})) != set(KEY_COMMANDS)):
        raise RuntimeError("Invalid RiceHub shortcut recovery file; refusing to replace shortcuts")
    return state


def install_bindings(*, state_dir: Path | None = None, launcher: Path | None = None) -> tuple[str, ...]:
    path = _state_path(state_dir)
    cli = launcher or bin_home() / "macrice"
    commands = {key: f"{shlex.quote(str(cli))} {action}" for key, action in KEY_COMMANDS.items()}
    current = {key: _read(key) for key in KEY_COMMANDS}
    state = _load(path)
    if state is None:
        state = {"version": 1, "original": current, "managed": commands}
        _save(path, state)  # Back up before changing a single Xfce shortcut.
    warnings = []
    changed = []
    try:
        for key in KEY_COMMANDS:
            if current[key] == commands[key]:
                continue
            if current[key] not in (state["original"][key], state["managed"][key]):
                warnings.append(f"Preserved modified shortcut {key}; change it in XFCE Keyboard settings")
                continue
            _write(key, commands[key])
            changed.append(key)
    except Exception:
        for key in reversed(changed):
            _write(key, current[key])
        raise
    if state["managed"] != commands:
        _save(path, {**state, "managed": commands})
    return tuple(warnings)


def restore_bindings(*, state_dir: Path | None = None) -> tuple[str, ...]:
    path = _state_path(state_dir)
    state = _load(path)
    if state is None:
        return ()
    warnings = []
    for key in KEY_COMMANDS:
        current = _read(key)
        if current == state["managed"][key]:
            _write(key, state["original"][key])
        elif current != state["original"][key]:
            warnings.append(f"Preserved user-edited shortcut {key}")
    path.unlink()
    return tuple(warnings)
