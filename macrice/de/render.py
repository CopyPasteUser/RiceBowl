"""Explicit, isolated labwc/RicePlate screenshot for reproducible Creator QA.

This is a headless native-shell preview, not an interactive login session or
an autonomous mockup converter. No processes or state survive the call.
"""

from __future__ import annotations

import json
import hashlib
import os
import re
import secrets
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from . import recipes, review
from .session import resources

DEFAULT_WIDTH = 1366
DEFAULT_HEIGHT = 768
SCALES = (1.0, 1.25, 1.5, 2.0)
REQUIRED = ("labwc", "wlr-randr", "grim", "riceplate-native", "swaybg")


class RenderError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__({
            "invalid_render_request": "Use a valid recipe, geometry and new absolute .png path",
            "render_unavailable": "Requires an unprivileged user and native headless Wayland tools",
            "render_failed": "Isolated Wayland render did not complete",
        }[code])


def _validate_output(output: Path | None, width: int, height: int, scale: float) -> None:
    if (output is None or not output.is_absolute() or output.suffix.lower() != ".png"
            or not output.parent.is_dir() or os.path.lexists(output)
            or not 640 <= width <= 4096 or not 480 <= height <= 2160
            or width * height > 16_777_216 or scale not in SCALES):
        raise RenderError("invalid_render_request")


def _output_name(wlr_randr: str, env: dict[str, str]) -> str:
    reported = subprocess.run([wlr_randr], env=env, capture_output=True,
                              check=True, text=True, timeout=5).stdout
    first = reported.splitlines()[0].split()[0] if reported.strip() else ""
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", first):
        raise RenderError("render_failed")
    return first


def _owned_session_pids(session: int, token: str) -> list[int]:
    """Find surviving children without trusting a recycled process-group ID."""
    marker = f"RICEBOWL_RENDER_SESSION={token}".encode()
    owned = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            fields = (entry / "stat").read_text().rsplit(") ", 1)[1].split()
            if fields[0] == "Z" or int(fields[3]) != session:
                continue
            if marker in (entry / "environ").read_bytes().split(b"\0"):
                owned.append(int(entry.name))
        except (OSError, ValueError, IndexError):
            continue  # Exited between the stat and environment reads.
    return owned


def _signal_owned(session: int, token: str, sig: signal.Signals) -> None:
    """Pin each matching PID before signalling; never kill a recycled group."""
    for pid in _owned_session_pids(session, token):
        try:
            fd = os.pidfd_open(pid)
        except ProcessLookupError:
            continue
        try:
            # Revalidate after opening the stable pidfd to close the PID-reuse race.
            if pid in _owned_session_pids(session, token):
                signal.pidfd_send_signal(fd, sig)
        except ProcessLookupError:
            pass
        finally:
            os.close(fd)


def _stop(process: subprocess.Popen[bytes], token: str | None = None) -> None:
    """Stop the leader's owned group, including orphans after leader exit."""
    if process.poll() is None:
        try:
            # An unreaped child pins its PID, so the group cannot be recycled.
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            process.wait(timeout=3)
    else:
        process.wait()

    if token is not None:
        # The session can outlive its leader. A random inherited marker and
        # pidfd allow killing its descendants without signalling unrelated PIDs.
        for sig, seconds in ((signal.SIGTERM, 0.3), (signal.SIGKILL, 1.0)):
            if not _owned_session_pids(process.pid, token):
                break
            _signal_owned(process.pid, token, sig)
            deadline = time.monotonic() + seconds
            while _owned_session_pids(process.pid, token) and time.monotonic() < deadline:
                time.sleep(0.05)
        if _owned_session_pids(process.pid, token):
            raise OSError("owned renderer session did not terminate")


def _cleanup_children(children: list[subprocess.Popen[bytes]],
                      token: str | None = None) -> None:
    """Attempt every teardown even when one child refuses to exit."""
    errors: list[Exception] = []
    for child in reversed(children):
        try:
            _stop(child, token)
        except (OSError, subprocess.SubprocessError) as exc:
            errors.append(exc)
    if errors:
        raise RenderError("render_failed") from errors[0]


