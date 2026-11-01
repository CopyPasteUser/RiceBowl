"""Regression: the installed shell launcher must forward CLI options unchanged."""

import subprocess
from pathlib import Path

from macmenu import __version__


def main() -> int:
    launcher = Path(__file__).resolve().parents[1] / "scripts" / "macmenu"
    try:
        result = subprocess.run(
            ["sh", str(launcher), "--version"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AssertionError("Launcher ignored --version and started the GTK menu") from exc
    assert result.returncode == 0, f"--version failed: {result.stderr.strip()}"
    assert result.stdout.strip() == f"MacMenu {__version__}", result.stdout
    print("Launcher CLI: --version forwarded without opening the GTK window")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
