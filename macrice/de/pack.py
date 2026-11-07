"""Portable, non-executable RicePacks for the experimental Wayland shell.

Only validated recipe data and declared provenance are included. A RicePack
does not contain scripts, untrusted assets or an active-session instruction.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import stat
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from . import recipes, review


PACK_VERSION = 2
PACK_FORMAT = "org.ricebowl.ricepack"
MAX_PACK_BYTES = 256 * 1024
MAX_METADATA_BYTES = 4096
MAX_MANIFEST_BYTES = 8192
_ZIP_DATE = (1980, 1, 1, 0, 0, 0)
_ID = re.compile(r"[a-z][a-z0-9-]{1,31}\Z")
_LICENSES = frozenset(("unspecified", "CC0-1.0", "CC-BY-4.0", "MIT", "custom"))
_ORIGINS = frozenset(("unspecified", "original", "ai-assisted", "adapted"))
_DEFAULT_PROVENANCE = {
    "author": "", "license": "unspecified", "origin": "unspecified", "source_reference": "",
}


def _bundled_wallpaper(recipe: recipes.PanelRecipe) -> tuple[str, str]:
    """Pin the original installed wallpaper bytes without bundling executables."""
    asset_id = recipe.wallpaper or "aero-seven-blue"
    path = recipes.wallpaper_path(recipe)
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > 8 * 1024 * 1024:
                raise PackError("Bundled wallpaper is unavailable or unsafe",
                                code="asset_unavailable")
            data = stream.read(8 * 1024 * 1024 + 1)
            if len(data) > 8 * 1024 * 1024:
                raise PackError("Bundled wallpaper is oversized", code="asset_unavailable")
    except OSError as exc:
        raise PackError("Bundled wallpaper is unavailable", code="asset_unavailable") from exc
    return asset_id, _digest(data)


def _asset_receipt(recipe: recipes.PanelRecipe, provenance: dict[str, str]) -> dict[str, Any]:
    asset_id, sha = _bundled_wallpaper(recipe)
    return {"version": 1, "wallpaper": {"id": asset_id, "sha256": sha,
                                        "provenance": provenance}}


class PackError(ValueError):
    """Invalid or unsafe portable package; no active desktop was changed."""

    def __init__(self, message: str, *, code: str = "invalid_pack") -> None:
        super().__init__(message)
        self.code = code


def _json_bytes(data: dict[str, Any]) -> bytes:
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_object(payload: bytes) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("utf-8"),
                           object_pairs_hook=recipes._object_without_duplicates)
    except (ValueError, UnicodeError, RecursionError, TypeError) as exc:
        raise PackError("Malformed or duplicate-key RicePack JSON") from exc
    if type(value) is not dict:
        raise PackError("RicePack JSON must be an object")
    return value


def _provenance(value: dict[str, Any]) -> dict[str, str]:
    if set(value) != set(_DEFAULT_PROVENANCE):
        raise PackError("Unsupported RicePack provenance fields")
    if (type(value["author"]) is not str or len(value["author"]) > 80
            or type(value["source_reference"]) is not str
            or len(value["source_reference"]) > 256
            or type(value["license"]) is not str or value["license"] not in _LICENSES
            or type(value["origin"]) is not str or value["origin"] not in _ORIGINS):
        raise PackError("Invalid RicePack provenance")
    for field in ("author", "source_reference"):
        if any(ord(char) < 32 or ord(char) == 127 for char in value[field]):
            raise PackError("RicePack provenance contains control characters")
    return value


def _read_owned_file(path: Path, *, suffix: str, limit: int) -> bytes:
    if not path.is_absolute() or path.suffix != suffix:
        raise PackError(f"Input must be an absolute {suffix} file", code="invalid_input")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        with os.fdopen(fd, "rb") as stream:
            meta = os.fstat(stream.fileno())
            if (not stat.S_ISREG(meta.st_mode) or meta.st_uid != os.geteuid()
                    or meta.st_mode & 0o022 or meta.st_size > limit):
                raise PackError("Input is unsafe, unowned or too large", code="invalid_input")
            payload = stream.read(limit + 1)
            if len(payload) > limit:
                raise PackError("Input exceeds its size limit", code="invalid_input")
            return payload
    except OSError as exc:
        raise PackError("Input is unavailable or unsafe", code="invalid_input") from exc


def _read_recipe(token: str) -> recipes.PanelRecipe:
    try:
        if token in recipes.BUILTINS:
            return recipes.load(token)
        if _ID.fullmatch(token):
            return recipes.load(token)
        return recipes.parse(recipes._read_import_source(Path(token)))
    except (recipes.RecipeError, OSError) as exc:
        raise PackError("Invalid or unsafe source recipe", code="invalid_recipe") from exc


def _new_archive(destination: Path, payload: bytes) -> None:
    if not destination.is_absolute() or destination.suffix != ".ricepack":
        raise PackError("Output must be an absolute .ricepack file", code="invalid_output")
    if len(payload) > MAX_PACK_BYTES:
        raise PackError("RicePack exceeds size limit", code="invalid_output")
    temporary: str | None = None
    try:
        descriptor, temporary = tempfile.mkstemp(prefix=".ricebowl-pack-",
                                                dir=destination.parent)
        with os.fdopen(descriptor, "wb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, destination)  # Atomic no-overwrite, including symlinks.
    except OSError as exc:
        raise PackError("Cannot publish RicePack without overwriting a file",
                        code="output_unavailable") from exc
    finally:
        if temporary is not None:
            os.unlink(temporary)


def export_pack(recipe_token: str, destination: Path,
                *, metadata: Path | None = None) -> dict[str, Any]:
    """Build reproducible bytes for a validated recipe; do not select/apply it."""
    if not destination.is_absolute() or destination.suffix != ".ricepack":
        raise PackError("Output must be an absolute .ricepack file", code="invalid_output")
    recipe = _read_recipe(recipe_token)
    provenance = dict(_DEFAULT_PROVENANCE)
    wallpaper_provenance = dict(_DEFAULT_PROVENANCE)
    if metadata is not None:
        declared = _parse_object(_read_owned_file(
            metadata, suffix=".json", limit=MAX_METADATA_BYTES))
        if "wallpaper_provenance" in declared:
            wallpaper = declared.pop("wallpaper_provenance")
            wallpaper_provenance = _provenance(wallpaper if type(wallpaper) is dict else {})
        provenance = _provenance(declared)
    canonical = review._manifest(recipe)
    recipe_payload = _json_bytes(canonical)
    # The canonical form must itself be the exact runtime schema, not a
    # Creator-only representation or an accidentally lossy normalization.
    try:
        if review._manifest(recipes.parse(recipe_payload)) != canonical:
            raise PackError("Recipe cannot be serialized losslessly", code="invalid_recipe")
    except recipes.RecipeError as exc:
        raise PackError("Canonical recipe is invalid", code="invalid_recipe") from exc
    manifest = {
        "format": PACK_FORMAT,
        "format_version": PACK_VERSION,
        "recipe": {"path": "recipe.json", "id": recipe.recipe_id,
                   "schema_version": recipe.schema_version,
                   "sha256": _digest(recipe_payload),
                   "semantic_sha256": review._semantic_hash(canonical)},
        "provenance": provenance,
        "runtime_assets": "bundled-wallpapers-only",
        "asset_manifest": _asset_receipt(recipe, wallpaper_provenance),
    }
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, "w", compression=zipfile.ZIP_STORED,
                         allowZip64=False) as archive:
        for name, data in (("ricepack.json", _json_bytes(manifest)),
                           ("recipe.json", recipe_payload)):
            info = zipfile.ZipInfo(name, date_time=_ZIP_DATE)
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, data)
    _new_archive(destination, memory.getvalue())
    return {"pack_version": PACK_VERSION, "ok": True, "created": True,
            "imported": False, "applied": False, "recipe_id": recipe.recipe_id,
            "package_sha256": _digest(memory.getvalue()), "manifest": manifest}


def _validate_archive(source: Path) -> tuple[dict[str, Any], bytes]:
    payload = _read_owned_file(source, suffix=".ricepack", limit=MAX_PACK_BYTES)
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            entries = archive.infolist()
            if (len(entries) != 2 or {entry.filename for entry in entries}
                    != {"ricepack.json", "recipe.json"}):
                raise PackError("RicePack must contain exactly two known data files")
            for entry in entries:
                mode = entry.external_attr >> 16
                if (entry.flag_bits & 1 or entry.compress_type != zipfile.ZIP_STORED
                        or stat.S_IFMT(mode) not in (0, stat.S_IFREG)
                        or entry.file_size > (MAX_MANIFEST_BYTES if entry.filename == "ricepack.json"
                                              else recipes.MAX_RECIPE_BYTES)):
                    raise PackError("Unsafe, compressed or oversized RicePack entry")
            metadata = _parse_object(archive.read("ricepack.json"))
            recipe_payload = archive.read("recipe.json")
    except (zipfile.BadZipFile, OSError, RuntimeError, EOFError, ValueError) as exc:
        if isinstance(exc, PackError):
            raise
        raise PackError("Corrupt or invalid RicePack archive") from exc
    version = metadata.get("format_version")
    expected = {"format", "format_version", "recipe", "provenance", "runtime_assets"}
    if version == 2:
        expected.add("asset_manifest")
    if (set(metadata) != expected
            or metadata["format"] != PACK_FORMAT
            or type(version) is not int
            or version not in (1, PACK_VERSION)
            or metadata["runtime_assets"] != "bundled-wallpapers-only"):
        raise PackError("Unsupported RicePack format or version")
    info = metadata["recipe"]
    if (type(info) is not dict
            or set(info) != {"path", "id", "schema_version", "sha256", "semantic_sha256"}
            or info["path"] != "recipe.json"
            or type(info["id"]) is not str or not _ID.fullmatch(info["id"])
            or type(info["schema_version"]) is not int
            or type(info["sha256"]) is not str
            or type(info["semantic_sha256"]) is not str):
        raise PackError("Invalid RicePack recipe manifest")
    _provenance(metadata["provenance"] if type(metadata["provenance"]) is dict else {})
    try:
        recipe = recipes.parse(recipe_payload)
    except recipes.RecipeError as exc:
        raise PackError("RicePack includes an invalid recipe") from exc
    if (recipe.recipe_id != info["id"] or recipe.schema_version != info["schema_version"]
            or _digest(recipe_payload) != info["sha256"]
            or review._semantic_hash(review._manifest(recipe)) != info["semantic_sha256"]):
        raise PackError("RicePack recipe fingerprint or identity mismatch")
    if version == 2:
        assets = metadata["asset_manifest"]
        if (type(assets) is not dict or set(assets) != {"version", "wallpaper"}
                or type(assets["version"]) is not int or assets["version"] != 1):
            raise PackError("Invalid RicePack asset manifest")
        wallpaper = assets["wallpaper"]
        if (type(wallpaper) is not dict
                or set(wallpaper) != {"id", "sha256", "provenance"}
                or type(wallpaper["id"]) is not str
                or type(wallpaper["sha256"]) is not str):
            raise PackError("Invalid bundled wallpaper receipt")
        _provenance(wallpaper["provenance"] if type(wallpaper["provenance"]) is dict else {})
        if (wallpaper["id"], wallpaper["sha256"]) != _bundled_wallpaper(recipe):
            raise PackError("Bundled wallpaper identity or checksum does not match",
                            code="asset_mismatch")
    return metadata, recipe_payload


def inspect_pack(source: Path) -> dict[str, Any]:
    """Verify all archive entries, fingerprints and the real recipe schema."""
    metadata, _ = _validate_archive(source)
    return {"pack_version": metadata["format_version"], "ok": True, "valid": True,
            "imported": False, "applied": False, "manifest": metadata}


def import_pack(source: Path) -> dict[str, Any]:
    """Install only the validated recipe, explicitly never its provenance as code."""
    metadata, payload = _validate_archive(source)
    if metadata["recipe"]["id"] in recipes.BUILTINS:
        raise PackError("Cannot replace a reserved built-in recipe", code="reserved_id")
    try:
        destination = (recipes._private_recipe_dir(create=True)
                       / f"{metadata['recipe']['id']}.json")
        recipes._write_private_new(destination, payload)
    except (OSError, recipes.RecipeError) as exc:
        raise PackError("Cannot install recipe without overwriting an existing file",
                        code="import_unavailable") from exc
    return {"pack_version": metadata["format_version"], "ok": True, "valid": True,
            "imported": True, "applied": False,
            "recipe_id": metadata["recipe"]["id"],
            "semantic_sha256": metadata["recipe"]["semantic_sha256"]}


def invalid_pack(error: PackError) -> dict[str, Any]:
    """Stable path-free errors for agents; no privacy-sensitive file paths."""
    return {"pack_version": PACK_VERSION, "ok": False, "imported": False,
            "applied": False, "error": {"code": error.code, "message": str(error)}}
