"""Opt-in, private and bounded Frutiger taskbar interaction evidence.

Only fixed UI target names and Boolean visibility are ever recorded. In
particular no window titles, launcher names, SSIDs or application IDs leak.
"""

from __future__ import annotations

import json
import logging
import os
import stat
from datetime import datetime, timezone
from pathlib import Path


MAX_BYTES = 65536
TARGETS = frozenset((
    "session", "start", "network", "audio", "battery", "bluetooth",
    "drives", "notifications", "calendar", "app-pin",
))
EVENTS = frozenset(("begin", "end", "click", "result", "dispatch"))


def trace_path(environment=None, *, user_home: Path | None = None) -> Path:
    env = os.environ if environment is None else environment
    root = env.get("XDG_CACHE_HOME", "")
    cache = Path(root) if root and Path(root).is_absolute() else (
        (user_home or Path.home()) / ".cache")
    return cache / "ricebowl" / "frutiger-interactions.jsonl"


class InteractionTrace:
    def __init__(self, path: Path | None = None):
        self.path = path or trace_path()
        self.enabled = False

    def start(self) -> None:
        self._append("begin", "session", None)
        self.enabled = True

    def stop(self) -> None:
        if self.enabled:
            self.record("end", "session")
            self.enabled = False

    def record(self, event: str, target: str, visible: bool | None = None) -> None:
        if not self.enabled:
            return
        try:
            self._append(event, target, visible)
        except OSError as exc:
            self.enabled = False
            logging.getLogger(__name__).warning("Aqua interaction trace stopped: %s", exc)

    def _append(self, event: str, target: str, visible: bool | None) -> None:
        if event not in EVENTS or target not in TARGETS or not (
                visible is None or isinstance(visible, bool)):
            raise ValueError("Invalid interaction trace event")
        parent = self.path.parent
        parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        directory = parent.lstat()
        if not stat.S_ISDIR(directory.st_mode) or directory.st_uid != os.getuid() or (
                stat.S_IMODE(directory.st_mode) & 0o077):
            raise OSError("Private ricebowl cache directory is unavailable (requires owner-only 0700)")
        record = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "event": event, "target": target}
        if visible is not None:
            record["visible"] = visible
        line = (json.dumps(record, separators=(",", ":")) + "\n").encode("utf-8")
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(self.path, flags, 0o600)
        try:
            current = os.fstat(fd)
            if (not stat.S_ISREG(current.st_mode) or current.st_uid != os.getuid()
                    or stat.S_IMODE(current.st_mode) & 0o077):
                raise OSError("Private interaction trace file has unsafe permissions")
            if current.st_size + len(line) > MAX_BYTES:
                os.ftruncate(fd, 0)
            os.write(fd, line)
        finally:
            os.close(fd)
