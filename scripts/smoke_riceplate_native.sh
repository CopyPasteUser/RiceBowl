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
if "$native" --recipe ../classic >/dev/null 2>&1; then
    echo "Native RicePlate accepted an unsupported external recipe" >&2
    exit 1
fi

runtime=$(mktemp -d)
chmod 0700 "$runtime"
cp "$source_root/macrice/de/resources/recipes/classic.json" "$runtime/custom.json"
chmod 0600 "$runtime/custom.json"
ln -s "$runtime/custom.json" "$runtime/symlink.json"
if "$native" --recipe "$runtime/symlink.json" >"$runtime/rejected.log" 2>&1; then
    echo "Native RicePlate accepted a symlinked recipe" >&2
    exit 1
fi
chmod 0644 "$runtime/custom.json"
if "$native" --recipe "$runtime/custom.json" >"$runtime/rejected.log" 2>&1; then
    echo "Native RicePlate accepted an overly public recipe" >&2
    exit 1
fi
if ! grep -q "owner-private" "$runtime/rejected.log"; then
    echo "Native RicePlate did not reject unsafe permissions at validation" >&2
    exit 1
fi
chmod 0600 "$runtime/custom.json"
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
    for recipe in classic chrome "$runtime/custom.json"; do
        case "$recipe" in
            /*) label=custom ;;
            *) label=$recipe ;;
        esac
        WAYLAND_DISPLAY=wayland-0 "$native" --recipe "$recipe" >"$runtime/plate-$label.log" 2>&1 &
        plate=$!
        sleep 1
        state=$(ps -o stat= -p "$plate" 2>/dev/null || :)
        case "$state" in
            ""|*Z*)
                echo "Native RicePlate ($label) exited unexpectedly" >&2
                sed -n "1,80p" "$runtime/plate-$label.log" >&2
                sed -n "1,80p" "$runtime/labwc.log" >&2
                exit 1 ;;
        esac
        echo "Native RicePlate $label layer surface remained alive"
        kill "$plate"
        wait "$plate" 2>/dev/null || :
        plate=
    done
    # We own this exact CI compositor PID. On labwc 0.7.1 the --exit client
    # command is not a reliable external teardown mechanism in a headless job.
    kill -TERM "$compositor"
    count=0
    while [ "$count" -lt 40 ]; do
        state=$(ps -o stat= -p "$compositor" 2>/dev/null || :)
        case "$state" in
            ""|*Z*)
                wait "$compositor" 2>/dev/null || :
                echo "Native RicePlate and headless labwc shut down cleanly"
                exit 0 ;;
        esac
        count=$((count + 1))
        sleep 0.25
    done
    echo "CI labwc did not respond to SIGTERM" >&2
    sed -n "1,70p" "$runtime/labwc.log" >&2
    exit 1
' sh "$source_root" "$runtime" "$native"
