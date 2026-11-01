#!/usr/bin/env bash
# Build a standard, distribution-managed package without root privileges.
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
project_version="$(sed -n 's/^version = "\([^"]*\)"$/\1/p' "${project_dir}/pyproject.toml" | head -n 1)"
version="${1:-${project_version/rc/~rc}}"
if [[ ! "${version}" =~ ^[0-9]+\.[0-9]+\.[0-9]+(~rc[0-9]+)?$ ]]; then
    echo 'Version must be X.Y.Z or X.Y.Z~rcN.' >&2
    exit 2
fi
if ! command -v dpkg-deb >/dev/null 2>&1; then
    echo 'dpkg-deb is not available.' >&2
    exit 1
fi

stage_dir="$(mktemp -d -t macmenu-deb.XXXXXXXX)"
trap 'rm -r -- "${stage_dir}"' EXIT
# mktemp creates 0700 directories. dpkg-deb preserves the root directory mode
# of its input tree; shipping ./ as 0700 could break installation permissions.
chmod 0755 "${stage_dir}"

mkdir -p "${stage_dir}/DEBIAN" "${stage_dir}/usr/share/macmenu/macmenu" \
    "${stage_dir}/usr/share/macmenu/assets" "${stage_dir}/usr/share/applications" "${stage_dir}/usr/bin"
install -m 0644 "${project_dir}"/macmenu/*.py "${stage_dir}/usr/share/macmenu/macmenu/"
install -m 0644 "${project_dir}"/assets/*.svg "${stage_dir}/usr/share/macmenu/assets/"
install -m 0755 "${project_dir}/scripts/macmenu" "${stage_dir}/usr/share/macmenu/launcher"
install -m 0644 "${project_dir}/scripts/macmenu.desktop" \
    "${stage_dir}/usr/share/applications/macmenu.desktop"
sed -i 's|^Icon=macmenu$|Icon=/usr/share/macmenu/assets/macmenu-app.svg|' \
    "${stage_dir}/usr/share/applications/macmenu.desktop"
ln -s /usr/share/macmenu/launcher "${stage_dir}/usr/bin/macmenu"

printf 'Package: xfce-macmenu\nVersion: %s\nSection: x11\nPriority: optional\nArchitecture: all\nMaintainer: MacMenu Project\nDepends: python3 (>= 3.10), python3-gi, gir1.2-gtk-3.0, librsvg2-common, exo-utils\nDescription: Fast macOS-inspired application launcher for Xfce\n MacMenu provides a monochrome Linux penguin icon, searchable app grid,\n fast shortcut toggle, favorites and appearance settings.\n' "${version}" > "${stage_dir}/DEBIAN/control"

if [[ -n "${SOURCE_DATE_EPOCH:-}" ]]; then
    find "${stage_dir}" -exec touch -h -d "@${SOURCE_DATE_EPOCH}" {} +
fi
output="${project_dir}/MacMenu-XFCE_${version/\~/-}_all.deb"
dpkg-deb --build --root-owner-group "${stage_dir}" "${output}"
echo "Package created: ${output}"
