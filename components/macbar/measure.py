#!/usr/bin/python3
"""Show measured proportional resident RAM, not inflated shared-library RSS."""

from __future__ import annotations

from pathlib import Path


def process_totals() -> list[tuple[str, int, int]]:
    results = []
    for path in Path("/proc").iterdir():
        if not path.name.isdecimal():
            continue
        try:
            args = (path / "cmdline").read_bytes().split(b"\x00")
            argv = [item.decode(errors="replace") for item in args if item]
            name = (path / "comm").read_text().strip()
            group = ""
            if any(Path(part).name == "macbar.py" for part in argv[:2]):
                group = "MacBar"
            elif name == "xfce4-panel" or name.startswith("wrapper-") and any("xfce4-panel" in part for part in argv[:2]):
                group = "XFCE Panel + plugins"
            elif name == "plank":
                group = "Plank (separate)"
            if not group:
                continue
            pss = next((int(line.split()[1]) for line in (path / "smaps_rollup").read_text().splitlines() if line.startswith("Pss:")), 0)
            results.append((group, int(path.name), pss))
        except (OSError, ValueError):
            continue
    return results


if __name__ == "__main__":
    totals: dict[str, int] = {}
    for group, _pid, pss in process_totals():
        totals[group] = totals.get(group, 0) + pss
    print("Proportional Set Size (PSS), including shared libraries proportionally:")
    for group, pss in sorted(totals.items()):
        print(f"  {group:<24} {pss / 1024:6.1f} MiB")
    if not totals:
        print("  No panel processes found or cannot read /proc/*/smaps_rollup.")
