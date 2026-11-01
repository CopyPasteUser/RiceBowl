#!/usr/bin/env bash
set -euo pipefail
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SOURCE"
exec /usr/bin/python3 -m macrice install "$@"
