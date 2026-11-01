import json
import stat
import tempfile
import unittest
from pathlib import Path

from macmenu import __version__
from macmenu.config import load, parse_backup, save, sanitize, save_backup, serialize_backup
from macmenu.commands import resolve_command
from macmenu.model import AppEntry, category_for, move_favorite, select_apps, visible_page


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.apps = [
            AppEntry("editor.desktop", "Code Editor", "Programmieren", "Development"),
            AppEntry("browser.desktop", "Web Browser", "Internet öffnen", "Internet"),
            AppEntry("calc.desktop", "Rechner", "Zahlen", "Utilities"),
        ]

    def test_search_is_global_and_ranks_name_prefixes(self):
        result = select_apps(self.apps, "web", "Development", [], [])
        self.assertEqual([app.app_id for app in result], ["browser.desktop"])

    def test_search_description_and_casefold(self):
        self.assertEqual(select_apps(self.apps, "PROGRAMMIEREN", "All Apps", [], [])[0].app_id, "editor.desktop")

    def test_favorites_and_recent_order(self):
        favorites = select_apps(self.apps, "", "Favorites", ["calc.desktop", "browser.desktop"], [])
        recent = select_apps(self.apps, "", "Recent", [], ["browser.desktop", "calc.desktop"])
        self.assertEqual([x.app_id for x in favorites], ["calc.desktop", "browser.desktop"])
        self.assertEqual([x.app_id for x in recent], ["browser.desktop", "calc.desktop"])

    def test_categories(self):
        self.assertEqual(category_for("AudioVideo;Player;"), "Media")
        self.assertEqual(category_for("X-Unknown;"), "Other")

    def test_search_includes_keywords(self):
        apps = [AppEntry("mail.desktop", "Post", "Briefe", "Internet", keywords="email smtp")]
        self.assertEqual(select_apps(apps, "SMTP", "All Apps", [], [])[0].app_id, "mail.desktop")

    def test_favorites_move_without_losing_entries(self):
        favorites = ["a", "b", "c"]
        self.assertEqual(move_favorite(favorites, "c", -1), ["a", "c", "b"])
        self.assertEqual(move_favorite(favorites, "a", -1), favorites)
        self.assertEqual(move_favorite(favorites, "missing", 1), favorites)

    def test_multiword_search_and_umlauts(self):
        apps = [
            AppEntry("a", "Büro Editor", "Texte ändern", "Office"),
            AppEntry("b", "Büro Kalender", "Termine", "Office"),
        ]
        self.assertEqual([a.app_id for a in select_apps(apps, "buro text", "All Apps", [], [])], ["a"])
        self.assertEqual([a.app_id for a in select_apps(apps, "kal büro", "All Apps", [], [])], ["b"])

    def test_search_favorite_ranking_without_changing_exact_matches(self):
        apps = [AppEntry("a", "Video Editor", "", "Media"),
                AppEntry("b", "Video Maker", "", "Media")]
        self.assertEqual(
            [a.app_id for a in select_apps(apps, "video", "All Apps", ["b"], [])],
            ["b", "a"],
        )

    def test_visible_page_bounds(self):
        self.assertEqual(visible_page(self.apps, 2), (self.apps[:2], 1))
        self.assertEqual(visible_page(self.apps, 10), (self.apps, 0))
        self.assertEqual(visible_page(self.apps, -1), ([], 3))


