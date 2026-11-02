"""User-local installer that delegates to each component's tested installer."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .environment import bin_home, data_home


COMPONENTS = ("macmenu", "control-center", "macbar")
MANAGED_MARKER = ".macrice-managed"
LAUNCHER_MARKER = "# Managed by MacRice XFCE"
DESKTOP_MARKER = "X-MacRice-Managed=true"


class InstallationError(RuntimeError):
    pass


@dataclass(frozen=True)
class InstallOptions:
    dry_run: bool = False
    no_start: bool = False
    bar_autostart: bool = False


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _check_layout(source: Path) -> None:
    required = (
        "macrice/cli.py",
        "macrice/gui.py",
        "macrice/plank.py",
        "components/plank/README.md",
        "components/macmenu/scripts/install_user.py",
        "components/control-center/install.sh",
        "components/macbar/install.sh",
        "launcher.py",
        "assets/macrice-symbolic.svg",
    )
    missing = [path for path in required if not (source / path).is_file()]
    if missing:
        raise InstallationError("Incomplete suite bundle: " + ", ".join(missing))


def _check_existing(target: Path) -> None:
    if target.is_symlink() or (target.exists() and not (target / MANAGED_MARKER).is_file()):
        raise InstallationError(f"Unmanaged installation at {target}; nothing replaced.")
    if target.exists() and target.stat().st_uid != os.getuid():
        raise InstallationError(f"Installation owned by another user: {target}")


def _check_system_package() -> None:
    if not shutil.which("dpkg-query"):
        return
    proc = subprocess.run(
        ["dpkg-query", "-W", "-f=${Status}", "xfce-macmenu"],
        capture_output=True, text=True, timeout=3, check=False,
    )
    if proc.returncode == 0 and proc.stdout.strip() == "install ok installed":
        raise InstallationError(
            "A system-wide xfce-macmenu DEB is installed. The suite will not "
            "remove packages or request sudo automatically. Run "
            "'sudo apt remove xfce-macmenu' yourself if you choose the user-local installer."
        )


def plan(source: Path, options: InstallOptions) -> list[tuple[str, list[str]]]:
    components = source / "components"
    return [
        (
            "MacMenu",
            ["/usr/bin/python3", str(components / "macmenu/scripts/install_user.py"),
             *(["--dry-run"] if options.dry_run else [])],
        ),
        (
            "Control Center",
            ["bash", str(components / "control-center/install.sh"),
             "--no-start" if options.no_start or options.dry_run else "--start-hidden"],
        ),
        (
            "MacBar",
            ["sh", str(components / "macbar/install.sh"),
             *(["--autostart"] if options.bar_autostart and not options.dry_run else [])],
        ),
    ]


def _copy_bundle(source: Path, stage: Path) -> None:
    def ignore(_directory: str, names: list[str]) -> set[str]:
        return {name for name in names if name in {".git", "__pycache__", ".venv"}
                or name.endswith((".pyc", ".pyo"))}

    for folder in ("macrice", "components", "assets"):
        shutil.copytree(source / folder, stage / folder, ignore=ignore)
    for file in ("launcher.py", "README.md", "LICENSE", "ROADMAP.md"):
        shutil.copy2(source / file, stage / file)
    (stage / MANAGED_MARKER).write_text("Managed by MacRice XFCE\n", encoding="ascii")


def _install_manager(source: Path) -> Path:
    data = data_home()
    target = data / "macrice"
    _check_existing(target)
    data.mkdir(mode=0o700, parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".macrice-stage-", dir=data))
    prior = None
    try:
        _copy_bundle(source, stage)
        if target.exists():
            archive = data / "macrice-versions"
            archive.mkdir(mode=0o700, parents=True, exist_ok=True)
            prior = archive / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            os.replace(target, prior)
        try:
            os.replace(stage, target)
        except Exception:
            if prior is not None:
                os.replace(prior, target)
            raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return target


def _write_entrypoints(installed: Path) -> None:
    binaries = bin_home()
    applications = data_home() / "applications"
    binaries.mkdir(mode=0o755, parents=True, exist_ok=True)
    applications.mkdir(mode=0o755, parents=True, exist_ok=True)

    launcher = binaries / "macrice"
    desktop = applications / "macrice.desktop"
    _check_entrypoints()
    content = '#!/bin/sh\n' + LAUNCHER_MARKER + '\nexec /usr/bin/python3 "' + str(installed / "launcher.py") + '" "$@"\n'
    _atomic_write(launcher, content, 0o755)

    desktop_content = (
        "[Desktop Entry]\nType=Application\nVersion=1.0\n"
        "Name=MacRice Settings\nComment=Manage the macOS-inspired XFCE desktop\n"
        f'Exec="{launcher}" gui\n'
        f"Icon={installed / 'assets/macrice-symbolic.svg'}\n"
        "Terminal=false\nCategories=Settings;Utility;\nStartupNotify=true\n"
        f"{DESKTOP_MARKER}\n"
    )
    _atomic_write(desktop, desktop_content, 0o644)


def _check_entrypoints() -> None:
    """Never replace another application's command or desktop entry."""
    candidates = (
        (bin_home() / "macrice", LAUNCHER_MARKER),
        (data_home() / "applications/macrice.desktop", DESKTOP_MARKER),
    )
    for path, marker in candidates:
        if path.is_symlink() or (path.exists() and (
            not path.is_file() or marker not in path.read_text(encoding="utf-8", errors="replace")
        )):
            raise InstallationError(f"Unmanaged file at {path}; nothing replaced.")


