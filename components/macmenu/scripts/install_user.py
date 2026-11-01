"""Recoverable, non-root upgrade for the managed MacMenu user installation.

Only MacMenu-owned paths and verified MacMenu processes are affected.  A
distribution-managed installation is removed only after an explicit prompt.
"""

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class InstallError(Exception):
    pass


def locations() -> tuple[Path, Path, Path]:
    data = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    binaries = Path(os.environ.get("XDG_BIN_HOME") or Path.home() / ".local/bin")
    return data / "macmenu", binaries / "macmenu", data / "applications/macmenu.desktop"


def verify_existing(app_dir: Path, link: Path, desktop: Path) -> None:
    """Never replace a path that another program or untracked user owns."""
    if app_dir.is_symlink() or (app_dir.exists() and not (app_dir / ".macmenu-managed").is_file()):
        raise InstallError(f"Unmanaged directory at {app_dir}; nothing was changed.")
    if app_dir.exists() and app_dir.stat().st_uid != os.getuid():
        raise InstallError(f"Installation is not owned by this user: {app_dir}")
    if link.is_symlink():
        target = (link.parent / os.readlink(link)).resolve()
        if target != (app_dir / "launcher").resolve():
            raise InstallError(f"Unrelated launcher symlink at {link}; nothing was changed.")
    elif link.exists():
        raise InstallError(f"Unrelated executable at {link}; nothing was changed.")
    if desktop.is_symlink():
        raise InstallError(f"Unmanaged desktop symlink at {desktop}; nothing was changed.")
    if desktop.exists():
        if not desktop.is_file() or desktop.stat().st_uid != os.getuid():
            raise InstallError(f"Desktop entry is not a regular user-owned file: {desktop}")
        if "X-MacMenu-Managed=true" not in desktop.read_text(encoding="utf-8"):
            raise InstallError(f"Unmanaged desktop entry at {desktop}; nothing was changed.")


