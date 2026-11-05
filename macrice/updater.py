"""Opt-in fast-forward updater with immutable source staging and recovery.

The checked-out source is advanced *after* a staged install succeeds. The
previous installed bundle is retained by the existing versioned installer.
This does not claim signed release verification or full component-level atomicity.
"""

from __future__ import annotations

import fcntl
import io
import os
import shutil
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .environment import data_home
from .installer import InstallOptions, InstallationError, install, project_root, MANAGED_MARKER


ALLOWED_REMOTES = frozenset({
    "https://github.com/CopyPasteUser/RiceBowl.git",
    "https://github.com/CopyPasteUser/RiceBowl",
    "git@github.com:CopyPasteUser/RiceBowl.git",
    "ssh://git@github.com/CopyPasteUser/RiceBowl.git",
})


def _default_source() -> Path:
    # Installed launchers run from ~/.local/share/macrice without .git;
    # never confuse that installed copy with the user's source checkout.
    for candidate in (project_root(), Path.cwd(), Path.home() / "RiceBowl"):
        if (candidate / ".git").is_dir() and not candidate.is_symlink():
            return candidate
    raise UpdateError("Could not locate a Git checkout; pass --source /path/to/RiceBowl")


class UpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class UpdatePlan:
    current: str
    available: str
    commits: int
    source: Path

    @property
    def needed(self) -> bool:
        return self.commits > 0