class SettingsTests(unittest.TestCase):
    def test_preferences_and_file_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "macmenu" / "settings.json"
            settings = load(path)
            self.assertNotIn("view", settings)
            settings["theme"] = "light"
            settings["favorites"] = ["editor.desktop"]
            save(settings, path)
            restored = load(path)
            self.assertEqual(restored["theme"], "light")
            self.assertEqual(restored["favorites"], ["editor.desktop"])
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_malformed_settings_are_sanitized(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(json.dumps({"view": "invalid", "favorites": ["a", 1, "a"]}), encoding="utf-8")
            data = load(path)
            self.assertNotIn("view", data)
            self.assertEqual(data["favorites"], ["a"])

    def test_additional_preferences_are_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(json.dumps({
                "theme": "system", "position": "panel", "icon_size": "large",
                "show_descriptions": False,
            }), encoding="utf-8")
            data = load(path)
            self.assertEqual(data["theme"], "system")
            self.assertEqual(data["position"], "panel")
            self.assertEqual(data["icon_size"], "large")
            self.assertNotIn("show_descriptions", data)

    def test_extended_apple_style_themes_roundtrip(self):
        for theme in ("dark", "light", "graphite", "ocean", "violet", "system"):
            with self.subTest(theme=theme):
                self.assertEqual(sanitize({"theme": theme})["theme"], theme)
                self.assertEqual(parse_backup(serialize_backup({"theme": theme}))["theme"], theme)
        self.assertEqual(sanitize({"theme": "arbitrary-css"})["theme"], "dark")

    def test_instant_toggle_defaults_and_legacy_upgrade(self):
        default = sanitize({})
        self.assertTrue(default["instant_toggle"])
        self.assertTrue(sanitize({"instant_toggle": "yes"})["instant_toggle"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prefs.json"
            configured = sanitize({"instant_toggle": False, "view": "classic", "keep_running": False})
            save(configured, path)
            self.assertFalse(load(path)["instant_toggle"])
            self.assertFalse(parse_backup(serialize_backup(configured))["instant_toggle"])
            self.assertNotIn("view", load(path))
            path.write_text(json.dumps({"view": "classic", "keep_running": False, "theme": "ocean", "favorites": ["a.desktop"]}))
            upgraded = load(path)
            self.assertTrue(upgraded["instant_toggle"])
            self.assertEqual(upgraded["favorites"], ["a.desktop"])
            self.assertEqual(upgraded["theme"], "ocean")

    def test_history_opt_out_clears_persisted_recent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            settings = load(path)
            settings["recent"] = ["one.desktop"]
            settings["history_enabled"] = False
            save(settings, path)
            restored = load(path)
            self.assertFalse(restored["history_enabled"])
            self.assertEqual(restored["recent"], [])
            self.assertEqual(json.loads(path.read_text())["recent"], [])

    def test_backup_roundtrip_and_strict_invalid_input(self):
        original = sanitize({"view": "classic", "favorites": ["test.desktop"], "theme": "system"})
        self.assertEqual(parse_backup(serialize_backup(original)), original)
        for invalid in ("", "{}", "[]", "{malformed", '{"backup_format":"other","view":"classic"}'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                parse_backup(invalid)

    def test_backup_is_private_and_recovers_saved_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "macmenu-backup.json"
            save_backup({"view": "classic", "favorites": ["editor.desktop"]}, target)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            self.assertEqual(parse_backup(target.read_text())["favorites"], ["editor.desktop"])
            self.assertEqual(json.loads(target.read_text())["backup_format"], "macmenu-settings-v1")

    def test_config_defaults_do_not_share_mutable_lists(self):
        one, two = sanitize({}), sanitize({})
        one["favorites"].append("one.desktop")
        self.assertEqual(two["favorites"], [])

    def test_invalid_app_ids_from_backup_are_removed(self):
        settings = sanitize({"favorites": ["good.desktop", "bad\nname", "\ud800", "", 42]})
        self.assertEqual(settings["favorites"], ["good.desktop"])
        self.assertEqual(parse_backup(serialize_backup(settings))["favorites"], ["good.desktop"])


class CommandTests(unittest.TestCase):
    def test_command_line_contract(self):
        self.assertEqual(resolve_command([]), "toggle")
        for option, action in (("--show", "show"), ("--hide", "hide"),
                               ("--quit", "quit"), ("--preferences", "preferences"),
                               ("--version", "version")):
            self.assertEqual(resolve_command([option]), action)
        for invalid in (["--unknown"], ["--show", "--hide"], ["--show=1"]):
            with self.assertRaises(ValueError):
                resolve_command(invalid)

    def test_source_version_matches_package_metadata(self):
        project = Path(__file__).resolve().parents[1]
        self.assertIn(f'version = "{__version__}"', (project / "pyproject.toml").read_text())


if __name__ == "__main__":
    unittest.main()
