#!/bin/sh
# Explicit, manual capture of the RUNNING Wayland compositor, never a synthetic preview.
set -eu

if [ "$#" -ne 1 ]; then
    echo "Usage: capture_wayland_panel.sh /absolute/new-capture.png" >&2
    exit 2
fi
case "$1" in
    /*.png) target=$1 ;;
    *) echo "Choose a new absolute .png output path" >&2; exit 2 ;;
esac
if [ -z "${WAYLAND_DISPLAY:-}" ] || ! command -v grim >/dev/null 2>&1; then
    echo "Requires a running Wayland session and the grim screenshot utility" >&2
    exit 1
fi
if [ -e "$target" ] || [ -L "$target" ]; then
    echo "Capture destination already exists (will not overwrite)" >&2
    exit 1
fi
umask 077
directory=$(dirname -- "$target")
temporary=$(mktemp "$directory/.ricebowl-capture-XXXXXXXX")
trap 'rm -f -- "$temporary"' EXIT HUP INT TERM
grim - > "$temporary"
python3 - "$temporary" <<'PY'
import struct
import sys
from pathlib import Path

source = Path(sys.argv[1])
with source.open("rb") as stream:
    raw = stream.read(24)
if (not 512 <= source.stat().st_size <= 64 * 1024 * 1024
        or raw[:8] != b"\x89PNG\r\n\x1a\n"
        or not all(1 <= x <= 8192 for x in struct.unpack(">II", raw[16:24]))):
    raise SystemExit("grim did not produce a valid bounded PNG screenshot")
PY
ln -- "$temporary" "$target"
echo "Captured actual Wayland framebuffer: $target"
