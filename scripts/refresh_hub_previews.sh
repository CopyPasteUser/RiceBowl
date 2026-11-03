#!/usr/bin/env bash
# Regenerate GTK3-compatible previews from the latest verified X11 gallery.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if command -v magick >/dev/null 2>&1; then
    convert_image=(magick)
elif command -v convert >/dev/null 2>&1; then
    convert_image=(convert)
else
    echo 'ImageMagick is required to refresh the developer preview assets.' >&2
    exit 1
fi

mkdir -p "$root/assets/hub-previews"
for name in aero windows10 winxp winclassic chromeos frutiger; do
    "${convert_image[@]}" "$root/screenshots/current/${name}-start.webp" \
        -resize 960x540 -strip -sampling-factor 4:4:4 -quality 88 \
        "$root/assets/hub-previews/${name}.jpg"
done
