#!/bin/sh
# CI-only: real two-output labwc with one native RicePlate process. The native
# renderer must own both panel surfaces and recover a secondary hotplug.
set -eu

source_root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd -P)
native="$source_root/components/riceplate-wayland/target/release/riceplate-native"
if [ ! -x "$native" ]; then
    echo "Missing native RicePlate preview binary" >&2
    exit 1
fi
runtime=$(mktemp -d)
chmod 0700 "$runtime"
trap 'rm -r -- "$runtime" 2>/dev/null || :' EXIT
export XDG_RUNTIME_DIR="$runtime"
export WLR_BACKENDS=headless
export WLR_HEADLESS_OUTPUTS=2
export WLR_RENDERER=pixman
export RICEBOWL_DE_NESTED=1

dbus-run-session -- sh -eu -c '
    source_root=$1
    runtime=$2
    native=$3
    labwc --config-dir "$source_root/macrice/de/resources/labwc" \
        --startup true >"$runtime/labwc.log" 2>&1 &
    compositor=$!
    plate=
    cleanup() {
        if [ -n "$plate" ]; then kill "$plate" 2>/dev/null || :; wait "$plate" 2>/dev/null || :; fi
        kill "$compositor" 2>/dev/null || :
        wait "$compositor" 2>/dev/null || :
    }
    trap cleanup EXIT
    count=0
    while [ "$count" -lt 40 ] && [ ! -S "$runtime/wayland-0" ]; do
        kill -0 "$compositor" 2>/dev/null || exit 1
        count=$((count + 1))
        sleep 0.25
    done
    [ -S "$runtime/wayland-0" ] || { echo "No headless Wayland socket" >&2; exit 1; }
    export WAYLAND_DISPLAY=wayland-0
    "$native" --recipe classic >"$runtime/plate.log" 2>&1 &
    plate=$!
    count=0
    while [ "$count" -lt 30 ]; do
        if ! kill -0 "$plate" 2>/dev/null; then
            echo "Native panel exited before output test" >&2
            sed -n "1,120p" "$runtime/plate.log" >&2
            exit 1
        fi
        count=$((count + 1))
        sleep 0.1
    done
    set -- $(wlr-randr | sed -n "/^[A-Za-z0-9_.-][A-Za-z0-9_.-]*[[:space:]]/s/[[:space:]].*//p")
    [ "$#" -eq 2 ] || { echo "Expected exactly two Wayland outputs" >&2; exit 1; }
    first=$1
    second=$2
    grim -o "$first" "$runtime/first.png"
    grim -o "$second" "$runtime/second.png"
    /usr/bin/python3 "$source_root/scripts/check_wayland_panel_outputs.py" \
        "$runtime/first.png" "$runtime/second.png"
    wlr-randr --output "$second" --off
    sleep 0.6
    grim -o "$first" "$runtime/first-after-off.png"
    /usr/bin/python3 "$source_root/scripts/check_wayland_panel_outputs.py" \
        "$runtime/first-after-off.png"
    wlr-randr --output "$second" --on
    sleep 0.8
    grim -o "$second" "$runtime/second-after-on.png"
    /usr/bin/python3 "$source_root/scripts/check_wayland_panel_outputs.py" \
        "$runtime/second-after-on.png"
    kill -0 "$plate" 2>/dev/null || { echo "Native panel exited after hotplug" >&2; exit 1; }
    echo "One native RicePlate process painted two outputs and survived secondary hotplug"
' sh "$source_root" "$runtime" "$native"
