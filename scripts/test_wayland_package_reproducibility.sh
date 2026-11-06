#!/bin/sh
# Build the same no-install Debian preview twice at different wall times.
set -eu

source_root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd -P)
test_dir=$(mktemp -d)
trap 'rm -r -- "$test_dir"' EXIT

sh "$source_root/scripts/build_wayland_session_deb.sh" "$test_dir/first.deb" >/dev/null
sleep 2
sh "$source_root/scripts/build_wayland_session_deb.sh" "$test_dir/second.deb" >/dev/null
if ! cmp -s "$test_dir/first.deb" "$test_dir/second.deb"; then
    echo "Wayland session package is not reproducible" >&2
    exit 1
fi
dpkg-deb --field "$test_dir/first.deb" Package Version Architecture
echo "Wayland session package is byte-for-byte reproducible"
