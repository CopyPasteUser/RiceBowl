"""Conservative, user-scoped Rice pack ZIP v2 import and removal.

No archive path can escape the private pack directory. Only declared image,
GTK CSS, XFWM and icon-theme files are accepted; scripts, links, SVG and CSS
resource imports are intentionally unsupported. Import never activates a rice.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import zipfile
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
from itertools import islice
from pathlib import Path, PurePosixPath

from ..environment import data_home
from .packs import RicePack, _IDENTIFIER, _name

VERSION = 2
MAX_ARCHIVE = 32 * 1024 * 1024
MAX_UNPACKED = 48 * 1024 * 1024
MAX_ENTRY = 12 * 1024 * 1024
MAX_FILES = 128
MAX_MANIFEST = 64 * 1024
HASH = re.compile(r"[a-f0-9]{64}\Z")
ASSET_KEYS = frozenset(("wallpaper", "gtk", "xfwm", "icons"))
TEXT_EXT = frozenset((".css", ".theme", ".themerc"))
IMAGE_EXT = frozenset((".png", ".jpg", ".jpeg"))
RECORD_FIELDS = frozenset(("schema_version", "id", "name", "base_style",
                           "description", "revision", "license", "assets", "files"))
LICENSE_FIELDS = frozenset(("spdx", "author", "source"))
SPDX = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+-]{1,63}\Z")


class PackImportError(ValueError):
    """A pack or installation location failed a non-destructive safety check."""


def _safe_path(name: str) -> bool:
    if (not isinstance(name, str) or not 1 <= len(name) <= 170
            or "\\" in name or any(ord(c) < 32 or ord(c) == 127 for c in name)):
        return False
    parts = PurePosixPath(name).parts
    return (len(parts) <= 7 and all(p not in ("", ".", "..") for p in parts)
            and not name.startswith("/") and not name.endswith("/")
            and "/./" not in name and "//" not in name)


def _valid_file(name: str) -> bool:
    if not _safe_path(name):
        return False
    parts = PurePosixPath(name).parts
    if parts[0] == "wallpaper":
        return len(parts) == 2 and PurePosixPath(name).suffix.lower() in IMAGE_EXT
    if parts[0] == "gtk":
        return len(parts) >= 3 and parts[1] == "gtk-3.0" and (
            PurePosixPath(name).suffix.lower() in IMAGE_EXT | frozenset((".css",)))
    if parts[0] == "xfwm":
        return len(parts) >= 3 and parts[1] == "xfwm4" and (
            PurePosixPath(name).suffix.lower() in IMAGE_EXT or parts[-1] == "themerc")
    if parts[0] == "icons":
        return (name == "icons/index.theme" or
                (len(parts) >= 3 and PurePosixPath(name).suffix.lower() in IMAGE_EXT))
    return False


def _validate(values: object, *, installed: bool) -> dict:
    from .profiles import PROFILE_FAMILIES

    fields = RECORD_FIELDS if installed else RECORD_FIELDS - {"revision"}
    if (not isinstance(values, dict) or set(values) != fields
            or type(values.get("schema_version")) is not int or values["schema_version"] != VERSION):
        raise PackImportError("unsupported visual pack schema")
    if not isinstance(values["id"], str) or not _IDENTIFIER.fullmatch(values["id"]):
        raise PackImportError("invalid pack ID")
    if values["id"] in PROFILE_FAMILIES:
        raise PackImportError("pack ID conflicts with a built-in rice")
    if not _name(values["name"], 80) or not isinstance(values["description"], str) or (
            values["description"] and not _name(values["description"], 240)):
        raise PackImportError("invalid pack name or description")
    if not isinstance(values["base_style"], str) or values["base_style"] not in PROFILE_FAMILIES:
        raise PackImportError("unknown base style")
    lic = values["license"]
    if (not isinstance(lic, dict) or set(lic) != LICENSE_FIELDS
            or not isinstance(lic["spdx"], str) or not SPDX.fullmatch(lic["spdx"])
            or not _name(lic["author"], 120) or not _name(lic["source"], 240)):
        raise PackImportError("license must declare SPDX identifier, author and origin")
    assets = values["assets"]
    if (not isinstance(assets, dict) or not assets or not set(assets) <= ASSET_KEYS
            or any(key != "wallpaper" and value is not True for key, value in assets.items())):
        raise PackImportError("invalid asset declarations")
    files = values["files"]
    if (not isinstance(files, dict) or not 1 <= len(files) <= MAX_FILES
            or any(not _valid_file(path) or not isinstance(digest, str) or not HASH.fullmatch(digest)
                   for path, digest in files.items())):
        raise PackImportError("invalid file inventory or digests")
    if "wallpaper" in assets and (not isinstance(assets["wallpaper"], str)
                                  or assets["wallpaper"] not in files
                                  or not assets["wallpaper"].startswith("wallpaper/")):
        raise PackImportError("wallpaper must reference an inventoried image")
    if (any(path.split("/", 1)[0] not in assets for path in files)
            or any(not any(path.startswith(key + "/") for path in files) for key in assets)):
        raise PackImportError("asset inventory and declarations disagree")
    for name, required in (("gtk", "gtk/gtk-3.0/gtk.css"),
                           ("xfwm", "xfwm/xfwm4/themerc"),
                           ("icons", "icons/index.theme")):
        if name in assets and required not in files:
            raise PackImportError(f"{name} requires {required}")
    if installed and (not isinstance(values["revision"], str)
                      or not HASH.fullmatch(values["revision"])):
        raise PackImportError("invalid installed revision")
    return values


def pack_from_record(values: object, filename_id: str) -> RicePack:
    record = _validate(values, installed=True)
    if record["id"] != filename_id:
        raise PackImportError("installed pack ID and filename disagree")
    return RicePack(record["id"], record["name"], record["base_style"],
                    record["description"], "installed", record["revision"],
                    tuple(sorted(record["assets"])))


def _root(data_root: Path | None = None) -> Path:
    return (data_root if data_root is not None else data_home()) / "ricebowl"


def _pack_name(pack: RicePack) -> str:
    return f"RiceBowl-{pack.id}-{pack.revision[:12]}"


def theme_name(pack: RicePack) -> str:
    return _pack_name(pack)


def _record_path(pack_id: str, data_root: Path | None = None) -> Path:
    return _root(data_root) / "packs" / f"{pack_id}.json"


def _assets_path(pack: RicePack, data_root: Path | None = None) -> Path:
    return _root(data_root) / "assets" / f"{pack.id}-{pack.revision[:12]}"


def _file_at(root: Path, name: str) -> Path:
    parts = PurePosixPath(name).parts
    if parts[0] in ("gtk", "xfwm"):
        return root.joinpath("theme", *parts[1:])
    return root.joinpath(*parts)


def _safe_owned_dir(path: Path, *, must_exist: bool = False) -> None:
    if path.is_symlink() or (path.exists() and (
            not path.is_dir() or path.stat().st_uid != os.getuid()
            or path.stat().st_mode & 0o022)):
        raise PackImportError("unmanaged or unsafe Rice pack directory")
    if must_exist and not path.is_dir():
        raise PackImportError("Rice pack assets are unavailable")


def _ensure_dir(path: Path) -> None:
    _safe_owned_dir(path)
    if not path.exists():
        path.mkdir(mode=0o700, parents=False, exist_ok=False)


def _check_regular(path: Path, expected: str) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o022 or info.st_size > MAX_ENTRY):
            raise PackImportError("installed asset is unsafe or modified")
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise PackImportError("installed asset checksum mismatch")


def read_record(pack: RicePack, data_root: Path | None = None) -> dict:
    path = _record_path(pack.id, data_root)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o022 or info.st_size > MAX_MANIFEST):
            raise PackImportError("installed manifest is unsafe")
        values = json.loads(stream.read(MAX_MANIFEST + 1).decode("utf-8"))
    if pack_from_record(values, pack.id) != pack:
        raise PackImportError("installed pack metadata changed")
    return values


def describe_installed(pack: RicePack, data_root: Path | None = None) -> dict:
    record = read_record(pack, data_root)
    return {"revision": pack.revision, "assets": record["assets"],
            "license": record["license"], "file_count": len(record["files"])}


def _check_links(pack: RicePack, assets: dict, data_root: Path) -> None:
    base = _assets_path(pack, data_root)
    for folder, enabled, target in (("themes", "gtk" in assets or "xfwm" in assets, base / "theme"),
                                    ("icons", "icons" in assets, base / "icons")):
        if enabled:
            link = data_root / folder / _pack_name(pack)
            if not link.is_symlink() or os.readlink(link) != str(target):
                raise PackImportError("installed theme link was changed")


def verify_installed(pack: RicePack, *, data_root: Path | None = None) -> dict:
    if pack.source != "installed":
        raise PackImportError("only installed visual packs have custom assets")
    data = data_root if data_root is not None else data_home()
    record = read_record(pack, data)
    root = _assets_path(pack, data)
    _safe_owned_dir(root, must_exist=True)
    _check_links(pack, record["assets"], data)
    for name, digest in record["files"].items():
        path = _file_at(root, name)
        if any(parent.is_symlink() for parent in path.parents if parent == root or root in parent.parents):
            raise PackImportError("installed asset path contains a symlink")
        _check_regular(path, digest)
    return record


def style_for(pack: RicePack, *, data_root: Path | None = None):
    """Return a verified custom appearance plus optional wallpaper source."""
    from ..rice import STYLES

    if pack.source != "installed":
        return STYLES[pack.base_style], None
    record = verify_installed(pack, data_root=data_root)
    root = _assets_path(pack, data_root)
    overrides = {}
    name = theme_name(pack)
    assets = record["assets"]
    for kind, attr in (("gtk", "gtk"), ("xfwm", "xfwm"), ("icons", "icon_theme")):
        if kind in assets:
            overrides[attr] = name
    wallpaper = _file_at(root, assets["wallpaper"]) if "wallpaper" in assets else None
    return replace(STYLES[pack.base_style], **overrides), wallpaper


def plan_pack(pack: RicePack, *, backend=None, data_root: Path | None = None,
              config_root: Path | None = None, source_root: Path | None = None):
    from ..rice import plan

    style, wallpaper = style_for(pack, data_root=data_root)
    if pack.source != "installed":
        options = {key: value for key, value in (("backend", backend), ("data_root", data_root),
                    ("config_root", config_root), ("source_root", source_root)) if value is not None}
        return plan(pack.base_style, **options)
    return plan(pack.base_style, backend=backend, data_root=data_root,
                config_root=config_root, source_root=source_root,
                style_override=style, wallpaper_source=wallpaper)


def apply_pack(pack: RicePack, *, backend=None, data_root: Path | None = None,
               config_root: Path | None = None, source_root: Path | None = None):
    from ..rice import apply

    style, wallpaper = style_for(pack, data_root=data_root)
    if pack.source != "installed":
        options = {key: value for key, value in (("backend", backend), ("data_root", data_root),
                    ("config_root", config_root), ("source_root", source_root)) if value is not None}
        return apply(pack.base_style, **options)
    return apply(pack.base_style, backend=backend, data_root=data_root,
                 config_root=config_root, source_root=source_root,
                 style_override=style, wallpaper_source=wallpaper)


def _check_text(name: str, raw: bytes) -> None:
    if PurePosixPath(name).suffix.lower() not in TEXT_EXT and not name.endswith("/themerc"):
        return
    try:
        content = raw.decode("utf-8")
    except UnicodeError as exc:
        raise PackImportError("theme text must be UTF-8") from exc
    # GTK CSS allows external file/network imports. Keep this bounded first
    # version strictly self-contained; no CSS import, URL or XML/SVG renderer.
    if name.endswith(".css") and ("\\" in content or "/*" in content or
            re.search(r"@\s*import\b|\burl\s*\(|-gtk-icon-source", content, re.I)):
        raise PackImportError("GTK CSS external resource references are unsupported")


def _check_image(name: str, header: bytes) -> None:
    suffix = PurePosixPath(name).suffix.lower()
    if suffix == ".png":
        if (not header.startswith(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
                or len(header) < 24):
            raise PackImportError("invalid PNG image header")
        width = int.from_bytes(header[16:20], "big")
        height = int.from_bytes(header[20:24], "big")
        if not 1 <= width <= 16384 or not 1 <= height <= 16384:
            raise PackImportError("image dimensions exceed safety limit")
    elif suffix in (".jpg", ".jpeg") and not header.startswith(b"\xff\xd8\xff"):
        raise PackImportError("invalid JPEG image header")


@contextmanager
def _open_zip(archive: Path):
    """Hold an O_NOFOLLOW file descriptor across inspection and extraction."""
    descriptor = os.open(archive, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_ARCHIVE:
            raise PackImportError("archive must be a regular ZIP within 32 MiB")
        try:
            zf = zipfile.ZipFile(stream)
        except (zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
            raise PackImportError("invalid ZIP archive") from exc
        with zf:
            yield zf


def _inspect_open(zf: zipfile.ZipFile) -> dict:
    """Validate the already-open archive and return its manifest."""
    members = zf.infolist()
    if (len(members) > MAX_FILES + 1 or len({m.filename for m in members}) != len(members)
            or sum(m.file_size for m in members) > MAX_UNPACKED):
        raise PackImportError("archive inventory is oversized or duplicated")
    for entry in members:
        mode = entry.external_attr >> 16
        if (entry.is_dir() or entry.flag_bits & 1 or entry.file_size > MAX_ENTRY
                or (mode and stat.S_IFMT(mode) not in (0, stat.S_IFREG))
                or (entry.filename != "manifest.json" and not _valid_file(entry.filename))):
            raise PackImportError("archive contains an unsafe entry")
    try:
        meta = zf.getinfo("manifest.json")
        if meta.file_size > MAX_MANIFEST:
            raise PackImportError("manifest exceeds 64 KiB")
        values = _validate(json.loads(zf.read(meta).decode("utf-8")), installed=False)
    except (KeyError, UnicodeError, json.JSONDecodeError) as exc:
        raise PackImportError("missing or invalid manifest JSON") from exc
    if set(values["files"]) != {m.filename for m in members} - {"manifest.json"}:
        raise PackImportError("ZIP inventory does not match declared checksums")
    for name, expected in values["files"].items():
        h = hashlib.sha256()
        with zf.open(name) as stream:
            chunks = [] if name.endswith((".css", ".theme", "/themerc")) else None
            header = b""
            for block in iter(lambda: stream.read(64 * 1024), b""):
                if len(header) < 32:
                    header = (header + block)[:32]
                h.update(block)
                if chunks is not None:
                    chunks.append(block)
        if h.hexdigest() != expected:
            raise PackImportError("archive file checksum mismatch")
        if chunks is not None:
            _check_text(name, b"".join(chunks))
        if PurePosixPath(name).suffix.lower() in IMAGE_EXT:
            _check_image(name, header)
    return values


def inspect_archive(archive: Path) -> dict:
    """Read-only ZIP verification, never extracts or follows archive paths."""
    with _open_zip(archive) as zf:
        values = _inspect_open(zf)
    return {"id": values["id"], "name": values["name"],
            "base_style": values["base_style"], "license": values["license"],
            "assets": values["assets"], "file_count": len(values["files"])}


def build_archive(directory: Path, output: Path) -> dict:
    """Bundle selected local assets deterministically; never overwrite output."""
    _safe_owned_dir(directory, must_exist=True)
    manifest = directory / "manifest.json"
    if manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size > MAX_MANIFEST:
        raise PackImportError("draft manifest must be a safe regular file within 64 KiB")
    _check_regular(manifest, hashlib.sha256(manifest.read_bytes()).hexdigest())
    try:
        draft = json.loads(manifest.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PackImportError("invalid draft manifest") from exc
    if not isinstance(draft, dict) or ("files" in draft and draft["files"] != {}):
        raise PackImportError("draft must omit files or use an empty files object")
    members = []
    for path in sorted(directory.rglob("*")):
        if path == manifest or path.is_dir() and not path.is_symlink():
            continue
        name = path.relative_to(directory).as_posix()
        if not _valid_file(name) or path.is_symlink():
            raise PackImportError("draft contains an unknown or unsafe file")
        if len(members) >= MAX_FILES or path.stat().st_size > MAX_ENTRY:
            raise PackImportError("draft contains too many or oversized files")
        members.append((name, path))
    if sum(path.stat().st_size for _, path in members) > MAX_UNPACKED:
        raise PackImportError("draft assets exceed the unpacked limit")
    inventory = {}
    for name, path in members:
        data = path.read_bytes()
        _check_text(name, data)
        if PurePosixPath(name).suffix.lower() in IMAGE_EXT:
            _check_image(name, data[:32])
        inventory[name] = hashlib.sha256(data).hexdigest()
    record = _validate({**draft, "files": inventory}, installed=False)
    if output.is_symlink() or output.exists():
        raise PackImportError("output ZIP already exists; refusing to overwrite")
    descriptor = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as target, zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(record, indent=2, ensure_ascii=False))
            for name, path in members:
                _check_regular(path, inventory[name])
                zf.write(path, name)
        result = inspect_archive(output)
        if output.stat().st_size > MAX_ARCHIVE:
            raise PackImportError("ZIP exceeds 32 MiB")
        return result
    except Exception:
        output.unlink(missing_ok=True)
        raise


def install_archive(archive: Path, *, accept_license: bool = False,
                    data_root: Path | None = None) -> RicePack:
    """Import an immutable copy with exclusive names, or leave no visible pack."""
    if os.geteuid() == 0:
        raise PackImportError("import as your desktop user, never with sudo")
    if not accept_license:
        raise PackImportError("review the pack license, then pass --accept-license")
    data = data_root if data_root is not None else data_home()
    with _open_zip(archive) as zf:
        values = _inspect_open(zf)
        h = hashlib.sha256()
        zf.fp.seek(0)
        for chunk in iter(lambda: zf.fp.read(64 * 1024), b""):
            h.update(chunk)
        record = {**values, "revision": h.hexdigest()}
        pack = pack_from_record(record, values["id"])
        root = _root(data)
        _safe_owned_dir(data)
        if not data.exists():
            data.mkdir(mode=0o700, parents=True)
        if not root.exists():
            root.mkdir(mode=0o700)
        for parent in (root, root / "packs", root / "assets", data / "themes", data / "icons"):
            if parent != root:
                _ensure_dir(parent)
        destination = _assets_path(pack, data)
        manifest_path = _record_path(pack.id, data)
        from .packs import discover
        existing, _ = discover(root / "packs")
        if (any(item.id == pack.id for item in existing) or manifest_path.exists()
                or manifest_path.is_symlink() or destination.exists() or destination.is_symlink()):
            raise PackImportError("pack ID or installed asset name is already in use")
        link_targets = []
        for folder, enabled in (("themes", "gtk" in record["assets"] or "xfwm" in record["assets"]),
                                ("icons", "icons" in record["assets"])):
            if enabled:
                link = data / folder / theme_name(pack)
                if link.exists() or link.is_symlink():
                    raise PackImportError("a custom theme/icon name is already occupied")
                link_targets.append((link, destination / ("theme" if folder == "themes" else "icons")))
        staged = Path(tempfile.mkdtemp(prefix=".pack-stage-", dir=root))
        links_made = []
        created_root = False
        try:
            for name in record["files"]:
                target = _file_at(staged, name)
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                with zf.open(name) as original, target.open("xb") as output:
                    digest = hashlib.sha256()
                    for chunk in iter(lambda: original.read(64 * 1024), b""):
                        digest.update(chunk)
                        output.write(chunk)
                    if digest.hexdigest() != record["files"][name]:
                        raise PackImportError("archive changed during installation")
                os.chmod(target, 0o600)
            # Never replace an existing directory even if it appeared after preflight.
            destination.mkdir(mode=0o700, exist_ok=False)
            created_root = True
            for child in staged.iterdir():
                os.rename(child, destination / child.name)
            for link, target in link_targets:
                os.symlink(str(target), link)
                links_made.append((link, str(target)))
            contents = json.dumps(record, indent=2, ensure_ascii=False).encode("utf-8")
            if len(contents) > MAX_MANIFEST:
                raise PackImportError("installed manifest too large")
            fd, temp = tempfile.mkstemp(prefix=".pack-record-", dir=manifest_path.parent)
            try:
                with os.fdopen(fd, "wb") as output:
                    output.write(contents)
                    output.flush()
                    os.fsync(output.fileno())
                os.chmod(temp, 0o600)
                os.link(temp, manifest_path)  # O_EXCL semantics, no overwrite.
            finally:
                Path(temp).unlink(missing_ok=True)
        except Exception:
            for link, target in links_made:
                if link.is_symlink() and os.readlink(link) == target:
                    link.unlink()
            if created_root:
                shutil.rmtree(destination)
            raise
        finally:
            shutil.rmtree(staged)
    return pack


def remove_installed(pack: RicePack, *, backend=None, data_root: Path | None = None) -> Path:
    """Move owned assets/record to private recovery storage after checking use."""
    if os.geteuid() == 0:
        raise PackImportError("remove packs as your desktop user, never with sudo")
    data = data_root if data_root is not None else data_home()
    record = verify_installed(pack, data_root=data)
    from ..rice import XfceBackend

    desktop = backend or XfceBackend()
    name = theme_name(pack)
    # Missing desktop/session access is not proof that a theme is inactive.
    for channel, key in (("xsettings", "/Net/ThemeName"),
                         ("xfwm4", "/general/theme"),
                         ("xsettings", "/Net/IconThemeName")):
        if desktop.get("xfconf", channel, key) == name:
            raise PackImportError("pack is active; restore or switch your rice first")
    # Active recovery snapshots may require assets even if desktop was changed.
    backups = data / "macrice-state/backups/rice"
    if backups.is_dir() and not backups.is_symlink():
        candidates = list(islice(backups.iterdir(), 257))
        if len(candidates) > 256:
            raise PackImportError("too many active recovery records to verify safely")
        for folder in candidates:
            manifest = folder / "manifest.json"
            if (not folder.is_dir() or folder.is_symlink() or (folder / "restored").exists()
                    or (folder / "failed").exists() or not manifest.is_file()
                    or manifest.is_symlink() or manifest.stat().st_size > 256 * 1024):
                continue
            if name in manifest.read_text(encoding="utf-8"):
                raise PackImportError("a pending Rice restore still references this pack")
    root = _root(data)
    trash = root / "removed"
    _ensure_dir(trash)
    archive = trash / f"{pack.id}-{pack.revision[:12]}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
    archive.mkdir(mode=0o700, exist_ok=False)
    asset = _assets_path(pack, data)
    original = _record_path(pack.id, data)
    links = []
    try:
        for kind, enabled in (("themes", "gtk" in record["assets"] or "xfwm" in record["assets"]),
                              ("icons", "icons" in record["assets"])):
            if enabled:
                link = data / kind / name
                target = str(asset / ("theme" if kind == "themes" else "icons"))
                if not link.is_symlink() or os.readlink(link) != target:
                    raise PackImportError("theme link changed while removing the pack")
                link.unlink()
                links.append((link, target))
        os.rename(original, archive / "manifest.json")
        os.rename(asset, archive / "assets")
    except Exception:
        if (archive / "assets").exists() and not asset.exists():
            os.rename(archive / "assets", asset)
        if (archive / "manifest.json").exists() and not original.exists():
            os.rename(archive / "manifest.json", original)
        for link, target in links:
            if not link.exists() and not link.is_symlink():
                os.symlink(target, link)
        raise
    return archive
