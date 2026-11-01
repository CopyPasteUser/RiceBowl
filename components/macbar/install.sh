#!/bin/sh
set -eu

# Safe by default: installing does not stop or change the existing XFCE panel.
usage() {
    printf 'Usage: ./install.sh [--autostart] [--replace-xfce]\n'
    exit 2
}

autostart=0
replace=0
for arg in "$@"; do
    case "$arg" in
        --autostart) autostart=1 ;;
        --replace-xfce) replace=1 ;;
        *) usage ;;
    esac
done

if [ "$replace" -eq 1 ] && [ "$autostart" -ne 1 ]; then
    printf '%s\n' 'Error: --replace-xfce requires --autostart.' >&2
    exit 2
fi

source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
data_dir="${XDG_DATA_HOME:-$HOME/.local/share}/macbar"
bin_dir="${XDG_BIN_HOME:-$HOME/.local/bin}"
config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/macbar"
autostart_dir="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"

if ! /usr/bin/python3 -c 'import gi; gi.require_version("Gtk", "3.0"); gi.require_version("GdkX11", "3.0"); from gi.repository import Gtk, GdkX11'; then
    printf '%s\n' 'Missing GTK3 Python bindings. On Mint/Ubuntu: sudo apt install python3-gi gir1.2-gtk-3.0' >&2
    exit 1
fi

install -d "$data_dir" "$bin_dir" "$config_dir"
install -m 755 "$source_dir/macbar.py" "$data_dir/macbar.py"
install -m 644 "$source_dir/status.py" "$data_dir/status.py"
if [ ! -e "$config_dir/config.json" ]; then
    install -m 644 "$source_dir/config.example.json" "$config_dir/config.json"
fi

# The installer-local data_dir becomes a literal path in the launcher.
printf '#!/bin/sh\nexec /usr/bin/python3 "%s/macbar.py" "$@"\n' "$data_dir" > "$bin_dir/macbar"
chmod 755 "$bin_dir/macbar"

if [ "$autostart" -eq 1 ]; then
    install -d "$autostart_dir"
    if [ "$replace" -eq 1 ]; then
        extra=' --replace-xfce'
    else
        extra=''
    fi
    printf '[Desktop Entry]\nType=Application\nName=MacBar\nComment=Minimal macOS-style top panel\nExec="%s/macbar"%s\nTerminal=false\nOnlyShowIn=XFCE;\nX-GNOME-Autostart-enabled=true\n' "$bin_dir" "$extra" > "$autostart_dir/macbar.desktop"
    printf '%s\n' 'Autostart enabled. You can remove ~/.config/autostart/macbar.desktop to undo it.'
fi

printf '\nInstalled: %s/macbar\n' "$bin_dir"
printf 'Configuration: %s/config.json\n' "$config_dir"
printf '%s\n' 'Try it first without replacing XFCE: ~/.local/bin/macbar'
