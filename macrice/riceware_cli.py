"""Small manual/test CLI for shared riceware before any renderer migration."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path


def add_commands(commands) -> None:
    riceware = commands.add_parser("riceware", help="Inspect and use opt-in riceware backends")
    backends = riceware.add_subparsers(dest="riceware_backend", required=True)
    backends.add_parser("manifest", help="Inspect the versioned renderer API without probing hardware")
    packs = backends.add_parser("packs", help="Discover presets and import verified visual Rice packs")
    packs.add_argument("action", choices=("list", "show", "check", "template", "apply",
                                          "build", "inspect", "import", "remove"))
    packs.add_argument("id", nargs="?", help="Built-in style or installed user pack ID")
    packs.add_argument("--yes", action="store_true", help="Confirm applying a pack to the XFCE desktop")
    packs.add_argument("--archive", type=Path,
                       help="Local .zip Rice pack to inspect or import")
    packs.add_argument("--directory", type=Path, help="Draft Rice pack directory to build")
    packs.add_argument("--output", type=Path, help="New ZIP archive path to build (never overwritten)")
    packs.add_argument("--accept-license", action="store_true",
                       help="Confirm you reviewed and accept the archive's license and origin")
    spice = backends.add_parser("spice", help="Read real hardware state or request an explicit change")
    spice.add_argument("action", choices=("status", "get", "set"))
    spice.add_argument("name", nargs="?")
    spice.add_argument("value", nargs="?")
    pop = backends.add_parser("pop", help="Use the existing XFCE notification service")
    pop.add_argument("action", choices=("status", "list", "mark-read", "dismiss",
                                        "clear", "quiet", "send"))
    pop.add_argument("value", nargs="?")
    pop.add_argument("body", nargs="?")
    pop.add_argument("--yes", action="store_true", help="Confirm irreversible history clearing")
    plate = backends.add_parser("plate", help="Inspect desktop, preview ricePlate or manage owned shortcuts")
    plate.add_argument("action", choices=("status", "install", "remove", "preview"))
    plate.add_argument("--profile", choices=("xp", "win7"))
    from .riceware.profiles import PROFILE_FAMILIES
    plate.add_argument("--style", choices=tuple(PROFILE_FAMILIES), default=None,
                       help="Rice-specific desktop preview style (default: winxp)")
    wine = backends.add_parser("wine", help="Manage private Wine prefixes without system changes")
    wine_actions = wine.add_subparsers(dest="action", required=True)
    for action in ("status", "list", "apps"):
        wine_actions.add_parser(action)
    for action in ("create", "resume", "log"):
        wine_actions.add_parser(action).add_argument("name")
    for action in ("run", "register"):
        entry = wine_actions.add_parser(action)
        entry.add_argument("name", help="Managed prefix")
        if action == "register":
            entry.add_argument("identifier", help="Stable application ID")
            entry.add_argument("title", help="Display name")
        entry.add_argument("executable")
        entry.add_argument("arguments", nargs=argparse.REMAINDER)
    for action in ("unregister", "run-app"):
        entry = wine_actions.add_parser(action)
        entry.add_argument("name", help="Managed prefix")
        entry.add_argument("identifier", help="Application ID")
        if action == "unregister":
            entry.add_argument("--yes", action="store_true", help="Confirm removing this registration")


def _dump(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False,
                     default=lambda item: asdict(item) if is_dataclass(item)
                     else str(item)))


def _parse_value(name: str, value: str | None):
    from .riceware.spice import ACTION_SPECS

    if name not in ACTION_SPECS:
        raise ValueError(f"Unknown riceSpice action: {name}")
    kind = ACTION_SPECS[name].kind
    if kind == "none":
        if value is not None:
            raise ValueError(f"{name} does not take a value")
        return None
    if value is None:
        raise ValueError(f"{name} requires a value")
    if kind == "boolean":
        if value not in ("on", "off"):
            raise ValueError("Use on or off for boolean controls")
        return value == "on"
    if kind == "integer":
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError("Volume and brightness must be whole numbers") from exc
    return value


def run(args) -> int:
    if args.riceware_backend == "manifest":
        from .riceware import manifest

        _dump(manifest())
        return 0
    if args.riceware_backend == "packs":
        from .riceware import packs
        from .riceware import pack_import

        if args.action == "build":
            if args.id or args.yes or args.archive or args.accept_license or not args.directory or not args.output:
                raise ValueError("Use packs build --directory DRAFT --output PACK.zip")
            _dump(pack_import.build_archive(args.directory, args.output))
            return 0
        if args.directory or args.output:
            raise ValueError("--directory and --output are only for packs build")
        if args.action in ("inspect", "import"):
            if args.id or args.yes or not args.archive or (args.action == "inspect" and args.accept_license):
                raise ValueError("Use packs inspect|import --archive LOCAL.zip (import also requires --accept-license)")
            if args.action == "inspect":
                _dump(pack_import.inspect_archive(args.archive))
            else:
                installed = pack_import.install_archive(args.archive, accept_license=args.accept_license)
                _dump({"installed": installed.id, "revision": installed.revision,
                       "assets": installed.asset_types, "activated": False})
            return 0
        if args.archive or args.accept_license:
            raise ValueError("--archive and --accept-license are only for packs inspect|import")

        found, warnings = packs.discover()
        if args.action == "list":
            if args.id or args.yes:
                raise ValueError("packs list accepts no ID or --yes")
            _dump({"schema_version": packs.SCHEMA_VERSION,
                   "visual_schema_version": pack_import.VERSION,
                   "packs": [{"id": p.id, "name": p.name, "base_style": p.base_style,
                              "source": p.source, "assets": p.asset_types} for p in found], "warnings": warnings})
            return 0
        if not args.id:
            raise ValueError(f"packs {args.action} requires a pack ID")
        pack = packs.resolve(args.id)
        if args.action != "apply" and args.yes:
            raise ValueError("--yes applies only to packs apply")
        if args.action == "show":
            _dump(pack.manifest())
            return 0
        if args.action == "template":
            _dump({"schema_version": packs.SCHEMA_VERSION,
                   "id": f"my-{pack.base_style}", "name": f"My {pack.name}",
                   "base_style": pack.base_style,
                   "description": "A named preset based on a supported RiceBowl style"})
            return 0
        if args.action == "check":
            result = packs.capabilities(pack)
            if pack.source == "installed":
                try:
                    pack_import.verify_installed(pack)
                    result["assets_valid"] = True
                except (OSError, ValueError) as exc:
                    result["assets_valid"] = False
                    result["asset_error"] = str(exc)
                result["ready"] = result["ready"] and result["assets_valid"]
            _dump(result)
            return 0 if result["ready"] else 1
        if args.action == "remove":
            if pack.source != "installed":
                raise ValueError("Only imported visual packs can be removed")
            if not args.yes:
                raise ValueError("Removing a pack requires --yes and an inactive rice")
            recovery = pack_import.remove_installed(pack)
            _dump({"removed": pack.id, "recovery": str(recovery)})
            return 0
        if not args.yes:
            raise ValueError("Applying a pack changes desktop settings; review packs show/check, then use --yes")
        # No arbitrary commands, assets or scripts can be supplied by JSON.
        # All changes still use the existing journaled, reversible rice engine.
        from .shell_session import install_login_reconciler, sync_theme

        style, _wallpaper = pack_import.style_for(pack)
        backup = pack_import.apply_pack(pack)
        notices = []
        try:
            install_login_reconciler()
        except OSError:
            notices.append("Login reconciler could not be installed")
        notices.extend(sync_theme(style.gtk))
        _dump({"applied": pack.id, "base_style": pack.base_style,
               "backup": str(backup), "session_warnings": notices})
        return 1 if notices else 0
    if args.riceware_backend == "spice":
        from .riceware import spice

        if args.action == "status":
            if args.name is not None or args.value is not None:
                raise ValueError("spice status takes no other arguments")
            _dump(spice.snapshot())
        elif args.action == "get":
            if args.name is None or args.value is not None:
                raise ValueError("Usage: riceware spice get CAPABILITY")
            _dump(spice.read(args.name))
        else:
            if args.name is None:
                raise ValueError("Usage: riceware spice set ACTION [VALUE]")
            result = spice.change(args.name, _parse_value(args.name, args.value))
            _dump(result)
            return 0 if result.status == "ok" else 1
        return 0
    if args.riceware_backend == "pop":
        from .riceware import pop

        if args.action in ("status", "list", "clear") and (
                args.value is not None or args.body is not None):
            raise ValueError(f"pop {args.action} takes no positional arguments")
        if args.action not in ("send", "status", "list", "clear") and args.body is not None:
            raise ValueError(f"pop {args.action} takes only one value")
        if args.action == "status":
            _dump(pop.status())
        elif args.action == "list":
            _dump(pop.history())
        elif args.action == "quiet":
            if args.value not in ("on", "off"):
                raise ValueError("Usage: riceware pop quiet on|off")
            _dump({"quiet": pop.set_quiet_mode(args.value == "on")})
        elif args.action == "send":
            if args.value is None:
                raise ValueError("Usage: riceware pop send SUMMARY [BODY]")
            pop.send(args.value, args.body or "")
        elif args.action == "dismiss":
            if args.value is None:
                raise ValueError("Usage: riceware pop dismiss ID")
            pop.dismiss(args.value)
        elif args.action == "mark-read":
            pop.mark_read((args.value,) if args.value else None)
        elif args.action == "clear":
            if not args.yes:
                raise ValueError("Clearing notification history requires --yes")
            pop.clear_history()
        return 0
    if args.riceware_backend == "plate":
        from .riceware import plate

        if args.action == "preview":
            if args.profile is not None:
                raise ValueError("ricePlate preview uses --style, not --profile")
            from .riceware.plate_preview import run
            return run(args.style or "winxp")
        if args.style is not None:
            raise ValueError("--style applies only to ricePlate preview")
        if args.action == "status":
            _dump(plate.snapshot())
        else:
            if args.profile is None:
                raise ValueError("Install/remove requires --profile xp|win7")
            changed, preserved = plate.manage_shortcuts(args.profile, args.action)
            _dump({"changed": changed, "preserved": preserved})
        return 0
    if args.riceware_backend == "wine":
        from .riceware import wine
        from .riceware import wine_apps

        if args.action == "status":
            _dump({"wine_version": wine.wine_version(), "prefixes": wine.list_prefixes()})
        elif args.action == "list":
            _dump(wine.list_prefixes())
        elif args.action == "apps":
            _dump(wine_apps.list_apps())
        elif args.action in ("create", "resume"):
            _dump(wine.create_prefix(args.name) if args.action == "create"
                  else wine.resume_prefix(args.name))
        elif args.action == "log":
            print(wine.read_init_log(args.name))
        elif args.action == "register":
            _dump(wine_apps.register(args.name, args.identifier, args.title,
                                     args.executable, tuple(args.arguments)))
        elif args.action == "unregister":
            if not args.yes:
                raise ValueError("Unregistering an app requires --yes")
            wine_apps.unregister(args.name, args.identifier)
        elif args.action == "run-app":
            _dump({"pid": wine_apps.launch_app(args.name, args.identifier)})
        elif args.action == "run":
            _dump({"pid": wine.launch(args.name, args.executable, tuple(args.arguments))})
        return 0
    raise ValueError("Unknown riceware backend")
