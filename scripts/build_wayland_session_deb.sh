#!/bin/sh
# Build an opt-in, removable login session package without touching the host.
set -eu

if ! command -v dpkg-deb >/dev/null 2>&1; then
    echo "dpkg-deb is required to build the Debian session package." >&2
    exit 1
fi
project_root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd -P)
version='0.1.0~preview1'
output=${1:-"$project_root/dist/ricebowl-wayland-session_${version}_all.deb"}
if [ -e "$output" ] || [ -L "$output" ]; then
    echo "Refusing to overwrite an existing package: $output" >&2
    exit 1
fi
mkdir -p -- "$(dirname -- "$output")"
stage=$(mktemp -d)
trap 'rm -r -- "$stage"' EXIT

install -D -m 0644 "$project_root/packaging/wayland/control" "$stage/DEBIAN/control"
install -D -m 0755 "$project_root/packaging/wayland/ricebowl-wayland-session" \
    "$stage/usr/bin/ricebowl-wayland-session"
install -D -m 0644 "$project_root/packaging/wayland/ricebowl.desktop" \
    "$stage/usr/share/wayland-sessions/ricebowl.desktop"
install -D -m 0644 "$project_root/packaging/wayland/ricebowl-portals.conf" \
    "$stage/usr/share/xdg-desktop-portal/ricebowl-portals.conf"
install -D -m 0644 "$project_root/packaging/wayland/ricebowl-session.target" \
    "$stage/usr/lib/systemd/user/ricebowl-session.target"

dpkg-deb --build --root-owner-group "$stage" "$output"
echo "Built $output (not installed)"
