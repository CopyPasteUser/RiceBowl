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
    "dock": ("plank",),
}


def open_component(name: str) -> None:
    if name == "dock":
        from .plank import open_dock
        open_dock()
        return
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
    commands.add_parser("hub", help="Open RiceHub: discover, apply and restore desktop rices")
    commands.add_parser("preview", help="Preview the complete desktop and apply or restore its Rice")
    commands.add_parser("status", help="Show installed components and the detected appearance")
    commands.add_parser("inspect", help="Print a safe, read-only JSON appearance report")
    installer = commands.add_parser("install", help="Install or repair the three bundled apps; preserve Plank")
    installer.add_argument("--dry-run", action="store_true", help="Do not write or start anything")
    installer.add_argument("--no-start", action="store_true", help="Install without launching GTK")
    installer.add_argument("--bar-autostart", action="store_true", help="Add MacBar to login without stopping XFCE Panel")
    theme = commands.add_parser("theme", help="Apply a consistent theme to the three apps only")
    theme.add_argument("preset", choices=PRESETS)
    opener = commands.add_parser("open", help="Launch/toggle one component")
    opener.add_argument("component", choices=tuple(COMMANDS))
    dock = commands.add_parser("dock", help="Inspect the existing dock or open its native preferences")
    dock.add_argument("action", choices=("status", "preferences"))
    rice = commands.add_parser("rice", help="Plan, apply or restore the complete XFCE desktop Rice")
    rice.add_argument("action", choices=("plan", "apply", "restore"))
    from .rice import STYLES
    rice.add_argument("style", nargs="?", choices=tuple(STYLES))
    profile = commands.add_parser("performance", help="Apply a Control Center resource profile")
    profile.add_argument("profile", choices=("light", "balanced", "visual", "report"))
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command in (None, "gui"):
            from .gui import run
            return run()
        if args.command == "hub":
            from .hub import run
            return run()
        if args.command == "preview":
            from .preview import run
            return run()
        if args.command == "rice":
            from .rice import RiceError, apply as apply_rice, plan as plan_rice, restore as restore_rice
            if args.action == "restore":
                if args.style is not None:
                    raise RiceError("Restore takes no style argument")
                backup = restore_rice()
                print("Desktop restored from:", backup)
                skipped_file = backup / "skipped.json"
                if skipped_file.is_file():
                    skipped = json.loads(skipped_file.read_text(encoding="utf-8"))
                    print("Preserved newer edits (not overwritten):", ", ".join(skipped))
            elif args.style is None:
                raise RiceError("Choose night or day (example: macrice rice plan night)")
            elif args.action == "plan":
                changes, _, _, _ = plan_rice(args.style)
                number = sum(item["before"] != item["after"] for item in changes)
                print(f"{args.style.title()} Rice is available. {number} desktop settings would change.")
                print("Themes, icons, fonts and wallpaper were validated; this was read-only.")
            else:
                print("Rice applied; backup:", apply_rice(args.style))
            return 0
        if args.command == "performance":
            from .performance import apply_profile, measure_processes
            if args.profile == "report":
                processes = measure_processes()
                if not processes:
                    print("No MacRice components or Plank processes found for this user.")
                for item in processes:
                    pss = f"{item['pss_kib'] / 1024:.1f} MiB" if item["pss_kib"] is not None else "unavailable"
                    cpu = f"{item['cpu_percent']:.1f}%" if item["cpu_percent"] is not None else "unavailable"
                    print(f"{item['name']} (PID {item['pid']}): PSS {pss} · CPU {cpu}")
            else:
                print(f"Performance profile {args.profile} applied; backup:", apply_profile(args.profile))
            return 0
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
            if appearance.plank_theme:
                print("  Plank theme:", appearance.plank_theme)
            return 0
        if args.command == "dock":
            from .plank import installed, open_dock, preferences
            if args.action == "preferences":
                print(open_dock(show_preferences=True))
            else:
                print("Plank:", "installed" if installed() else "not installed")
                print(json.dumps(preferences().__dict__, indent=2, ensure_ascii=False))
            return 0
        if args.command == "install":
            install(InstallOptions(args.dry_run, args.no_start, args.bar_autostart))
            return 0
        if args.command == "theme":
            backup = apply_preset(args.preset)
            print(f"Applied {args.preset} to MacMenu, Control Center and MacBar.")
            print("Backups:", backup)
            print("Running MacRice apps reload their theme automatically.")
            return 0
        if args.command == "open":
            open_component(args.component)
            return 0
    except (InstallationError, ValueError, OSError, RuntimeError) as exc:
        print("MacRice:", exc, file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
