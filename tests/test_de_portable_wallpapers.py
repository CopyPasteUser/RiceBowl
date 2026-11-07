"""Schema-v6 image assets: reproducible portable archives, private runtime data."""

import contextlib
import io
import json
import os
import stat
import struct
import tempfile
import unittest
import zlib
import zipfile
from pathlib import Path
from unittest import mock

from macrice.cli import main
from macrice.de import assets, pack, recipes


def png() -> bytes:
    def chunk(name: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + name + data
                + struct.pack(">I", zlib.crc32(name + data)))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00\xff"))
            + chunk(b"IEND", b""))


class PortableWallpaperTests(unittest.TestCase):
    def test_png_validation_limits_and_owner_file_permissions(self):
        image = png()
        wallpaper_id = assets.image_id(image)
        self.assertTrue(assets.ASSET_ID.fullmatch(wallpaper_id))
        invalid = bytearray(image)
        invalid[-8] ^= 1
        with self.assertRaises(assets.AssetError):
            assets.validate_png(bytes(invalid))
        with self.assertRaises(assets.AssetError):
            assets.validate_png(image * (assets.MAX_IMAGE_BYTES // len(image) + 1))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "original.png"
            source.write_bytes(image)
            link = root / "symlink.png"
            link.symlink_to(source)
            with self.assertRaises(assets.AssetError):
                assets.import_png(link)
            config = root / "config"
            config.mkdir(mode=0o700)
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(config)}):
                saved_id, saved_path = assets.import_png(source)
                self.assertEqual(saved_id, wallpaper_id)
                self.assertEqual(saved_path.stat().st_mode & 0o777, 0o600)
                self.assertEqual(assets.read(saved_id)[1], image)
                saved_path.write_bytes(image + b"garbage")
                with self.assertRaises(assets.AssetError):
                    assets.read(saved_id)

    def test_schema_v6_pack_roundtrip_deterministic_and_no_session_apply(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_png = root / "photo.png"
            source_png.write_bytes(png())
            source_config = root / "source-config"
            source_config.mkdir(mode=0o700)
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(source_config)}):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(main(["de", "asset-import", "--asset", str(source_png),
                                           "--json"]), 0)
                wallpaper_id = json.loads(output.getvalue())["asset_id"]
                draft = root / "draft.json"
                recipes.create_from_template(source="classic", destination=draft,
                                             recipe_id="portable-picture", name="Portable PNG",
                                             schema_version=6)
                data = json.loads(draft.read_text())
                data["desktop"]["wallpaper"] = wallpaper_id
                draft.write_text(json.dumps(data))
                self.assertEqual(recipes.parse(draft.read_bytes()).wallpaper, wallpaper_id)
                first, second = root / "first.ricepack", root / "second.ricepack"
                exported = pack.export_pack(str(draft), first)
                pack.export_pack(str(draft), second)
                self.assertEqual(first.read_bytes(), second.read_bytes())
                self.assertEqual(exported["pack_version"], 3)
                with zipfile.ZipFile(first) as archive:
                    self.assertEqual(archive.namelist(), ["ricepack.json", "recipe.json",
                                                             "assets/wallpaper.png"])
                    self.assertEqual(archive.read("assets/wallpaper.png"), png())
            target_config = root / "target-config"
            target_config.mkdir(mode=0o700)
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(target_config)}):
                self.assertEqual(pack.inspect_pack(first)["pack_version"], 3)
                self.assertFalse((target_config / "ricebowl").exists())
                imported = pack.import_pack(first)
                self.assertTrue(imported["imported"])
                self.assertFalse(imported["applied"])
                installed = recipes.load("portable-picture")
                self.assertEqual(recipes.wallpaper_path(installed).read_bytes(), png())
                self.assertEqual(recipes.current_selection(), ("classic", None))
                restored = root / "restored.ricepack"
                pack.export_pack("portable-picture", restored)
                self.assertEqual(first.read_bytes(), restored.read_bytes())

    def test_tamper_paths_and_old_schema_reject_asset_injection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            png_path = root / "photo.png"
            png_path.write_bytes(png())
            config = root / "config"
            config.mkdir(mode=0o700)
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(config)}):
                wallpaper_id, _ = assets.import_png(png_path)
                recipe_path = root / "v6.json"
                recipes.create_from_template(source="classic", destination=recipe_path,
                                             recipe_id="secured-rice", name="Secure",
                                             schema_version=6)
                draft = json.loads(recipe_path.read_text())
                draft["desktop"]["wallpaper"] = wallpaper_id
                recipe_path.write_text(json.dumps(draft))
                good = root / "good.ricepack"
                pack.export_pack(str(recipe_path), good)
                with zipfile.ZipFile(good) as archive:
                    manifest = archive.read("ricepack.json")
                    recipe_data = archive.read("recipe.json")
                with zipfile.ZipFile(root / "tampered.ricepack", "w") as archive:
                    archive.writestr("ricepack.json", manifest)
                    archive.writestr("recipe.json", recipe_data)
                    archive.writestr("assets/wallpaper.png", png() + b"garbage")
                with self.assertRaises(pack.PackError):
                    pack.import_pack(root / "tampered.ricepack")
                self.assertFalse((config / "ricebowl/recipes/secured-rice.json").exists())
                draft["schema_version"] = 5
                with self.assertRaises(recipes.RecipeError):
                    recipes.parse(json.dumps(draft).encode())
                draft["schema_version"] = 6
                draft["desktop"]["wallpaper"] = "../../wallpaper.png"
                with self.assertRaises(recipes.RecipeError):
                    recipes.parse(json.dumps(draft).encode())