def _verify_stage(stage: Path, capture: dict[str, object]) -> None:
    """Check the captured regular file matches the subprocess's sealed receipt."""
    descriptor = os.open(stage, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size != capture.get("bytes"):
            raise RenderError("render_failed")
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != capture.get("sha256"):
        raise RenderError("render_failed")


def render(recipe_token: str | None, output: Path | None, *,
           width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT,
           scale: float = 1.0) -> dict[str, object]:
    """Render one validated recipe with a private headless compositor, then exit."""
    _validate_output(output, width, height, scale)
    if not recipe_token:
        raise RenderError("invalid_render_request")
    try:
        recipe = recipes.load(recipe_token)
    except recipes.RecipeError as exc:
        raise RenderError("invalid_render_request") from exc
    if os.geteuid() == 0:
        raise RenderError("render_unavailable")
    binary = {name: shutil.which(name) for name in REQUIRED}
    if any(value is None for value in binary.values()):
        raise RenderError("render_unavailable")
    assert output is not None
    image_path = recipes.wallpaper_path(recipe)
    launcher = Path(__file__).resolve().parents[2] / "launcher.py"
    if not image_path.is_file() or not launcher.is_file():
        raise RenderError("render_unavailable")

    try:
        with tempfile.TemporaryDirectory(prefix="ricebowl-render-") as runtime, \
             tempfile.TemporaryDirectory(prefix=".ricebowl-render-", dir=output.parent) as staging:
            env = dict(os.environ)
            env.update({"XDG_RUNTIME_DIR": runtime, "WLR_BACKENDS": "headless",
                        "WLR_HEADLESS_OUTPUTS": "1", "WLR_RENDERER": "pixman",
                        "RICEBOWL_DE_NESTED": "1", "LABWC_UPDATE_ACTIVATION_ENV": "0"})
            token = secrets.token_hex(16)
            env["RICEBOWL_RENDER_SESSION"] = token
            env.pop("WAYLAND_DISPLAY", None)
            env.pop("DISPLAY", None)
            children: list[subprocess.Popen[bytes]] = []
            try:
                compositor = subprocess.Popen(
                    [binary["labwc"], "--config-dir", str(resources() / "labwc"),
                     "--startup", "true"], env=env, stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                children.append(compositor)
                socket = Path(runtime) / "wayland-0"
                deadline = time.monotonic() + 10
                while not socket.is_socket():
                    if compositor.poll() is not None or time.monotonic() >= deadline:
                        raise RenderError("render_failed")
                    time.sleep(0.1)
                env["WAYLAND_DISPLAY"] = "wayland-0"
                # The socket can appear before the output registry is ready.
                deadline = time.monotonic() + 4
                while True:
                    try:
                        screen = _output_name(binary["wlr-randr"], env)
                        break
                    except (RenderError, subprocess.SubprocessError, IndexError):
                        if compositor.poll() is not None or time.monotonic() >= deadline:
                            raise RenderError("render_failed") from None
                        time.sleep(0.2)
                subprocess.run([binary["wlr-randr"], "--output", screen,
                                "--custom-mode", f"{width}x{height}@60Hz",
                                "--scale", str(scale)], env=env, timeout=8, check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                for command in ([binary["swaybg"], "--image", str(image_path), "--mode", "fill"],
                                [binary["riceplate-native"], "--recipe",
                                 recipes.native_token(recipe_token)]):
                    child = subprocess.Popen(command, env=env, stdin=subprocess.DEVNULL,
                                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                             start_new_session=True)
                    children.append(child)
                time.sleep(1)
                if any(child.poll() is not None for child in children):
                    raise RenderError("render_failed")
                stage = Path(staging) / "capture.png"
                capture = subprocess.Popen(
                    [sys.executable, str(launcher), "de", "capture", "--output", str(stage),
                     "--json"], env=env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                    start_new_session=True)
                children.append(capture)
                stdout, _ = capture.communicate(timeout=35)
                if capture.returncode != 0:
                    raise RenderError("render_failed")
                receipt = json.loads(stdout)
                if (not isinstance(receipt, dict) or receipt.get("ok") is not True
                        or not isinstance(receipt.get("capture"), dict)
                        or receipt["capture"].get("width") != width
                        or receipt["capture"].get("height") != height):
                    raise RenderError("render_failed")
                result = {
                    "render_version": 1,
                    "source": "isolated-headless-labwc-native-riceplate",
                    "recipe": {"id": recipe.recipe_id, "schema_version": recipe.schema_version,
                               "semantic_sha256": review._semantic_hash(review._manifest(recipe))},
                    "output": {**receipt["capture"], "path": str(output)},
                    "geometry": {"width": width, "height": height, "scale": scale},
                    "mutates_active_desktop": False,
                    "interactive_session": False,
                }
            finally:
                _cleanup_children(children, token)
            # Publish only after teardown succeeds. This preserves the destination
            # when even a successful screenshot leaves an orphaned process.
            _verify_stage(stage, receipt["capture"])
            os.link(stage, output, follow_symlinks=False)
            return result
    except RenderError:
        raise
    except (OSError, IndexError, KeyError, ValueError, subprocess.SubprocessError) as exc:
        raise RenderError("render_failed") from exc
