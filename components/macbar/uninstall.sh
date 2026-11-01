#!/bin/sh
set -eu

# Only remove installed MacBar-owned files; keep user configuration and XFCE.
config_home="${XDG_CONFIG_HOME:-$HOME/.config}"
data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
autostart="$config_home/autostart/macbar.desktop"

if [ -f "$autostart" ] && grep -q '^Name=MacBar$' "$autostart"; then
    rm -f -- "$autostart"
fi

launcher="$HOME/.local/bin/macbar"
if [ -f "$launcher" ] && grep -q '/macbar.py' "$launcher"; then
    rm -f -- "$launcher"
fi

for file in macbar.py status.py; do
    if [ -f "$data_home/macbar/$file" ]; then
        rm -f -- "$data_home/macbar/$file"
    fi
done

printf '%s\n' 'MacBar removed. Your ~/.config/macbar settings were kept.'
printf '%s\n' 'To restore the original top panel, run: xfce4-panel'
