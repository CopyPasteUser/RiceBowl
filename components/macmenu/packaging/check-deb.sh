#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! -f "$1" ]]; then
    echo 'Usage: bash packaging/check-deb.sh FILE.deb' >&2
    exit 2
fi
package="$1"
root_mode="$(dpkg-deb --contents "${package}" | awk '$NF == "./" { print $1 }')"
if [[ "${root_mode}" != 'drwxr-xr-x' ]]; then
    echo "Unsafe package root permissions: ${root_mode}" >&2
    exit 1
fi
if [[ "$(dpkg-deb --field "${package}" Package)" != 'xfce-macmenu' ]]; then
    echo 'Unexpected Debian package name.' >&2
    exit 1
fi
contents="$(dpkg-deb --contents "${package}")"
for file in './usr/bin/macmenu' './usr/share/macmenu/launcher' \
    './usr/share/macmenu/macmenu/commands.py' './usr/share/applications/macmenu.desktop' \
    './usr/share/macmenu/assets/macmenu-app.svg' \
    './usr/share/macmenu/assets/macmenu-penguin.svg' \
    './usr/share/macmenu/assets/macmenu-penguin-ink.svg'; do
    if [[ "${contents}" != *"${file}"* ]]; then
        echo "Package file is missing: ${file}" >&2
        exit 1
    fi
done
if [[ "${contents}" == *'./usr/share/macmenu/macmenu/session.py'* ]]; then
    echo 'Legacy session control code is still packaged.' >&2
    exit 1
fi
desktop_contents="$(dpkg-deb --fsys-tarfile "${package}" | tar -xO ./usr/share/applications/macmenu.desktop)"
if [[ "${desktop_contents}" != *'Icon=/usr/share/macmenu/assets/macmenu-app.svg'* ]]; then
    echo 'The desktop entry does not reference the packaged MacMenu icon.' >&2
    exit 1
fi
echo "Debian package verified: $(dpkg-deb --field "${package}" Version), root permissions 0755"
