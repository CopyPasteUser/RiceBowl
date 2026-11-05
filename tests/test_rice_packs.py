"""Data-only Rice pack discovery and session integration, no real desktop writes."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from macrice import cli
from macrice.rice import STYLES
from macrice.riceware import packs
from macrice.riceware.profiles import PROFILE_FAMILIES


class RicePackTests(unittest.TestCase):
    def write_pack(self, folder, name="my-xp", **changes):
        values = {"schema_version": 1, "id": name, "name": "My XP",
                  "base_style": "winxp", **changes}
        target = folder / f"{name}.json"
        target.write_text(json.dumps(values), encoding="utf-8")
        return target

    def test_builtin_catalog_matches_real_rice_styles(self):
        found, warnings = packs.discover(Path("/unlikely/ricebowl/nonexistent/packs"))
        self.assertFalse(warnings)
        self.assertEqual({item.id for item in found}, set(STYLES))
        for item in found:
            with self.subTest(style=item.id):
                manifest = item.manifest()
                self.assertEqual(manifest["family"], PROFILE_FAMILIES[item.id])
                self.assertEqual(manifest["appearance"]["gtk"], STYLES[item.id].gtk)
                self.assertEqual(manifest["schema_version"], 1)
                self.assertEqual(packs.shell_for_theme(STYLES[item.id].gtk),
                                 (manifest["shell"], manifest["family"] == "macos"))
        self.assertEqual(packs.shell_for_theme("Mint-Y"), (None, False))

    def test_user_pack_is_a_safe_named_alias_without_execution_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_pack(root)
            found, warnings = packs.discover(root)
            self.assertEqual(warnings, ())
            item = next(p for p in found if p.id == "my-xp")
            self.assertEqual((item.source, item.base_style), ("user", "winxp"))
            self.assertEqual(packs.resolve("my-xp", root), item)

    def test_rejects_scripts_unrecognized_fields_and_builtin_override(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_pack(root, name="my-xp", command="shutdown -h now")
            self.write_pack(root, name="winxp")
            found, warnings = packs.discover(root)
            self.assertEqual(len(warnings), 2)
            self.assertEqual(len(found), len(STYLES))
            self.assertEqual(packs.resolve("winxp", root).source, "built-in")

    def test_rejects_symlink_oversize_and_unsafe_id_without_reading_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = self.write_pack(root, name="good-pack")
            (root / "linked.json").symlink_to(original)
            big = self.write_pack(root, name="huge-pack", description="a" * (packs.MAX_PACK_BYTES + 5))
            self.write_pack(root, name="bad id")
            found, warnings = packs.discover(root)
            self.assertIn("good-pack", {item.id for item in found})
            self.assertEqual(len(warnings), 3)
            self.assertNotIn(str(root), " ".join(warnings))
            self.assertTrue(big.exists())

    def test_rejects_untrusted_pack_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "real"
            target.mkdir()
            (root / "alias").symlink_to(target, target_is_directory=True)
            _, warnings = packs.discover(root / "alias")
            self.assertEqual(len(warnings), 1)

    def test_group_writable_manifest_is_never_loaded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = self.write_pack(root)
            file.chmod(0o664)
            found, warnings = packs.discover(root)
            self.assertEqual(len(warnings), 1)
            self.assertNotIn("my-xp", [item.id for item in found])

    def test_capability_discovery_is_read_only_and_family_scoped(self):
        with tempfile.TemporaryDirectory() as directory:
            # Empty local launcher directory; only selected fake binaries exist.
            which = lambda name: f"/usr/bin/{name}" if name in {
                "xfconf-query", "gsettings", "xfwm4", "nmcli"} else None
            win = packs.capabilities(packs.resolve("winxp", Path(directory)),
                                      which=which, binaries=Path(directory),
                                      environment={"DISPLAY": ":99", "XDG_SESSION_TYPE": "x11"})
            self.assertTrue(win["ready"])
            self.assertTrue(win["optional"]["NetworkManager"])
            self.assertFalse(win["optional"]["riceExplorer"])
            mac = packs.capabilities(packs.resolve("night", Path(directory)),
                                      which=which, binaries=Path(directory),
                                      environment={"DISPLAY": ":99"})
            self.assertFalse(mac["ready"])
            self.assertFalse(mac["required"]["plank"])
            self.assertFalse(mac["required"]["macbar"])
            self.assertFalse(packs.capabilities(packs.resolve("winxp", Path(directory)),
                                                which=which, binaries=Path(directory),
                                                environment={})["ready"])

    def test_cli_show_and_list_are_read_only(self):
        for args in (("riceware", "packs", "list"), ("riceware", "packs", "show", "winxp"),
                     ("riceware", "packs", "template", "winxp")):
            with self.subTest(args=args), redirect_stdout(io.StringIO()) as output:
                self.assertEqual(cli.main(list(args)), 0)
                self.assertIn("schema_version", json.loads(output.getvalue()))

    def test_template_roundtrips_as_an_installed_pack(self):
        with tempfile.TemporaryDirectory() as directory:
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(cli.main(["riceware", "packs", "template", "winxp"]), 0)
            example = json.loads(output.getvalue())
            target = Path(directory) / (example["id"] + ".json")
            target.write_text(json.dumps(example), encoding="utf-8")
            self.assertEqual(packs.resolve(example["id"], Path(directory)).base_style, "winxp")

    def test_cli_requires_explicit_confirmation_and_reuses_transactional_apply(self):
        with self.assertRaises(ValueError):
            from macrice.riceware_cli import run
            run(cli.parser().parse_args(["riceware", "packs", "apply", "winxp"]))
        with mock.patch("macrice.rice.apply", return_value=Path("/tmp/safe-backup")) as apply, \
             mock.patch("macrice.shell_session.install_login_reconciler") as reconciler, \
             mock.patch("macrice.shell_session.sync_theme", return_value=()) as sync, \
             redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main(["riceware", "packs", "apply", "winxp", "--yes"]), 0)
            apply.assert_called_once_with("winxp")
            reconciler.assert_called_once_with()
            sync.assert_called_once_with(STYLES["winxp"].gtk)
            self.assertEqual(json.loads(output.getvalue())["applied"], "winxp")


if __name__ == "__main__":
    unittest.main()
