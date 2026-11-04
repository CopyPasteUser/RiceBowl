"""Separate XP Luna StatusNotifier preferences; shared verified storage format."""

from __future__ import annotations

import os
from pathlib import Path


def preferences_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "ricehub" / "winxp-tray.json"
