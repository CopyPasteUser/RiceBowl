"""Small manual/test CLI for shared riceware before any renderer migration."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass


def add_commands(commands) -> None:
    riceware = commands.add_parser("riceware", help="Inspect and use opt-in riceware backends")
    backends = riceware.add_subparsers(dest="riceware_backend", required=True)
    spice = backends.add_parser("spice", help="Read real hardware state or request an explicit change")
    spice.add_argument("action", choices=("status", "get", "set"))
    spice.add_argument("name", nargs="?")
    spice.add_argument("value", nargs="?")
    pop = backends.add_parser("pop", help="Use the existing XFCE notification service")
    pop.add_argument("action", choices=("status", "list", "mark-read", "dismiss", "clear", "quiet", "send"))
    pop.add_argument("value", nargs="?")
    pop.add_argument("body", nargs="?")
    plate = backends.add_parser("plate", help="Inspect desktop or manage owned XFDesktop shortcuts")
    plate.add_argument("action", choices=("status", "install", "remove"))
    plate.add_argument("--profile", choices=("xp", "win7"))
    wine = backends.add_parser("wine", help="Manage private Wine prefixes without system changes")
    wine.add_argument("action", choices=("status", "list", "create", "run"))
    wine.add_argument("name", nargs="?")
    wine.add_argument("executable", nargs="?")
    wine.add_argument("arguments", nargs=argparse.REMAINDER)


def _dump(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False,
                     default=lambda item: asdict(item) if is_dataclass(item)
                     else str(item)))


def _parse_value(name: str, value: str | None):
    if name == "wifi_disconnect":
        if value is not None:
            raise ValueError("wifi_disconnect does not take a value")
        return None
    if value is None:
        raise ValueError(f"{name} requires a value")
    if name in ("wifi", "bluetooth_power", "audio_mute", "microphone_mute"):
        if value not in ("on", "off"):
            raise ValueError("Use on or off for boolean controls")
        return value == "on"
    if name in ("audio_volume", "microphone_volume", "brightness"):
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError("Volume and brightness must be whole numbers") from exc
    return value


def run(args) -> int:
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

        if args.action == "status":
            _dump({"host": "xfce-notifyd", "unread": pop.unread(), "quiet": pop.quiet_mode()})
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
            pop.clear_history()
        return 0
    if args.riceware_backend == "plate":
        from .riceware import plate

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

        if args.action == "status":
            _dump({"wine_version": wine.wine_version(), "prefixes": wine.list_prefixes()})
        elif args.action == "list":
            _dump(wine.list_prefixes())
        elif args.action == "create":
            if args.name is None or args.executable is not None:
                raise ValueError("Usage: riceware wine create NAME")
            _dump(wine.create_prefix(args.name))
        else:
            if args.name is None or args.executable is None:
                raise ValueError("Usage: riceware wine run NAME EXECUTABLE [ARGS...]")
            _dump({"pid": wine.launch(args.name, args.executable, tuple(args.arguments))})
        return 0
    raise ValueError("Unknown riceware backend")
