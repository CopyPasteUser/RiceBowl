"""Small, testable CLI contract for desktop launchers and keyboard shortcuts."""


COMMANDS = {
    "--toggle": "toggle",
    "--show": "show",
    "--hide": "hide",
    "--preferences": "preferences",
    "--quit": "quit",
    "--version": "version",
}


def resolve_command(arguments: list[str]) -> str:
    if not arguments:
        return "toggle"
    if len(arguments) == 1 and arguments[0] in COMMANDS:
        return COMMANDS[arguments[0]]
    raise ValueError(
        "Invalid command. Options: --toggle, --show, --hide, "
        "--preferences, --quit, --version"
    )
