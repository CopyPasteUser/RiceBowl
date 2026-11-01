#!/usr/bin/env bash
# Non-root MacMenu user installer. Previous managed versions are safely migrated.
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec /usr/bin/python3 "${project_dir}/scripts/install_user.py" "$@"