def _atomic_write(target: Path, content: str, mode: int) -> None:
    fd, temporary = tempfile.mkstemp(prefix=".macrice-", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)


def install(options: InstallOptions, source: Path | None = None, output=print) -> Path | None:
    if os.geteuid() == 0:
        raise InstallationError("Run as your normal desktop user, never with sudo.")
    source = source or project_root()
    _check_layout(source)
    _check_existing(data_home() / "macrice")
    _check_entrypoints()
    _check_system_package()

    commands = plan(source, options)
    if options.dry_run:
        output("Dry run: no files or XFCE settings will be changed.")
        output("Plank, XFCE themes, icons and the XFCE Panel stay untouched.")
        for name, argv in commands:
            output(f"  {name}: {' '.join(argv)}")
        from .plank import installed as plank_installed
        output("  Plank: " + ("existing system dock detected; preserved" if plank_installed()
                             else "not installed; optionally use 'sudo apt install plank'"))
        return None

    # The bundle is kept installed for later GUI-driven repairs. Each component
    # then uses its own battle-tested user-local upgrade and backup procedure.
    installed = _install_manager(source)
    for name, _ in commands:
        argv = dict(plan(installed, options))[name]
        output(f"Installing {name}...")
        try:
            result = subprocess.run(
                argv, cwd=installed / "components" /
                {"MacMenu": "macmenu", "Control Center": "control-center", "MacBar": "macbar"}[name],
                capture_output=True, text=True, timeout=90, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise InstallationError(f"{name} did not finish: {exc}") from exc
        if result.returncode:
            # Show a bounded relevant error without dumping user-specific logs.
            detail = (result.stderr or result.stdout).strip()[-900:]
            raise InstallationError(f"{name} installation stopped: {detail}")
        output(f"  {name}: installed")

    _write_entrypoints(installed)
    from .plank import installed as plank_installed
    if plank_installed():
        output("Plank: existing dock detected; no changes to its settings or launchers.")
    else:
        output("Plank: not installed. Optional on Mint: sudo apt install plank")
    output("MacRice installed. Run 'macrice gui' for the manager.")
    output("The XFCE Panel was not replaced. No theme or icon was changed.")
    return installed
