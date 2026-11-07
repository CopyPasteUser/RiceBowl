"""Content-addressed, non-executable user wallpapers for schema-v6 recipes.

Only inspected PNG bytes are accepted. Recipe files contain a SHA-256 asset
identifier, never a filesystem path, script, URI or remote resource.
"""

from __future__ import annotations

import hashlib
import os
import re
import stat
import struct
import zlib
from pathlib import Path


MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_DIMENSION = 4096
ASSET_ID = re.compile(r"asset-[0-9a-f]{64}\Z")
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_PNG_TYPES = {b"IHDR", b"IDAT", b"IEND", b"PLTE"}


class AssetError(ValueError):
    """An image, path, or owner-private asset collection failed validation."""


def validate_png(data: bytes) -> None:
    """Bound image dimensions, size, PNG structure and every chunk checksum."""
    if not _PNG_SIGNATURE == data[:8] or len(data) > MAX_IMAGE_BYTES:
        raise AssetError("Wallpaper must be a bounded PNG image")
    index = 8
    chunks = 0
    saw_header = saw_pixels = saw_end = False
    pixel_chunks: list[bytes] = []
    pixels_finished = False
    row_bytes = height = 0
    while index + 12 <= len(data) and chunks < 256:
        length = struct.unpack_from(">I", data, index)[0]
        name = data[index + 4:index + 8]
        finish = index + 12 + length
        if (length > MAX_IMAGE_BYTES or finish > len(data)
                or not all(65 <= byte <= 90 or 97 <= byte <= 122 for byte in name)):
            raise AssetError("Invalid PNG chunk length or type")
        content = data[index + 8:index + 8 + length]
        checksum = struct.unpack_from(">I", data, index + 8 + length)[0]
        if zlib.crc32(name + content) != checksum:
            raise AssetError("PNG chunk checksum mismatch")
        if name == b"IHDR":
            if saw_header or chunks != 0 or length != 13:
                raise AssetError("Invalid PNG image header")
            width, height, depth, color, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", content)
            if not (1 <= width <= MAX_DIMENSION and 1 <= height <= MAX_DIMENSION
                    and width * height <= 4096 * 2160 and depth == 8
                    and color in (2, 6) and (compression, filtering, interlace) == (0, 0, 0)):
                raise AssetError("Unsupported PNG format or dimensions")
            row_bytes = 1 + width * (3 if color == 2 else 4)
            saw_header = True
        elif name == b"IDAT":
            if not saw_header or saw_end or pixels_finished or length == 0:
                raise AssetError("Invalid PNG pixel data")
            saw_pixels = True
            pixel_chunks.append(content)
        elif name == b"IEND":
            if not saw_header or not saw_pixels or saw_end or length != 0 or finish != len(data):
                raise AssetError("Invalid PNG image terminator")
            saw_end = True
            break
        elif name not in _PNG_TYPES and name[:1].isupper():
            raise AssetError("Unsupported PNG critical chunk")
        if name != b"IDAT" and saw_pixels:
            pixels_finished = True
        index = finish
        chunks += 1
    if not saw_end:
        raise AssetError("Truncated or excessively complex PNG image")
    # Validate the bounded raster, not just the PNG wrapper. This also rejects
    # corrupt deflate payloads and decompression bombs hidden in tiny files.
    expected = row_bytes * height
    try:
        decoder = zlib.decompressobj()
        raw = decoder.decompress(b"".join(pixel_chunks), expected + 1)
    except zlib.error as exc:
        raise AssetError("Invalid PNG compressed pixels") from exc
    if (not decoder.eof or decoder.unused_data or decoder.unconsumed_tail
            or len(raw) != expected
            or any(raw[row * row_bytes] > 4 for row in range(height))):
        raise AssetError("PNG raster data is invalid or oversized")


def image_id(data: bytes) -> str:
    validate_png(data)
    return "asset-" + hashlib.sha256(data).hexdigest()


def _collection(*, create: bool) -> Path:
    configured = os.environ.get("XDG_CONFIG_HOME")
    root = Path(configured) if configured else Path.home() / ".config"
    if not root.is_absolute():
        raise AssetError("XDG_CONFIG_HOME must be absolute")
    directory = root / "ricebowl" / "wallpapers"
    for folder in (root, root / "ricebowl", directory):
        if create and not os.path.lexists(folder):
            folder.mkdir(mode=0o700)
        try:
            info = folder.lstat()
        except FileNotFoundError:
            if not create:
                return directory
            raise AssetError("Wallpaper collection cannot be created") from None
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
                or info.st_mode & 0o022
                or (folder == directory and info.st_mode & 0o077)):
            raise AssetError("Unsafe wallpaper configuration directory")
    return directory


def _read_owned_png(source: Path, *, owner_private: bool = False) -> bytes:
    if not source.is_absolute() or source.suffix != ".png":
        raise AssetError("Wallpaper source must be an absolute .png path")
    try:
        descriptor = os.open(source, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                    or info.st_mode & 0o022 or info.st_size > MAX_IMAGE_BYTES
                    or (owner_private and info.st_mode & 0o077)):
                raise AssetError("Wallpaper must be an owner-controlled regular file")
            data = stream.read(MAX_IMAGE_BYTES + 1)
    except OSError as exc:
        raise AssetError("Wallpaper could not be read safely") from exc
    validate_png(data)
    return data


def read(asset_id: str) -> tuple[Path, bytes]:
    if not ASSET_ID.fullmatch(asset_id):
        raise AssetError("Invalid content-addressed wallpaper ID")
    location = _collection(create=False) / (asset_id + ".png")
    data = _read_owned_png(location, owner_private=True)
    if image_id(data) != asset_id:
        raise AssetError("Private wallpaper content does not match its SHA-256 ID")
    return location, data


def store(data: bytes) -> tuple[str, Path]:
    asset_id = image_id(data)
    directory = _collection(create=True)
    location = directory / (asset_id + ".png")
    if os.path.lexists(location):
        _, original = read(asset_id)
        if original != data:
            raise AssetError("Existing wallpaper asset does not match")
        return asset_id, location
    # New private immutable content, no overwrites, including symlinks.
    from .recipes import _write_private_new
    try:
        _write_private_new(location, data, suffix=".png")
    except (OSError, ValueError) as exc:
        raise AssetError("Cannot install the wallpaper without overwriting data") from exc
    return asset_id, location


def import_png(source: Path) -> tuple[str, Path]:
    """Explicit local import; never select a rice or replace live wallpaper."""
    return store(_read_owned_png(source))
