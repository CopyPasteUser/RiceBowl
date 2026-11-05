"""Explicit, non-overwriting local file-copy drops for ricePlate folder links.

This is deliberately *not* a replacement file manager. XFDesktop and Thunar
remain responsible for desktop icon placement, moving folders and Trash. A
RiceBowl folder drop always asks before copying, writes in a worker thread,
never executes a dropped item, and can undo only unchanged new files.
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from urllib.parse import unquote, urlsplit


MAX_FILES = 32
MAX_TOTAL_BYTES = 8 * 1024 ** 3


@dataclass(frozen=True)
class CopyPlan:
    destination: Path
    sources: tuple[Path, ...]
    total_bytes: int


@dataclass(frozen=True)
class CopyReceipt:
    destination: Path
    # Filename, device, inode, size, mtime_ns: only an unchanged copy can undo.
    created: tuple[tuple[str, int, int, int, int], ...]


def parse_local_uris(uris) -> tuple[Path, ...]:
    if not isinstance(uris, (list, tuple)) or not 1 <= len(uris) <= MAX_FILES:
        raise ValueError("Drop between 1 and 32 local files at a time")
    result = []
    seen = set()
    for uri in uris:
        if not isinstance(uri, str) or len(uri) > 8192:
            raise ValueError("Invalid dropped URI")
        parsed = urlsplit(uri)
        if (parsed.scheme != "file" or parsed.netloc not in ("", "localhost")
                or parsed.query or parsed.fragment):
            raise ValueError("Only local file:// drag-and-drop is supported")
        decoded = unquote(parsed.path, errors="strict")
        if not decoded.startswith("/") or "\x00" in decoded:
            raise ValueError("Invalid local file URI")
        path = Path(decoded)
        if path not in seen:
            seen.add(path)
            result.append(path)
    return tuple(result)


def plan_copy(uris, destination: Path) -> CopyPlan:
    sources = parse_local_uris(uris)
    target = Path(destination)
    if target.is_symlink() or not target.is_dir():
        raise ValueError("The destination must be an existing, non-symlink folder")
    names = set()
    size = 0
    for item in sources:
        source = item.lstat()
        if not stat.S_ISREG(source.st_mode):
            raise ValueError("Folder and symbolic-link drops stay in the file manager")
        if item.name in ("", ".", "..") or item.name in names:
            raise ValueError("Dropped files have conflicting names")
        names.add(item.name)
        if (target / item.name).exists() or (target / item.name).is_symlink():
            raise FileExistsError(f"Destination already has {item.name}; nothing will be overwritten")
        size += source.st_size
        if size > MAX_TOTAL_BYTES:
            raise ValueError("File drop exceeds the 8 GiB safety limit")
    return CopyPlan(target, sources, size)


def _same_copy(folder_fd: int, entry: tuple[str, int, int, int, int]) -> bool:
    name, device, inode, size, mtime_ns = entry
    try:
        found = os.stat(name, dir_fd=folder_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    return (stat.S_ISREG(found.st_mode) and found.st_dev == device and
            found.st_ino == inode and found.st_size == size and found.st_mtime_ns == mtime_ns)


def _discard_new(folder_fd: int, entries) -> tuple[int, int]:
    removed = skipped = 0
    for entry in entries:
        if _same_copy(folder_fd, entry):
            os.unlink(entry[0], dir_fd=folder_fd)
            removed += 1
        else:
            skipped += 1
    return removed, skipped


def copy_files(plan: CopyPlan, *, cancel: Event | None = None) -> CopyReceipt:
    """Copy atomically per name with O_EXCL; undo partial copies on errors."""
    if not isinstance(plan, CopyPlan) or not 1 <= len(plan.sources) <= MAX_FILES:
        raise ValueError("Invalid drop plan")
    folder_fd = os.open(plan.destination, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    created = []
    current_name = None
    copied_bytes = 0
    try:
        for source in plan.sources:
            if cancel is not None and cancel.is_set():
                raise RuntimeError("File copy cancelled")
            source_fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                original = os.fstat(source_fd)
                if not stat.S_ISREG(original.st_mode):
                    raise ValueError("File type changed during drag-and-drop")
                current_name = source.name
                output_fd = os.open(current_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                                    os.O_NOFOLLOW, 0o600, dir_fd=folder_fd)
                opened = os.fstat(output_fd)
                try:
                    with os.fdopen(output_fd, "wb") as output, \
                            os.fdopen(os.dup(source_fd), "rb") as input_file:
                        while True:
                            if cancel is not None and cancel.is_set():
                                raise RuntimeError("File copy cancelled")
                            block = input_file.read(1024 * 1024)
                            if not block:
                                break
                            copied_bytes += len(block)
                            if copied_bytes > MAX_TOTAL_BYTES:
                                raise ValueError("File drop exceeded the 8 GiB safety limit")
                            output.write(block)
                        output.flush()
                        os.fsync(output.fileno())
                except BaseException:
                    # Safe cleanup of a partially written destination; the
                    # O_EXCL-created inode is owned by this transfer.
                    partial = os.stat(current_name, dir_fd=folder_fd, follow_symlinks=False)
                    if (stat.S_ISREG(partial.st_mode) and partial.st_dev == opened.st_dev
                            and partial.st_ino == opened.st_ino):
                        os.unlink(current_name, dir_fd=folder_fd)
                    raise
                final = os.stat(current_name, dir_fd=folder_fd, follow_symlinks=False)
                created.append((current_name, final.st_dev, final.st_ino,
                                final.st_size, final.st_mtime_ns))
                current_name = None
            finally:
                os.close(source_fd)
        return CopyReceipt(plan.destination, tuple(created))
    except BaseException:
        _discard_new(folder_fd, created)
        raise
    finally:
        os.close(folder_fd)


def undo_copy(receipt: CopyReceipt) -> tuple[int, int]:
    """Delete only unchanged files created by this exact copy operation."""
    if not isinstance(receipt, CopyReceipt) or len(receipt.created) > MAX_FILES:
        raise ValueError("Invalid file copy receipt")
    folder_fd = os.open(receipt.destination, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        return _discard_new(folder_fd, receipt.created)
    finally:
        os.close(folder_fd)
