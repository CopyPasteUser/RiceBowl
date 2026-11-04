"""Bounded, cancellable Windows 98 Find search engine.

Runs on a worker, never GTK's main thread. It searches native Linux paths,
does not recurse into symlinked directories, and never writes to user files.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import stat
import time
from typing import Callable

MAX_VISITED = 50_000
MAX_RESULTS = 500
MAX_TEXT_FILE = 1024 * 1024
MAX_TEXT_TOTAL = 32 * 1024 * 1024
_BATCH_SIZE = 20


@dataclass(frozen=True)
class FindCriteria:
    name: str = ""
    text: str = ""
    extension: str = ""
    kind: str = "both"  # both, files or folders
    modified_within_days: int | None = None
    min_bytes: int | None = None
    max_bytes: int | None = None
    include_hidden: bool = False


@dataclass(frozen=True)
class FindSummary:
    scanned: int
    matches: int
    reason: str
    content_skipped: int


def validate_criteria(criteria: FindCriteria) -> None:
    if criteria.kind not in ("both", "files", "folders"):
        raise ValueError("Unknown file type filter.")
    if criteria.modified_within_days not in (None, 1, 7, 30, 365):
        raise ValueError("Select a valid modification period.")
    if any(value is not None and (not isinstance(value, int) or value < 0)
           for value in (criteria.min_bytes, criteria.max_bytes)):
        raise ValueError("File sizes must be non-negative.")
    if criteria.max_bytes is not None and criteria.min_bytes is not None and (
            criteria.min_bytes > criteria.max_bytes):
        raise ValueError("Minimum size cannot exceed maximum size.")
    if criteria.extension and ("/" in criteria.extension or "\x00" in criteria.extension
                               or len(criteria.extension) > 64):
        raise ValueError("Enter a valid extension.")
    if len(criteria.name) > 256 or len(criteria.text) > 256:
        raise ValueError("Search terms are too long.")
    if criteria.text and criteria.kind == "folders":
        raise ValueError("Text can only be searched inside files.")
    if not any((criteria.name.strip(), criteria.text.strip(),
                criteria.extension.strip(), criteria.modified_within_days is not None,
                criteria.min_bytes is not None, criteria.max_bytes is not None,
                criteria.kind != "both")):
        raise ValueError("Enter a name, text or search filter.")


def _has_text(path: Path, needle: str, budget: int) -> tuple[bool, int]:
    """Read a small regular file without following a final symlink replacement."""
    if budget <= 0:
        return False, 0
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        return False, 0
    with os.fdopen(fd, "rb", closefd=True) as stream:
        meta = os.fstat(stream.fileno())
        if (not stat.S_ISREG(meta.st_mode) or meta.st_size > MAX_TEXT_FILE
                or meta.st_size > budget):
            return False, 0
        # Read at most MAX_TEXT_FILE; do not load unbounded or special files.
        data = stream.read(MAX_TEXT_FILE + 1)
    if len(data) > MAX_TEXT_FILE:
        return False, min(len(data), budget)
    if b"\x00" in data:
        return False, len(data)
    return needle in data.decode("utf-8", errors="replace").casefold(), len(data)


def search_folder(
    root: Path,
    criteria: FindCriteria,
    stopped,
    emit: Callable[[list[Path], int, bool, str], None],
    *,
    now: float | None = None,
    max_visited: int = MAX_VISITED,
    max_results: int = MAX_RESULTS,
) -> FindSummary:
    """Emit result batches from the worker; caller marshals them to GTK.

    'stopped' exposes is_set(); emit never changes the filesystem.
    Limits intentionally also apply to match-all filtered searches.
    """
    validate_criteria(criteria)
    if not root.is_dir():
        raise ValueError("Choose an existing search folder.")
    now = time.time() if now is None else now
    cutoff = (now - criteria.modified_within_days * 86400
              if criteria.modified_within_days is not None else None)
    extension = criteria.extension.strip().lstrip(".").casefold()
    name_query = criteria.name.strip().casefold()
    text_query = criteria.text.strip().casefold()
    pending: list[Path] = []
    scanned = matches = text_bytes = skipped = 0
    first_error = ""
    reason = "complete"

    def onerror(error):
        nonlocal first_error
        if not first_error:
            first_error = str(error)

    for current, directories, files in os.walk(root, topdown=True, followlinks=False,
                                               onerror=onerror):
        if stopped.is_set():
            reason = "stopped"
            break
        directories[:] = [item for item in directories
                          if (criteria.include_hidden or not item.startswith("."))
                          and not Path(current, item).is_symlink()]
        names = [*directories, *(file for file in files
                                if criteria.include_hidden or not file.startswith("."))]
        for filename in names:
            if stopped.is_set():
                reason = "stopped"
                break
            if scanned >= max_visited:
                reason = "scan limit reached"
                break
            if matches >= max_results:
                reason = "result limit reached"
                break
            scanned += 1
            if name_query and name_query not in filename.casefold():
                continue
            path = Path(current, filename)
            try:
                metadata = path.lstat()
            except OSError:
                continue
            is_dir = stat.S_ISDIR(metadata.st_mode)
            is_file = stat.S_ISREG(metadata.st_mode)
            if criteria.kind == "files" and not is_file:
                continue
            if criteria.kind == "folders" and not is_dir:
                continue
            if extension and (not is_file or not filename.casefold().endswith("." + extension)):
                continue
            if cutoff is not None and metadata.st_mtime < cutoff:
                continue
            if (criteria.min_bytes is not None or criteria.max_bytes is not None) and not is_file:
                continue
            if criteria.min_bytes is not None and metadata.st_size < criteria.min_bytes:
                continue
            if criteria.max_bytes is not None and metadata.st_size > criteria.max_bytes:
                continue
            if text_query:
                if not is_file or text_bytes >= MAX_TEXT_TOTAL:
                    skipped += 1
                    continue
                try:
                    matched, used = _has_text(path, text_query, MAX_TEXT_TOTAL - text_bytes)
                except (OSError, UnicodeError):
                    matched, used = False, 0
                text_bytes += used
                if not matched:
                    if used == 0:
                        skipped += 1
                    continue
            pending.append(path)
            matches += 1
            if len(pending) >= _BATCH_SIZE:
                emit(pending, scanned, False, "")
                pending = []
        if reason != "complete":
            break

    if reason == "complete" and first_error:
        reason = "some folders could not be accessed"
    if text_query and skipped:
        reason += f" · {skipped} files skipped (size, format or access)"
    emit(pending, scanned, True, reason)
    return FindSummary(scanned, matches, reason, skipped)
