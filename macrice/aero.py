"""Safe, user-local installation of RiceBowl's own Aero GTK/XFWM/icon artwork.

Never touch /usr/share or replace an existing (possibly user-edited) theme.
The desktop restore engine reverts theme *selection* while retaining these
harmless shared files for later switches; no system packages are required.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from .environment import bin_home


THEME = "RiceHub-Aero"
BUNDLES = (
    ("assets/themes/RiceHub-Aero", "themes/RiceHub-Aero"),
    ("assets/icons/RiceHub-Aero", "icons/RiceHub-Aero"),
)


class AeroAssetError(ValueError):
    pass


AUTOSTART_MARKER = "# RiceHub Aero autostart (managed by RiceHub)"


def autostart_file(config_root: Path) -> Path:
    return config_root / "autostart/ricehub-aero-shell.desktop"


def read_autostart(config_root: Path) -> str | None:
    target = autostart_file(config_root)
    if target.is_symlink() or target.parent.is_symlink():
        raise AeroAssetError("Unmanaged symlink at Aero autostart path")
    if not target.exists():
        return None
    if not target.is_file() or target.stat().st_size > 16 * 1024:
        raise AeroAssetError("Unexpected file at Aero autostart path")
    content = target.read_text(encoding="utf-8")
    from .installer import project_root
    if content not in (autostart_content(project_root()), legacy_autostart_content(project_root())):
        raise AeroAssetError("Existing Aero autostart is not managed by RiceBowl or was customized")
    return content


def autostart_content(source_root: Path) -> str:
    executable = str(bin_home() / "macrice").replace('"', '\\"')
    icon = str(source_root / "assets/aero-penguin.svg").replace('"', '\\"')
    return (
        "[Desktop Entry]\nType=Application\nVersion=1.0\n"
        "Name=RiceBowl Aero Taskbar\nComment=Lightweight Windows 7-inspired Start menu and taskbar\n"
        f'Exec="{executable}" aero-shell\nIcon={icon}\n'
        "Terminal=false\nOnlyShowIn=XFCE;\nX-GNOME-Autostart-enabled=true\n"
        f"{AUTOSTART_MARKER}\n"
    )


def legacy_autostart_content(source_root: Path) -> str:
    """Exact legacy managed entry, recognized during upgrades and restore."""
    return autostart_content(source_root).replace(
        "Name=RiceBowl Aero Taskbar", "Name=RiceHub Aero Taskbar"
    )


def write_autostart(config_root: Path, content: str | None) -> None:
    target = autostart_file(config_root)
    read_autostart(config_root)  # Fail closed if a user replaced our managed entry.
    if content is None:
        target.unlink(missing_ok=True)
        return
    from .installer import project_root
    if content not in (autostart_content(project_root()), legacy_autostart_content(project_root())):
        raise AeroAssetError("Refusing non-canonical Aero autostart content")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".ricehub-aero-start-", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temp, 0o644)
        os.replace(temp, target)
    finally:
        Path(temp).unlink(missing_ok=True)


def _compatible_managed_file(relative: Path, current: bytes, expected: bytes) -> bool:
    """Only accept unchanged assets or the exact pre-RiceBowl index metadata.

    The strict comparison on every other file protects customized artwork.
    """
    return current == expected or (
        relative == Path("index.theme")
        and b"RiceBowl" in expected
        and current == expected.replace(b"RiceBowl", b"RiceHub")
    )


def _migrate_owned_index(target: Path, source: Path) -> None:
    """Backup and atomically relabel only a verified, old managed index.theme."""
    old_index = target / "index.theme"
    new_index = source / "index.theme"
    if not old_index.is_file() or old_index.is_symlink() or not new_index.is_file():
        return
    current, expected = old_index.read_bytes(), new_index.read_bytes()
    if current == expected:
        return
    if not _compatible_managed_file(Path("index.theme"), current, expected):
        raise AeroAssetError(f"Customized theme metadata cannot be migrated: {target}")
    backup_dir = target.parent / ".ricebowl-metadata-backups"
    if backup_dir.is_symlink() or (backup_dir.exists() and not backup_dir.is_dir()):
        raise AeroAssetError("Unmanaged metadata backup path")
    backup_dir.mkdir(mode=0o700, exist_ok=True)
    backup_fd, backup_file = tempfile.mkstemp(prefix=target.name + "-", suffix=".theme", dir=backup_dir)
    try:
        with os.fdopen(backup_fd, "wb") as stream:
            stream.write(current)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(backup_file, 0o600)
        fd, temporary = tempfile.mkstemp(prefix=".ricebowl-index-", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(expected)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, 0o644)
            os.replace(temporary, old_index)
        finally:
            Path(temporary).unlink(missing_ok=True)
    except Exception:
        # Keep a successful backup on disk even when the metadata write fails.
        raise


def preflight(source_root: Path, data_root: Path,
              bundles: tuple[tuple[str, str], ...] = BUNDLES) -> list[tuple[Path, Path]]:
    """Validate whole bundles and destinations before creating a single file."""
    packages = []
    for relative, destination in bundles:
        source = source_root / relative
        target = data_root / destination
        if not source.is_dir() or source.is_symlink():
            raise AeroAssetError(f"Bundled Aero theme directory is missing: {relative}")
        files = [p for p in source.rglob("*") if p.is_file()]
        if not files or len(files) > 180:
            raise AeroAssetError("Aero theme assets are missing or unexpectedly numerous")
        if any(p.is_symlink() for p in source.rglob("*")):
            raise AeroAssetError("Refusing symlinks in bundled theme assets")
        if any(p.stat().st_size > 2 * 1024 * 1024 for p in files):
            raise AeroAssetError("Unexpectedly large Aero theme asset")
        if any(p.is_symlink() for p in (target, *target.parents)):
            raise AeroAssetError(f"Refusing symlinked theme target: {target}")
        if target.exists():
            if not target.is_dir():
                raise AeroAssetError(f"Theme target is not a directory: {target}")
            actual = {p.relative_to(target) for p in target.rglob("*") if p.is_file()}
            expected = {p.relative_to(source) for p in files}
            if (actual != expected or any(p.is_symlink() for p in target.rglob("*")) or
                    any(not _compatible_managed_file(
                        p.relative_to(source), (target / p.relative_to(source)).read_bytes(), p.read_bytes()
                    ) for p in files)):
                raise AeroAssetError(f"Existing customized theme conflicts with RiceBowl: {target}")
        packages.append((source, target))
    return packages


def install(packages: list[tuple[Path, Path]]) -> None:
    """Stage complete directories then rename them into an unoccupied path."""
    for source, target in packages:
        if target.exists():
            _migrate_owned_index(target, source)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".ricehub-aero-", dir=target.parent))
        try:
            for item in source.rglob("*"):
                relative = item.relative_to(source)
                output = stage / relative
                if item.is_dir():
                    output.mkdir(parents=True, exist_ok=True)
                else:
                    output.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(item, output, follow_symlinks=False)
                    os.chmod(output, 0o644)
            if target.exists() or target.is_symlink():
                raise AeroAssetError(f"Theme target appeared during installation: {target}")
            os.rename(stage, target)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
