"""Explicit, reversible resource preferences for the existing Control Center.

Light/Balanced/Visual map to its tested Light/Balanced/Responsive policies.
No always-running profile daemon, silent hardware guesses or extra dependencies.
"""

from __future__ import annotations

import os
import shutil
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from .environment import config_home, data_home, private_state_root
from .shell_session import SHELLS
from .themes import _read_preferences, _stage_json


RICEBOWL_NAMES = {
    "aero": "RiceBowl Windows 7", "ten": "RiceBowl Windows 10",
    "winxp": "RiceBowl XP Luna", "winclassic": "RiceBowl Windows 98 SE",
    "chromeos": "RiceBowl ChromeOS", "frutiger": "RiceBowl Frutiger Aero",
}


PROFILES = {
    "light": {
        "resource_profile": "light", "animation_speed": "off",
        "reduce_motion": True, "media_thumbnail": False,
    },
    "balanced": {
        "resource_profile": "balanced", "animation_speed": "fast",
        "reduce_motion": False, "media_thumbnail": True,
    },
    "visual": {
        "resource_profile": "responsive", "animation_speed": "smooth",
        "reduce_motion": False, "media_thumbnail": True,
    },
}


def _component(argv: list[str]) -> str | None:
    if any(Path(arg).name == "launcher.py" for arg in argv[:3]):
        for profile, title in RICEBOWL_NAMES.items():
            if SHELLS[profile] in argv[2:5]:
                return title
    if any(argv[i:i + 2] == ["-m", "macmenu"] for i in range(len(argv) - 1)):
        return "MacMenu"
    names = {Path(arg).name for arg in argv[:4]}
    if "macos-control-center" in names:
        return "Control Center"
    if "macbar.py" in names or "macbar" in names:
        return "MacBar"
    if argv and Path(argv[0]).name == "plank":
        return "Plank"
    return None


def _process_ticks(process: Path) -> int | None:
    try:
        # The command name in stat may contain spaces or parentheses.
        fields = (process / "stat").read_text().rsplit(") ", 1)[1].split()
        return int(fields[11]) + int(fields[12])
    except (IndexError, OSError, ValueError):
        return None


def _process_threads(process: Path) -> int | None:
    try:
        for line in (process / "status").read_text().splitlines():
            if line.startswith("Threads:"):
                return int(line.split()[1])
    except (IndexError, OSError, ValueError):
        pass
    return None


def measure_processes(*, proc_root: Path = Path("/proc"), sample_ms: int = 200) -> list[dict]:
    """On-demand PSS/CPU report. Never runs as a resident background monitor."""
    processes = []
    uid = os.getuid()
    for process in proc_root.iterdir():
        if not process.name.isdecimal():
            continue
        try:
            if process.stat().st_uid != uid:
                continue
            argv = (process / "cmdline").read_bytes()[:8192].decode("utf-8", "replace").rstrip("\0").split("\0")
            name = _component(argv)
            if not name:
                continue
            pss = None
            try:
                for line in (process / "smaps_rollup").read_text().splitlines():
                    if line.startswith("Pss:"):
                        pss = int(line.split()[1])
                        break
            except (OSError, ValueError):
                pass
            processes.append({"name": name, "pid": int(process.name), "pss_kib": pss,
                              "ticks": _process_ticks(process), "threads": _process_threads(process),
                              "path": process})
        except (OSError, ValueError):
            continue
    if not processes:
        return []
    start = time.monotonic()
    time.sleep(max(50, min(sample_ms, 1000)) / 1000)
    elapsed = max(0.001, time.monotonic() - start)
    ticks_per_second = os.sysconf("SC_CLK_TCK")
    result = []
    for item in processes:
        latest = _process_ticks(item["path"])
        delta = max(0, latest - item["ticks"]) if latest is not None and item["ticks"] is not None else None
        result.append({"name": item["name"], "pid": item["pid"], "pss_kib": item["pss_kib"],
                       "threads": item["threads"],
                       "cpu_percent": round(100 * delta / (elapsed * ticks_per_second), 1) if delta is not None else None})
    return result


def summarize_samples(samples: list[list[dict]]) -> dict:
    """Median per-PID resource snapshot; absent counters stay explicitly unknown.

    PSS estimates unique resident footprint; summing RSS would double count
    shared libraries. Per-process CPU is a one-core percentage, not a machine
    total, and sampling does not run unless explicitly requested.
    """
    grouped = {}
    for sample in samples:
        for item in sample:
            key = (item["name"], item["pid"])
            grouped.setdefault(key, []).append(item)
    components = []
    for (name, pid), readings in sorted(grouped.items()):
        medians = {}
        for field in ("pss_kib", "cpu_percent", "threads"):
            values = [item[field] for item in readings if item[field] is not None]
            medians[field] = round(statistics.median(values), 1) if values else None
        components.append({"name": name, "pid": pid, "observations": len(readings),
                           **medians})
    totals = {field: [] for field in ("pss_kib", "cpu_percent")}
    partial = False
    for sample in samples:
        for field in totals:
            observed = [item[field] for item in sample if item[field] is not None]
            if sample and len(observed) == len(sample):
                totals[field].append(sum(observed))
            elif sample:
                partial = True
    partial |= any(entry[field] is None for entry in components
                   for field in ("pss_kib", "cpu_percent"))
    return {
        "samples": len(samples), "components": components,
        "total_pss_kib": round(statistics.median(totals["pss_kib"]), 1)
        if totals["pss_kib"] else None,
        "total_cpu_percent": round(statistics.median(totals["cpu_percent"]), 1)
        if totals["cpu_percent"] else None,
        "partial": partial,
    }


def apply_profile(name: str, *, config_root: Path | None = None,
                  data_root: Path | None = None) -> Path:
    """Back up the complete previous config, atomically update only profile keys."""
    if name not in PROFILES:
        raise ValueError("Choose light, balanced or visual")
    if os.geteuid() == 0:
        raise ValueError("Apply performance profiles as your desktop user, never with sudo")
    config_root = config_root or config_home()
    data_root = data_root or data_home()
    target = config_root / "macos-control-center/config.json"
    if target.parent.is_symlink():
        raise ValueError("Refusing to update preferences through a symlinked directory")
    previous = _read_preferences(target)
    updated = {**previous, **PROFILES[name]}
    if updated == previous:
        return target

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = private_state_root(data_root) / "backups/performance" / stamp
    backup.mkdir(mode=0o700, parents=True, exist_ok=False)
    if target.exists():
        copy = backup / "control-center-config.json"
        shutil.copy2(target, copy, follow_symlinks=False)
        os.chmod(copy, 0o600)
    else:
        (backup / "previously-absent").write_text("Config was absent before profile change\n")

    temporary = _stage_json(target, updated)
    try:
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return backup
