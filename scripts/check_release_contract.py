#!/usr/bin/env python3
"""Read-only, dependency-free RiceBowl release metadata and sign-off gate.

This gate intentionally cannot approve physical-device acceptance. A human
must record it in the tracked sign-off file after testing on real hardware.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[1]
SIGNOFF_FILE = ".github/release-signoff-1.0.json"
REQUIRED_EVIDENCE = ("login_and_recovery", "xfce_rollback", "xwayland_and_portals",
                     "shell_and_hardware", "authoring_and_switch", "performance")


class ReleaseGateError(ValueError):
    """The requested release is not supported by the recorded evidence."""


def read_version(root: Path) -> str:
    """Check the user-visible module and wheel metadata agree, without imports."""
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    project = re.search(r"(?ms)^\[project\]\s*(.*?)(?=^\[|\Z)", pyproject)
    if project is None:
        raise ReleaseGateError("Missing pyproject.toml [project] metadata")
    package = re.search(r'^version\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"\s*$',
                        project.group(1), re.M)
    module = re.search(r'^__version__\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"\s*$',
                       (root / "macrice/__init__.py").read_text(encoding="utf-8"), re.M)
    if package is None or module is None or package.group(1) != module.group(1):
        raise ReleaseGateError("Python package and CLI versions differ or are invalid")
    return package.group(1)


def check_release(root: Path, tag: str | None) -> str:
    version = read_version(root)
    if tag is None:
        return version
    candidate = re.fullmatch(r"v(\d+\.\d+\.\d+)(?:-rc\.([1-9]\d*))?", tag)
    if candidate is None or candidate.group(1) != version:
        raise ReleaseGateError("Tag and source version differ or tag is not vX.Y.Z[-rc.N]")
    if tag == "v1.0.0":
        file = root / SIGNOFF_FILE
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ReleaseGateError("Missing or invalid 1.0 hardware sign-off") from exc
        if not isinstance(data, dict) or set(data) != {"status", "device", "date_utc", "evidence"}:
            raise ReleaseGateError("Incomplete 1.0 hardware sign-off")
        evidence = data["evidence"]
        if (data["status"] != "approved"
                or not isinstance(data["device"], str) or not data["device"].strip()
                or not isinstance(data["date_utc"], str)
                or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", data["date_utc"])
                or not isinstance(evidence, dict)
                or set(evidence) != set(REQUIRED_EVIDENCE)
                or any(not isinstance(evidence[key], str) or not evidence[key].strip()
                       for key in REQUIRED_EVIDENCE)):
            raise ReleaseGateError("RiceBowl 1.0 requires documented real-device acceptance")
    return version


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", help="Release tag to validate (e.g. v1.0.0-rc.1)")
    args = parser.parse_args(argv)
    try:
        version = check_release(SOURCE_ROOT, args.tag)
    except (ReleaseGateError, OSError) as exc:
        print(f"RiceBowl release gate: BLOCKED — {exc}", file=sys.stderr)
        return 1
    print(f"RiceBowl release metadata: {version}; tag gate: {args.tag or 'not requested'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
