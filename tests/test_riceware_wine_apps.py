"""Wine app catalog safety tests, using only disposable fake prefixes."""

import fcntl
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from macrice import cli
from macrice.riceware import wine_apps


def ready_prefix(parent: Path, name: str = "games") -> Path:
    parent.mkdir(mode=0o700)
    prefix = parent / name
    prefix.mkdir(mode=0o700)
    (prefix / ".ricewine-ready").write_text("managed", encoding="utf-8")
    (prefix / "system.reg").write_text("registry", encoding="utf-8")
    return prefix


class WineCatalogTests(unittest.TestCase):
    def test_register_list_launch_unregister_without_touching_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "prefixes"
            prefix = ready_prefix(store)
            exe = prefix / "test.exe"
            exe.write_bytes(b"original")
            app = wine_apps.register("games", "test", "Test Program", str(exe),
                                     ("--windowed",), icon="application-x-executable",
                                     store=store)
            self.assertEqual(app.title, "Test Program")
            self.assertEqual(wine_apps.register("games", "test", "Test Program", str(exe),
                                                ("--windowed",), icon="application-x-executable",
                                                store=store), app)
            listed = wine_apps.list_apps(store=store)
            self.assertEqual(listed.applications, (app,))
            self.assertEqual(listed.issues, ())
            with patch.object(wine_apps.wine, "launch", return_value=789) as launch:
                self.assertEqual(wine_apps.launch_app("games", "test", store=store), 789)
                launch.assert_called_once_with("games", str(exe), ("--windowed",), store=store)
            with self.assertRaises(ValueError):
                wine_apps.register("games", "test", "Changed", str(exe), store=store)
            wine_apps.unregister("games", "test", store=store)
            self.assertEqual(wine_apps.list_apps(store=store).applications, ())
            self.assertEqual(exe.read_bytes(), b"original")

    def test_corrupt_catalog_is_not_overwritten_and_other_prefixes_still_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "prefixes"
            broken = ready_prefix(store)
            (store / "working").mkdir(mode=0o700)
            (store / "working" / ".ricewine-ready").write_text("managed")
            (store / "working" / "system.reg").write_text("registry")
            catalog = broken / wine_apps.CATALOG
            catalog.write_text("{invalid", encoding="utf-8")
            os.chmod(catalog, 0o600)
            with self.assertRaises(RuntimeError):
                wine_apps.register("games", "x", "X", "app.exe", store=store)
            self.assertEqual(catalog.read_text(), "{invalid")
            report = wine_apps.list_apps(store=store)
            self.assertEqual(len(report.issues), 1)
            self.assertEqual(report.applications, ())

    def test_symlinked_catalog_cannot_overwrite_user_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "prefixes"
            prefix = ready_prefix(store)
            victim = Path(tmp) / "private-note"
            victim.write_text("untouched")
            (prefix / wine_apps.CATALOG).symlink_to(victim)
            with self.assertRaises(RuntimeError):
                wine_apps.register("games", "x", "X", "app.exe", store=store)
            self.assertEqual(victim.read_text(), "untouched")

    def test_invalid_app_fields_and_concurrent_writer_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "prefixes"
            prefix = ready_prefix(store)
            with self.assertRaises(ValueError):
                wine_apps.register("games", "../escape", "X", "app.exe", store=store)
            with self.assertRaises(ValueError):
                wine_apps.register("games", "x", "Bad\nName", "app.exe", store=store)
            lock = prefix / wine_apps.LOCK
            with lock.open("wb+") as output:
                os.chmod(lock, 0o600)
                fcntl.flock(output, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaisesRegex(RuntimeError, "busy"):
                    wine_apps.register("games", "x", "X", "app.exe", store=store)

    def test_cli_exposes_apps_and_confirms_unregister(self):
        output = io.StringIO()
        with patch.object(wine_apps, "list_apps", return_value=wine_apps.CatalogSnapshot(())), \
             redirect_stdout(output):
            self.assertEqual(cli.main(["riceware", "wine", "apps"]), 0)
        self.assertEqual(json.loads(output.getvalue())["applications"], [])
        with patch.object(wine_apps, "unregister") as remove, \
             redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["riceware", "wine", "unregister", "games", "x"]), 1)
            remove.assert_not_called()
            self.assertEqual(cli.main([
                "riceware", "wine", "unregister", "games", "x", "--yes"]), 0)
            remove.assert_called_once_with("games", "x")


if __name__ == "__main__":
    unittest.main()
