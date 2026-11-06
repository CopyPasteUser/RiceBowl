"""A public 1.0 tag cannot outrun version metadata or device acceptance."""

import json
import tempfile
import unittest
from pathlib import Path

from scripts.check_release_contract import ReleaseGateError, check_release, read_version


class ReleaseContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "macrice").mkdir()
        (self.root / ".github").mkdir()
        self.write_version("0.9.1", "0.9.1")

    def write_version(self, package: str, module: str):
        (self.root / "pyproject.toml").write_text(
            f'[project]\nname = "ricebowl-xfce"\nversion = "{package}"\n\n[tool.ruff]\n',
            encoding="utf-8")
        (self.root / "macrice/__init__.py").write_text(
            f'__version__ = "{module}"\n', encoding="utf-8")

    def test_repository_version_metadata_matches(self):
        from macrice import __version__
        self.assertEqual(read_version(Path(__file__).resolve().parents[1]), __version__)

    def test_mismatched_metadata_and_tags_are_blocked(self):
        self.write_version("0.9.1", "0.9.0")
        with self.assertRaisesRegex(ReleaseGateError, "versions differ"):
            check_release(self.root, None)
        self.write_version("0.9.1", "0.9.1")
        for tag in ("v1.0.0", "v0.9.1-rc.0", "0.9.1", "v0.9.1-garbage"):
            with self.subTest(tag=tag), self.assertRaises(ReleaseGateError):
                check_release(self.root, tag)
        self.assertEqual(check_release(self.root, "v0.9.1-rc.1"), "0.9.1")

    def test_stable_one_zero_requires_explicit_evidence_for_every_gate(self):
        self.write_version("1.0.0", "1.0.0")
        self.assertEqual(check_release(self.root, "v1.0.0-rc.1"), "1.0.0")
        with self.assertRaisesRegex(ReleaseGateError, "sign-off"):
            check_release(self.root, "v1.0.0")
        signoff = {"status": "pending", "device": "ThinkPad X1 Yoga 2nd",
                   "date_utc": "2026-11-06", "evidence": {
                       name: "Tested: QA log" for name in (
                           "login_and_recovery", "xfce_rollback", "xwayland_and_portals",
                           "shell_and_hardware", "authoring_and_switch", "performance")}}
        location = self.root / ".github/release-signoff-1.0.json"
        location.write_text(json.dumps(signoff), encoding="utf-8")
        with self.assertRaisesRegex(ReleaseGateError, "real-device acceptance"):
            check_release(self.root, "v1.0.0")
        signoff["status"] = "approved"
        location.write_text(json.dumps(signoff), encoding="utf-8")
        self.assertEqual(check_release(self.root, "v1.0.0"), "1.0.0")


if __name__ == "__main__":
    unittest.main()
