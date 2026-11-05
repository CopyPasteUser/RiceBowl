#!/bin/sh
# Linux CI: launch real labwc 0.7+ headless and require a responsive Wayland
# socket plus a live native panel. Runs only inside an isolated D-Bus session.
set -eu

project_root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd -P)
runtime=$(mktemp -d)
chmod 0700 "$runtime"
trap 'rm -r -- "$runtime"' EXIT
export XDG_RUNTIME_DIR="$runtime"
export WLR_BACKENDS=headless
export WLR_HEADLESS_OUTPUTS=1
export WLR_RENDERER=pixman
export XDG_SESSION_TYPE=wayland

dbus-run-session -- sh -eu -c '
    project_root=$1
    runtime=$2
    /usr/bin/python3 "$project_root/launcher.py" de start --nested >"$runtime/labwc.log" 2>&1 &
    compositor=$!
    trap "kill $compositor 2>/dev/null || :; wait $compositor 2>/dev/null || :" EXIT
    ready=0
    count=0
    while [ "$count" -lt 80 ]; do
        if ! kill -0 "$compositor" 2>/dev/null; then
            echo "labwc exited before its Wayland socket was ready" >&2
            sed -n "1,100p" "$runtime/labwc.log" >&2
            exit 1
        fi
        if [ -S "$runtime/wayland-0" ]; then
            ready=1
            break
        fi
        count=$((count + 1))
        sleep 0.25
    done
    if [ "$ready" -ne 1 ]; then
        echo "No Wayland socket after 20 seconds" >&2
        sed -n "1,100p" "$runtime/labwc.log" >&2
        exit 1
    fi
    export WAYLAND_DISPLAY=wayland-0
    if ! timeout 8s wayland-info >/dev/null 2>"$runtime/info.log"; then
        echo "Wayland compositor did not answer protocol discovery" >&2
        sed -n "1,100p" "$runtime/info.log" >&2
        sed -n "1,100p" "$runtime/labwc.log" >&2
        exit 1
    fi
    # The nested session must not import or override the parent activation
    # environment. A native panel still needs to start successfully.
    ready=0
    count=0
    while [ "$count" -lt 40 ]; do
        if pgrep -u "$(id -u)" -x waybar >/dev/null 2>&1; then
            ready=1
            break
        fi
        count=$((count + 1))
        sleep 0.25
    done
    if [ "$ready" -ne 1 ]; then
        echo "Waybar did not start in the labwc preview session" >&2
        sed -n "1,100p" "$runtime/labwc.log" >&2
        exit 1
    fi
    # Closing the native panel must also end the compositor. This is essential
    # on labwc 0.7.1 shipped with Mint 22, which lacks --session supervision.
    pkill -TERM -u "$(id -u)" -x waybar
    count=0
    while [ "$count" -lt 40 ]; do
        if ! kill -0 "$compositor" 2>/dev/null; then
            echo "labwc and Waybar started, then exited cleanly together"
            exit 0
        fi
        # A terminated child remains visible to kill -0 until the EXIT trap
        # reaps it. A zombie here also proves that labwc has shut down.
        state=$(ps -o stat= -p "$compositor" 2>/dev/null || :)
        case "$state" in
            *Z*) echo "labwc and Waybar started, then exited cleanly together"; exit 0 ;;
        esac
        count=$((count + 1))
        sleep 0.25
    done
    echo "labwc stayed alive after the panel exited" >&2
    sed -n "1,100p" "$runtime/labwc.log" >&2
    exit 1
' sh "$project_root" "$runtime"
