#!/bin/sh
# CI-only: real headless labwc plus one separately launched native layer surface.
set -eu

source_root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd -P)
native="$source_root/components/riceplate-wayland/target/release/riceplate-native"
if [ ! -x "$native" ]; then
    echo "Native RicePlate binary is not built" >&2
    exit 1
fi
"$native" --version

runtime=$(mktemp -d)
chmod 0700 "$runtime"
cleanup_runtime() {
    if ! rm -r -- "$runtime" 2>/dev/null; then
        echo "CI note: temporary runtime mount remained for runner cleanup" >&2
    fi
}
trap cleanup_runtime EXIT
export XDG_RUNTIME_DIR="$runtime"
export WLR_BACKENDS=headless
export WLR_HEADLESS_OUTPUTS=1
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
        if [ -n "$plate" ]; then
            kill "$plate" 2>/dev/null || :
            wait "$plate" 2>/dev/null || :
        fi
        kill "$compositor" 2>/dev/null || :
        wait "$compositor" 2>/dev/null || :
    }
    trap cleanup EXIT
    count=0
    while [ "$count" -lt 40 ]; do
        if ! kill -0 "$compositor" 2>/dev/null; then
            echo "labwc stopped before creating the Wayland socket" >&2
            sed -n "1,70p" "$runtime/labwc.log" >&2
            exit 1
        fi
        if [ -S "$runtime/wayland-0" ]; then break; fi
        count=$((count + 1))
        sleep 0.25
    done
    if [ ! -S "$runtime/wayland-0" ]; then
        echo "No headless Wayland socket" >&2
        sed -n "1,70p" "$runtime/labwc.log" >&2
        exit 1
    fi
    WAYLAND_DISPLAY=wayland-0 "$native" >"$runtime/plate.log" 2>&1 &
    plate=$!
    sleep 1
    state=$(ps -o stat= -p "$plate" 2>/dev/null || :)
    case "$state" in
        ""|*Z*)
            echo "Native RicePlate surface exited unexpectedly" >&2
            sed -n "1,80p" "$runtime/plate.log" >&2
            sed -n "1,80p" "$runtime/labwc.log" >&2
            exit 1 ;;
    esac
    echo "Native RicePlate layer surface remained alive on headless labwc"
    kill "$plate"
    wait "$plate" 2>/dev/null || :
    plate=
    WAYLAND_DISPLAY=wayland-0 labwc --exit >/dev/null 2>&1 || :
    wait "$compositor"
' sh "$source_root" "$runtime" "$native"
