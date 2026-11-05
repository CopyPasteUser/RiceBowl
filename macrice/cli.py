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
    commands.add_parser("hub", help="Open RiceBowl: discover, apply and restore desktop rices")
    commands.add_parser("preview", help="Preview the complete desktop and apply or restore its Rice")
    aero = commands.add_parser("aero-shell", help="Run or toggle the Windows 7-inspired taskbar and Start menu")
    ten_shell = commands.add_parser("windows10-shell", help="Run or quit the Windows 10-inspired taskbar and Start menu")
    ten_shell.add_argument("--quit", action="store_true")
    ten_shell.add_argument("--toggle-menu", action="store_true")
    ten_shell.add_argument("--actions", action="store_true")
    aero.add_argument("--quit", action="store_true", help="Stop the resident Aero taskbar")
    aero.add_argument("--toggle-menu", action="store_true")
    aero.add_argument("--control", action="store_true", help="Toggle the Aero Control Panel")
    for key in ("winxp", "winclassic", "chromeos", "frutiger"):
        shell = commands.add_parser(f"{key}-shell", help=f"Run or toggle the {key} taskbar and launcher")
        shell.add_argument("--quit", action="store_true")
        shell.add_argument("--toggle-menu", action="store_true")
        shell.add_argument("--control", action="store_true")
        if key == "frutiger":
            trace = shell.add_mutually_exclusive_group()
            trace.add_argument("--trace-actions", action="store_true",
                               help="Record only fixed Frutiger UI click/outcome labels to a private bounded file")
            trace.add_argument("--trace-stop", action="store_true", help="Stop Frutiger UI evidence recording")
            trace.add_argument("--trace-path", action="store_true", help="Print evidence file location without running the shell")
    commands.add_parser("session-sync", help="Reconcile active rice after XFCE autostart")
    commands.add_parser("session-menu", help="Toggle the active rice's application menu")
    commands.add_parser("session-control", help="Toggle the active rice's control panel")
    commands.add_parser("session-keys-restore", help="Restore the previous Super/Right Control shortcuts")
    xp_desktop = commands.add_parser("winxp-desktop", help="Manage optional XP XFDesktop shortcuts safely")
    xp_desktop.add_argument("action", choices=("status", "install", "remove"))
    commands.add_parser("status", help="Show installed components and the detected appearance")
    commands.add_parser("inspect", help="Print a safe, read-only JSON appearance report")
    doctor = commands.add_parser("doctor", help="Run read-only RiceBowl/XFCE health checks")
    doctor.add_argument("--json", action="store_true", help="Print machine-readable health results")
    from .riceware.profiles import PROFILE_FAMILIES
    doctor.add_argument("--style", choices=tuple(PROFILE_FAMILIES),
                        help="Also preflight the chosen rice's real assets and desktop settings")
    app_compat = commands.add_parser("app-compat", help="Inspect a window's theme compatibility without modifying apps")
    target = app_compat.add_mutually_exclusive_group(required=True)
    target.add_argument("--select", action="store_true", help="Select an X11 window with the pointer")
    target.add_argument("--window-id", metavar="HEX", help="Inspect an existing hexadecimal X11 window ID")
    app_compat.add_argument("--json", action="store_true", help="Print sanitized machine-readable results")
    updater = commands.add_parser("update", help="Inspect or explicitly install a verified fast-forward revision")
    updater.add_argument("action", choices=("check", "apply"))
    updater.add_argument("--source", type=Path, help="Trusted RiceBowl Git checkout (defaults to ~/RiceBowl)")
    updater.add_argument("--refresh", action="store_true", help="Fetch origin/main before checking")
    updater.add_argument("--yes", action="store_true", help="Confirm a staged update with recovery")
    updater.add_argument("--revision", help="Optional exact 40-digit revision from update check")
    updater.add_argument("--preserve-checkout", action="store_true",
                         help="Opt in to installing from official Git while leaving a dirty source tree unchanged")
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
    rice.add_argument("action", choices=("plan", "apply", "restore", "repair-assets"))
    from .rice import STYLES
    rice.add_argument("style", nargs="?", choices=tuple(STYLES))
    profile = commands.add_parser("performance", help="Apply a Control Center resource profile")
    profile.add_argument("profile", choices=("light", "balanced", "visual", "report", "desktop"))
    profile.add_argument("--json", action="store_true", help="Machine-readable on-demand report")
    profile.add_argument("--samples", type=int, default=3, metavar="N",
                         help="Read 1–9 short CPU/PSS samples for report/desktop (default: 3)")
    from .riceware_cli import add_commands
    add_commands(commands)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "riceware":
            from .riceware_cli import run as run_riceware
            return run_riceware(args)
        if args.command in (None, "gui"):
            from .gui import run
            return run()
        if args.command == "hub":
            from .hub import run
            return run()
        if args.command == "preview":
            from .preview import run
            return run()
        if args.command == "aero-shell":
            from .aero_shell import run
            suffix = ["--quit"] if args.quit else ["--control"] if args.control else ["--toggle-menu"] if args.toggle_menu else []
            return run(["ricehub-aero-shell", *suffix])
        if args.command == "windows10-shell":
            from .ten_shell import run
            suffix = ["--quit"] if args.quit else ["--actions"] if args.actions else ["--toggle-menu"] if args.toggle_menu else []
            return run(["ricehub-ten-shell", *suffix])
        if args.command in ("winxp-shell", "winclassic-shell", "chromeos-shell", "frutiger-shell"):
            from .aero_shell import run
            profile = args.command.removesuffix("-shell")
            if profile == "frutiger" and args.trace_path:
                from .interaction_trace import trace_path
                print(trace_path())
                return 0
            suffix = (["--trace-actions"] if profile == "frutiger" and args.trace_actions else
                      ["--trace-stop"] if profile == "frutiger" and args.trace_stop else
                      ["--quit"] if args.quit else ["--control"] if args.control else
                      ["--toggle-menu"] if args.toggle_menu else [])
            return run([f"ricehub-{profile}-shell", *suffix], profile=profile)
        if args.command in ("session-menu", "session-control"):
            from .session_shortcuts import dispatch
            dispatch("menu" if args.command == "session-menu" else "control")
            return 0
        if args.command == "session-keys-restore":
            from .session_shortcuts import restore_bindings
            for warning in restore_bindings():
                print("Shortcut warning:", warning, file=sys.stderr)
            return 0
        if args.command == "winxp-desktop":
            from .luna_desktop import desktop_path, manage

            changed, preserved = manage(args.action)
            print("XP desktop:", desktop_path())
            for name in changed:
                print(" ", "Installed" if args.action == "install" else "Removed", name)
            for name in preserved:
                print("  Preserved", name)
            if args.action == "status" and not preserved:
                print("  No XP shortcuts currently installed")
            return 0
        if args.command == "session-sync":
            from .shell_session import login_reconcile
            warnings = login_reconcile()
            for warning in warnings:
                print("Session warning:", warning, file=sys.stderr)
            return 1 if warnings else 0
        if args.command == "rice":
            from .rice import RiceError, apply as apply_rice, plan as plan_rice, restore as restore_rice
            if args.action == "restore":
                if args.style is not None:
                    raise RiceError("Restore takes no style argument")
                backup = restore_rice()
                print("Desktop restored from:", backup)
                from .rice import XfceBackend
                try:
                    theme = XfceBackend().get("xfconf", "xsettings", "/Net/ThemeName")
                    from .shell_session import sync_theme
                    for warning in sync_theme(theme):
                        print("Taskbar warning:", warning, file=sys.stderr)
                except (OSError, RuntimeError) as exc:
                    print("Taskbar warning:", exc, file=sys.stderr)
                skipped_file = backup / "skipped.json"
                if skipped_file.is_file():
                    skipped = json.loads(skipped_file.read_text(encoding="utf-8"))
                    print("Preserved newer edits (not overwritten):", ", ".join(skipped))
            elif args.style is None:
                raise RiceError("Choose night or day (example: macrice rice plan night)")
            elif args.action == "repair-assets":
                from .rice import repair_assets
                backups = repair_assets(args.style)
                print("RiceBowl asset repair complete. Original assets archived at:")
                for backup in backups:
                    print(" ", backup)
                print("Review these backups before deletion; now choose Apply rice.")
            elif args.action == "plan":
                changes, _, _, _ = plan_rice(args.style)
                number = sum(item["before"] != item["after"] for item in changes)
                print(f"{args.style.title()} Rice is available. {number} desktop settings would change.")
                print("Themes, icons, fonts and wallpaper were validated; this was read-only.")
            else:
                print("Rice applied; backup:", apply_rice(args.style))
                from .shell_session import install_login_reconciler
                try:
                    install_login_reconciler()
                except OSError as exc:
                    print("Session autostart warning:", exc, file=sys.stderr)
                from .shell_session import sync_theme
                from .rice import STYLES
                for warning in sync_theme(STYLES[args.style].gtk):
                    print("Taskbar warning:", warning, file=sys.stderr)
            return 0
        if args.command == "performance":
            from .performance import (apply_profile, desktop_session_report,
                                      measure_processes, summarize_samples)
            if args.profile in ("report", "desktop"):
                if not 1 <= args.samples <= 9:
                    raise ValueError("--samples must be between 1 and 9")
                desktop = args.profile == "desktop"
                samples = [measure_processes(include_desktop=True) if desktop else measure_processes()
                           for _ in range(args.samples)]
                result = desktop_session_report(samples) if desktop else summarize_samples(samples)
                if args.json:
                    print(json.dumps(result, indent=2))
                    return 0
                if not result["components"]:
                    print("No recognized XFCE/RiceBowl processes found for this user." if desktop else
                          "No RiceBowl components or Plank processes found for this user.")
                for item in result["components"]:
                    pss = f"{item['pss_kib'] / 1024:.1f} MiB" if item["pss_kib"] is not None else "unavailable"
                    cpu = f"{item['cpu_percent']:.1f}%" if item["cpu_percent"] is not None else "unavailable"
                    threads = str(item["threads"]) if item["threads"] is not None else "unavailable"
                    role = f" [{item['role']}]" if desktop else ""
                    print(f"{item['name']}{role} (PID {item['pid']}): PSS {pss} · CPU {cpu} · Threads {threads}")
                if result["total_pss_kib"] is not None:
                    print(f"Sampled total PSS: {result['total_pss_kib'] / 1024:.1f} MiB"
                          + (" (partial)" if result["partial"] else ""))
                if desktop:
                    total = result["xfce_pss_kib"]
                    print("XFCE sampled PSS: " + (f"{total / 1024:.1f} MiB" if total is not None
                                                   else "unavailable"))
                    for warning in result["warnings"]:
                        print("Overlap warning:", warning)
                    print("Read-only inventory: core/shared services were not stopped.")
            else:
                if args.json or args.samples != 3:
                    raise ValueError("--json and --samples apply only to performance report/desktop")
                print(f"Performance profile {args.profile} applied; backup:", apply_profile(args.profile))
            return 0
        if args.command == "inspect":
            print(json.dumps(detect().as_dict(), indent=2, ensure_ascii=False))
            return 0
        if args.command == "doctor":
            from .doctor import diagnose, summary
            checks = diagnose(style=args.style)
            if args.json:
                print(json.dumps({"checks": [item.as_dict() for item in checks],
                                  "summary": dict(zip(("ok", "warning", "info"), summary(checks)))},
                                 indent=2, ensure_ascii=False))
            else:
                for item in checks:
                    print(f"[{item.status.upper():7}] {item.message}")
                    if item.advice:
                        print("          " + item.advice)
                ok, warnings, optional = summary(checks)
                print(f"{ok} ready · {warnings} attention · {optional} optional")
            return 1 if any(item.status == "warning" for item in checks) else 0
        if args.command == "app-compat":
            from .app_compat import format_report, inspect_window
            report = inspect_window(window_id=args.window_id)
            print(json.dumps(report, indent=2, ensure_ascii=False) if args.json else format_report(report))
            return 0
        if args.command == "update":
            from .updater import UpdateError, apply as apply_update, inspect as inspect_update
            if args.action == "apply":
                if not args.yes:
                    raise UpdateError("Use update check --refresh first, then update apply --yes")
                if args.revision and (len(args.revision) != 40 or any(
                        character not in "0123456789abcdefABCDEF" for character in args.revision)):
                    raise UpdateError("--revision must be a full Git commit SHA (40 hex digits)")
                plan = apply_update(source=args.source, expected_revision=args.revision,
                                    preserve_checkout=args.preserve_checkout)
                print("RiceBowl updated to " + plan.available[:12] if plan.needed else
                      "RiceBowl already up to date")
                if plan.changed:
                    print(f"Source checkout not advanced: {len(plan.changed)} local change(s) preserved in place.")
                print("Restart the manager to load the new code; your desktop rice was not switched.")
            else:
                plan = inspect_update(source=args.source, refresh=args.refresh,
                                      allow_dirty=args.preserve_checkout)
                print("Local revision: " + plan.current[:12])
                print("Installed:      " + (plan.installed[:12] if plan.installed else "unknown (legacy installation)"))
                print("Available:      " + plan.available)
                if plan.changed:
                    print(f"Local files:    {len(plan.changed)} changed; a preserve-mode install will not advance the checkout")
                print(f"New source commits: {plan.commits}" +
                      (" — run update apply --yes (optionally --revision SHA) after review" if plan.needed else
                       " — installed version current (cached; use --refresh to check GitHub)"))
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
