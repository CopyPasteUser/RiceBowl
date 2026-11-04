"""Windows 98-style read-only System Properties, backed by real Linux facts.

Never pretends to have Win9x drivers, a Registry, or Windows drive letters.
Refresh reads local sysfs/procfs on demand; no daemon or persistent polling.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import platform


@dataclass(frozen=True)
class SystemSnapshot:
    distribution: str
    kernel: str
    machine: str
    cpu_model: str
    cpu_threads: int | None
    memory_total: int | None
    memory_available: int | None
    uptime_seconds: int | None
    interfaces: tuple[tuple[str, str], ...]
    block_devices: tuple[tuple[str, int | None], ...]


def read_small(path: Path, limit: int = 65536) -> str:
    """Bounded read of kernel/distribution-provided textual properties."""
    try:
        with path.open("rb") as stream:
            return stream.read(limit).decode("utf-8", errors="replace")
    except (OSError, ValueError):
        return ""


def release_name(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("PRETTY_NAME="):
            value = line.partition("=")[2].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1]
            return value[:180] or "Linux"
    return "Linux (distribution information unavailable)"


def cpu_name(text: str) -> str:
    matches = {}
    for line in text.splitlines():
        key, separator, value = line.partition(":")
        label = key.strip().casefold()
        if separator and label in ("model name", "hardware", "model", "processor"):
            matches.setdefault(label, value.strip())
    for label in ("model name", "hardware", "model", "processor"):
        candidate = matches.get(label, "")
        # The Linux "processor: 0" field is a CPU index, not a model name.
        if candidate and not (label == "processor" and candidate.isdecimal()):
            return candidate[:180]
    return "Processor model unavailable"


def meminfo_bytes(text: str, key: str) -> int | None:
    for line in text.splitlines():
        name, separator, value = line.partition(":")
        if separator and name.strip() == key:
            tokens = value.strip().split()
            if len(tokens) >= 2 and tokens[0].isdigit() and tokens[1] == "kB":
                return int(tokens[0]) * 1024
    return None


def size_label(value: int | None) -> str:
    if value is None or value < 0:
        return "Unavailable"
    if value >= 1024 ** 3:
        return f"{value / (1024 ** 3):.1f} GiB"
    if value >= 1024 ** 2:
        return f"{value / (1024 ** 2):.1f} MiB"
    return f"{value} bytes"


def _names(directory: Path, limit: int = 64) -> tuple[str, ...]:
    try:
        return tuple(sorted(entry.name for entry in directory.iterdir()))[:limit]
    except OSError:
        return ()


def collect_system(root: Path = Path("/")) -> SystemSnapshot:
    """Capture a small current snapshot; root can be a disposable test tree."""
    cpu = read_small(root / "proc/cpuinfo")
    mem = read_small(root / "proc/meminfo", 8192)
    try:
        uptime = int(float(read_small(root / "proc/uptime", 256).split()[0]))
    except (ValueError, IndexError, OverflowError):
        uptime = None

    networks = tuple(
        (name, read_small(root / "sys/class/net" / name / "operstate", 64).strip()
         or "unknown")
        for name in _names(root / "sys/class/net")
    )
    disks = []
    for name in _names(root / "sys/block"):
        if name.startswith(("loop", "ram", "zram")):
            continue
        raw = read_small(root / "sys/block" / name / "size", 64).strip()
        # Linux sysfs block-size field is measured in 512-byte sectors.
        sectors = int(raw) if raw.isdecimal() else None
        disks.append((name, sectors * 512 if sectors is not None else None))
    return SystemSnapshot(
        distribution=release_name(read_small(root / "etc/os-release", 8192)),
        kernel=platform.release(),
        machine=platform.machine() or "Unknown",
        cpu_model=cpu_name(cpu),
        cpu_threads=os.cpu_count(),
        memory_total=meminfo_bytes(mem, "MemTotal"),
        memory_available=meminfo_bytes(mem, "MemAvailable"),
        uptime_seconds=uptime,
        interfaces=networks,
        block_devices=tuple(disks),
    )


def report_sections(snapshot: SystemSnapshot) -> dict[str, str]:
    """User-visible factual tab content for the classic System applet."""
    days, remainder = divmod(snapshot.uptime_seconds or 0, 86400)
    hours, minutes = divmod(remainder // 60, 60)
    uptime = (f"{days} days, {hours} hours, {minutes} minutes"
              if snapshot.uptime_seconds is not None else "Unavailable")
    general = (
        f"Operating system: {snapshot.distribution}\n"
        f"System type: Linux ({snapshot.machine})\n"
        f"Kernel: {snapshot.kernel}\n\n"
        f"Processor: {snapshot.cpu_model}\n"
        f"Logical processors: {snapshot.cpu_threads or 'Unavailable'}\n"
        f"Installed memory: {size_label(snapshot.memory_total)}\n\n"
        "This is a Linux desktop with a Windows 98-inspired interface."
    )
    interfaces = "\n".join(f"  {name} — {state}" for name, state in snapshot.interfaces)
    disks = "\n".join(
        f"  {name} — {size_label(size)}" for name, size in snapshot.block_devices)
    devices = (
        "Network interfaces\n"
        + (interfaces or "  None reported") + "\n\n"
        + "Block devices\n"
        + (disks or "  None reported") + "\n\n"
        + "Device details come from /sys. This viewer does not install drivers."
    )
    perf = (
        f"Uptime: {uptime}\n"
        f"Total memory: {size_label(snapshot.memory_total)}\n"
        f"Available memory: {size_label(snapshot.memory_available)}\n"
        f"Logical processors: {snapshot.cpu_threads or 'Unavailable'}\n\n"
        "Click Refresh for a new read-only snapshot. No background polling."
    )
    return {"General": general, "Device Manager": devices, "Performance": perf}


def show_system(shell, Gtk):
    """Classic tabbed read-only System Properties dialog."""
    parent = getattr(shell, "actions", None) or shell.bar
    dialog = Gtk.Dialog(title="System Properties", transient_for=parent)
    dialog.set_default_size(565, 430)
    dialog.set_resizable(True)
    dialog.add_button("Close", Gtk.ResponseType.CLOSE)
    refresh_id = 100
    dialog.add_button("Refresh", refresh_id)
    area = dialog.get_content_area()
    area.set_border_width(10)
    area.set_spacing(10)
    header = Gtk.Label(label="System Properties — Linux", xalign=0)
    area.pack_start(header, False, False, 0)
    notebook = Gtk.Notebook()
    area.pack_start(notebook, True, True, 0)
    views = {}
    for title in ("General", "Device Manager", "Performance"):
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        text = Gtk.TextView()
        text.set_editable(False)
        text.set_cursor_visible(False)
        text.set_wrap_mode(Gtk.WrapMode.WORD)
        text.set_left_margin(12)
        text.set_right_margin(12)
        text.set_top_margin(12)
        scroller.add(text)
        notebook.append_page(scroller, Gtk.Label(label=title))
        views[title] = text

    def refresh():
        data = report_sections(collect_system())
        for title, widget in views.items():
            widget.get_buffer().set_text(data[title])

    refresh()
    dialog.show_all()
    try:
        while dialog.run() == refresh_id:
            refresh()
    finally:
        dialog.destroy()