def _git(source: Path, *args: str, timeout: int = 15) -> str:
    try:
        proc = subprocess.run(["git", "-C", str(source), *args], text=True,
                              capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise UpdateError("Git did not complete; no update applied") from exc
    if proc.returncode:
        raise UpdateError("Git " + args[0] + " failed: " +
                          (proc.stderr.strip() or "check the checkout and network")[-180:])
    return proc.stdout.strip()


def local_changes(source: Path) -> tuple[str, ...]:
    """Bounded, read-only filename summary; never read local file contents."""
    lines = _git(source, "status", "--porcelain", "--untracked-files=normal").splitlines()
    return tuple("".join(c if c.isprintable() else "?" for c in line)[:115]
                 for line in lines[:12]) + ((f"… and {len(lines) - 12} more",)
                                           if len(lines) > 12 else ())


def _validate_checkout(source: Path) -> None:
    if os.geteuid() == 0:
        raise UpdateError("Update as your desktop user, not with sudo")
    if source.is_symlink() or (source / ".git").is_symlink() or not (source / ".git").is_dir():
        raise UpdateError("Updater requires a normal RiceBowl Git checkout")
    if _git(source, "remote", "get-url", "origin") not in ALLOWED_REMOTES:
        raise UpdateError("Origin is not the official RiceBowl repository; refusing code execution")
    if _git(source, "symbolic-ref", "--short", "HEAD") != "main":
        raise UpdateError("Switch to your clean main branch before updating")


def preserve_changes(*, source: Path | None = None) -> str:
    """Explicitly stow dirty tracked/untracked files in a *local* Git stash.

    Caller must obtain user consent beforehand. The stash is never dropped or
    applied automatically; the owner can inspect/restore it after the update.
    """
    source = _default_source() if source is None else source
    _validate_checkout(source)
    if not local_changes(source):
        raise UpdateError("No local changes need preserving")
    _git(source, "stash", "push", "--include-untracked",
         "--message", "RiceBowl updater: saved before manual update", timeout=90)
    revision = _git(source, "rev-parse", "refs/stash")
    if local_changes(source):
        raise UpdateError("Some local edits remain; saved stash " + revision[:12] +
                          " exists, but update is blocked")
    return revision


def inspect(*, source: Path | None = None, refresh: bool = False) -> UpdatePlan:
    """Read-only by default; explicit refresh fetches only the trusted main ref."""
    source = _default_source() if source is None else source
    _validate_checkout(source)
    dirty = local_changes(source)
    if dirty:
        raise UpdateError("Checkout contains local changes; commit or preserve them first:\n" +
                          "\n".join(dirty))
    if refresh:
        _git(source, "fetch", "--no-tags", "origin", "main", timeout=45)
    current = _git(source, "rev-parse", "HEAD")
    available = _git(source, "rev-parse", "refs/remotes/origin/main")
    try:
        ancestor = subprocess.run(["git", "-C", str(source), "merge-base", "--is-ancestor",
                                   current, available], capture_output=True, timeout=10,
                                  check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise UpdateError("Could not check fast-forward safety") from exc
    if ancestor.returncode:
        raise UpdateError("Local main and origin/main have diverged; never force-update")
    count = int(_git(source, "rev-list", "--count", current + ".." + available))
    return UpdatePlan(current, available, count, source)


def _extract_commit(source: Path, revision: str, destination: Path) -> None:
    """Reject archive paths and links that could escape the staging directory."""
    try:
        proc = subprocess.run(["git", "-C", str(source), "archive", "--format=tar", revision],
                              capture_output=True, timeout=45, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise UpdateError("Could not stage the pinned release") from exc
    if proc.returncode:
        raise UpdateError("Could not archive the selected Git revision")
    with tarfile.open(fileobj=io.BytesIO(proc.stdout), mode="r:") as archive:
        for member in archive.getmembers():
            path = Path(member.name)
            if (path.is_absolute() or ".." in path.parts or not path.parts
                    or not (member.isfile() or member.isdir())):
                raise UpdateError("Unsafe archive member; update rejected")
        archive.extractall(destination, filter="data")


def apply(*, source: Path | None = None, expected_revision: str | None = None) -> UpdatePlan:
    """Install a pinned FF revision, recover the previous bundle on failure."""
    if os.geteuid() == 0:
        raise UpdateError("Never run the updater as root")
    base = data_home()
    target = base / "macrice"
    if target.is_symlink() or not (target / MANAGED_MARKER).is_file():
        raise UpdateError("No managed existing installation to recover; run the installer first")
    locks = base / "macrice-updates"
    if locks.is_symlink() or (locks.exists() and
                             (not locks.is_dir() or locks.stat().st_uid != os.getuid())):
        raise UpdateError("Update lock directory is not a user-owned directory")
    locks.mkdir(parents=True, mode=0o700, exist_ok=True)
    lock_file = locks / "update.lock"
    if lock_file.is_symlink() or (lock_file.exists() and
                                  (not lock_file.is_file() or lock_file.stat().st_uid != os.getuid())):
        raise UpdateError("Update lock file is not user-owned or is a symlink")
    with lock_file.open("a+b") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise UpdateError("Another RiceBowl update is already running") from exc
        plan = inspect(source=source, refresh=True)
        if expected_revision is not None and plan.available != expected_revision:
            raise UpdateError("Available revision changed since preview; check updates again")
        if not plan.needed:
            return plan
        archive = base / "macrice-versions"
        if archive.is_symlink() or (archive.exists() and
                                    (not archive.is_dir() or archive.stat().st_uid != os.getuid())):
            raise UpdateError("Prior bundle archive location is unsafe; refusing update")
        before = set(archive.iterdir()) if archive.is_dir() else set()
        with tempfile.TemporaryDirectory(prefix="ricebowl-update-", dir=locks) as stage:
            staged = Path(stage)
            _extract_commit(plan.source, plan.available, staged)
            try:
                install(InstallOptions(no_start=True), source=staged, output=lambda _: None)
                # Verify installed bundle before advancing the user's source tree.
                if not (target / MANAGED_MARKER).is_file() or not (target / "launcher.py").is_file():
                    raise InstallationError("Installed bundle did not pass integrity checks")
                _git(plan.source, "merge", "--ff-only", plan.available, timeout=45)
            except (InstallationError, UpdateError, OSError, RuntimeError) as exc:
                previous = sorted(set(archive.iterdir()) - before) if archive.is_dir() else []
                if not previous:
                    raise UpdateError("Update failed before staging the prior bundle: " + str(exc)) from exc
                try:
                    install(InstallOptions(no_start=True), source=previous[-1], output=lambda _: None)
                except (InstallationError, OSError, RuntimeError) as recovery:
                    raise UpdateError("Update failed and automatic reinstall failed; previous bundle at " +
                                      str(previous[-1]) + ": " + str(recovery)) from exc
                raise UpdateError("Update failed; previous installed bundle reinstalled. " + str(exc)) from exc
        return plan