def installed_system_package() -> str | None:
    if not shutil.which("dpkg-query"):
        return None
    result = subprocess.run(
        ["dpkg-query", "-W", "-f=${Status} ${Version}", "xfce-macmenu"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode or not result.stdout.startswith("install ok installed "):
        return None
    return result.stdout.removeprefix("install ok installed ").strip()


def resolve_system_package(version: str) -> None:
    print(f"A system-wide MacMenu package ({version}) is installed.")
    print("A user installation alongside it can launch the wrong version.")
    if not sys.stdin.isatty():
        raise InstallError("Remove it with 'sudo apt remove xfce-macmenu' first, then rerun the installer.")
    answer = input("Remove the old xfce-macmenu Debian package now? [y/N] ").strip().casefold()
    if answer not in {"y", "yes"}:
        raise InstallError("System package retained. No new user installation was made.")
    result = subprocess.run(["sudo", "apt-get", "remove", "xfce-macmenu"], check=False)
    if result.returncode or installed_system_package():
        raise InstallError("System package removal failed; user installation was not changed.")


def is_macmenu_command(args: list[str]) -> bool:
    return (len(args) >= 3 and Path(args[0]).name.startswith("python3")
            and args[1:3] == ["-m", "macmenu"])


def running_macmenu_pids() -> list[int]:
    """Only the current user's Python -m macmenu process, never broad name matches."""
    matches = []
    for proc in Path("/proc").glob("[0-9]*"):
        try:
            if proc.stat().st_uid != os.getuid():
                continue
            args = [part.decode("utf-8", "replace") for part in
                    (proc / "cmdline").read_bytes().split(b"\0") if part]
            if is_macmenu_command(args):
                matches.append(int(proc.name))
        except (OSError, ValueError):
            continue
    return matches


def stop_previous_instance(app_dir: Path) -> None:
    pids = running_macmenu_pids()
    if not pids:
        return
    launcher = app_dir / "launcher"
    if launcher.is_file():
        try:
            subprocess.run([str(launcher), "--quit"], timeout=4, check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired):
            pass
    deadline = time.monotonic() + 2
    while running_macmenu_pids() and time.monotonic() < deadline:
        time.sleep(0.1)
    # If the old CLI could not reach its GApplication instance, terminate only
    # an exact, user-owned MacMenu module process. Never use pkill -f.
    for pid in set(pids).intersection(running_macmenu_pids()):
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 3
    while running_macmenu_pids() and time.monotonic() < deadline:
        time.sleep(0.1)
    remaining = running_macmenu_pids()
    if remaining:
        raise InstallError(f"MacMenu is still running (PIDs {remaining}). No files were replaced.")
    print("Stopped the previous MacMenu instance.")


def stage_application(source: Path, app_dir: Path) -> Path:
    staging = Path(tempfile.mkdtemp(prefix=".macmenu-stage-", dir=app_dir.parent))
    (staging / "macmenu").mkdir()
    for module in sorted((source / "macmenu").glob("*.py")):
        shutil.copyfile(module, staging / "macmenu" / module.name)
        (staging / "macmenu" / module.name).chmod(0o644)
    (staging / "assets").mkdir()
    for asset in ("macmenu-penguin.svg", "macmenu-penguin-ink.svg", "macmenu-app.svg"):
        shutil.copyfile(source / "assets" / asset, staging / "assets" / asset)
        (staging / "assets" / asset).chmod(0o644)
    shutil.copyfile(source / "scripts/macmenu", staging / "launcher")
    (staging / "launcher").chmod(0o755)
    (staging / ".macmenu-managed").write_text("Managed by MacMenu installer\n", encoding="utf-8")
    return staging


def desktop_contents(source: Path, app_dir: Path) -> bytes:
    contents = (source / "scripts/macmenu.desktop").read_text(encoding="utf-8")
    target = str(app_dir / "launcher")
    escaped = target.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`")
    contents = contents.replace("Exec=macmenu", f'Exec="{escaped}"')
    contents = contents.replace("Icon=macmenu", f"Icon={app_dir / 'assets/macmenu-app.svg'}")
    return contents.encode("utf-8")


def upgrade(source: Path, app_dir: Path, link: Path, desktop: Path) -> Path | None:
    """Stage, back up and swap the tracked app without touching user data."""
    app_dir.parent.mkdir(parents=True, exist_ok=True)
    link.parent.mkdir(parents=True, exist_ok=True)
    desktop.parent.mkdir(parents=True, exist_ok=True)
    staging = stage_application(source, app_dir)
    desktop_tmp = desktop.parent / f".macmenu-desktop-{uuid4().hex}"
    link_tmp = link.parent / f".macmenu-link-{uuid4().hex}"
    retired = app_dir.parent / f".macmenu-retired-{uuid4().hex}"
    backup = None
    old_desktop = desktop.read_bytes() if desktop.exists() else None
    old_link = os.readlink(link) if link.is_symlink() else None
    swapped = moved_old = desktop_changed = link_changed = False
    try:
        desktop_tmp.write_bytes(desktop_contents(source, app_dir))
        desktop_tmp.chmod(0o644)
        link_tmp.symlink_to(app_dir / "launcher")
        if app_dir.exists():
            backups = app_dir.parent / "macmenu-backups"
            backups.mkdir(mode=0o700, exist_ok=True)
            backup = backups / f"before-rc11-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
            shutil.copytree(app_dir, backup, symlinks=True)
            backup.chmod(0o700)
            app_dir.rename(retired)
            moved_old = True
        staging.rename(app_dir)
        swapped = True
        desktop_tmp.replace(desktop)
        desktop_changed = True
        link_tmp.replace(link)
        link_changed = True
    except Exception:
        if link_changed:
            link.unlink()
            if old_link is not None:
                link.symlink_to(old_link)
        if desktop_changed:
            if old_desktop is None:
                desktop.unlink()
            else:
                desktop.write_bytes(old_desktop)
        if swapped:
            shutil.rmtree(app_dir)  # exact newly staged installation
        if moved_old and retired.exists():
            retired.rename(app_dir)
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)
        if desktop_tmp.exists():
            desktop_tmp.unlink()
        if link_tmp.is_symlink():
            link_tmp.unlink()
    if moved_old:
        try:
            shutil.rmtree(retired)  # exact managed former installation; backup retained
        except OSError as exc:
            print(f"The retired copy at {retired} could not be removed: {exc}", file=sys.stderr)
    return backup


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Upgrade the user-scoped MacMenu installation safely")
    parser.add_argument("--dry-run", action="store_true", help="Inspect the upgrade without changing anything")
    args = parser.parse_args(argv)
    source = Path(__file__).resolve().parents[1]
    app_dir, link, desktop = locations()
    try:
        verify_existing(app_dir, link, desktop)
        package = installed_system_package()
        pids = running_macmenu_pids()
        print(f"MacMenu target: {app_dir}")
        print(f"Running MacMenu instances: {pids or 'none'}")
        print(f"Previous user installation: {'yes' if app_dir.exists() else 'no'}")
        if args.dry_run:
            print(f"System Debian package: {package or 'none'}")
            print("Dry run complete; nothing was changed.")
            return 0
        subprocess.run([sys.executable, "-c",
                        'import gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk, Gio'],
                       check=True, stdout=subprocess.DEVNULL)
        if package:
            resolve_system_package(package)
        stop_previous_instance(app_dir)
        backup = upgrade(source, app_dir, link, desktop)
    except (InstallError, OSError, subprocess.CalledProcessError) as exc:
        print(f"MacMenu installation stopped: {exc}", file=sys.stderr)
        return 1
    print("MacMenu RC11 is installed. Start with:", link)
    if backup:
        print("Previous installation backup:", backup)
    print("Your favorites, recent apps and appearance settings were preserved.")
    print("Use the same 'macmenu --toggle' shortcut to open, close and reopen the menu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
