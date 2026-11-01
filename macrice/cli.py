"""Command-line entrypoint shared by the launcher, installer and GTK manager."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from . import __version__
from .environment import bin_home, detect, installed_components
from .installer import InstallOptions, InstallationError, install
from .themes import PRESETS, apply_preset


COMMANDS = {
    "menu": ("macmenu", "--toggle"),
    "center": ("macos-control-center-toggle",),
    "bar": ("macbar",),
}


def open_component(name: str) -> None:
    args = COMMANDS[name]
    executable = bin_home() / args[0]
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise InstallationError(f"{name} is not installed; run 'macrice install' first.")
    subprocess.Popen(
        [str(executable), *args[1:]],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        close_fds=True, start_new_session=True,
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="macrice", description="Manage the macOS-inspired XFCE Rice Suite"
    )
    p.add_argument("--version", action="version", version=f"MacRice {__version__}")
    commands = p.add_subparsers(dest="command")
    commands.add_parser("gui", help="Open the native GTK settings manager")
    commands.add_parser("status", help="Show installed components and the detected appearance")
    commands.add_parser("inspect", help="Print a safe, read-only JSON appearance report")
    installer = commands.add_parser("install", help="Install or repair all three components")
    installer.add_argument("--dry-run", action="store_true", help="Do not write or start anything")
    installer.add_argument("--no-start", action="store_true", help="Install without launching GTK")
    installer.add_argument("--bar-autostart", action="store_true", help="Add MacBar to login without stopping XFCE Panel")
    theme = commands.add_parser("theme", help="Apply a consistent theme to the three apps only")
    theme.add_argument("preset", choices=PRESETS)
    opener = commands.add_parser("open", help="Launch/toggle one component")
    opener.add_argument("component", choices=tuple(COMMANDS))
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command in (None, "gui"):
            from .gui import run
            return run()
        if args.command == "inspect":
            print(json.dumps(detect().as_dict(), indent=2, ensure_ascii=False))
            return 0
        if args.command == "status":
            print("MacRice " + __version__)
            for name, value in installed_components().items():
                print(f"  {name}: {'installed' if value else 'not installed'}")
            appearance = detect()
            print("  XFCE GTK theme:", appearance.gtk_theme or "not detected")
            print("  Icon theme:", appearance.icon_theme or "not detected")
            return 0
        if args.command == "install":
            install(InstallOptions(args.dry_run, args.no_start, args.bar_autostart))
            return 0
        if args.command == "theme":
            backup = apply_preset(args.preset)
            print(f"Applied {args.preset} to MacMenu, Control Center and MacBar.")
            print("Backups:", backup)
            print("Restart the three apps to apply the new theme.")
            return 0
        if args.command == "open":
            open_component(args.component)
            return 0
    except (InstallationError, ValueError, OSError) as exc:
        print("MacRice:", exc, file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
