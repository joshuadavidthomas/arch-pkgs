#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

shopt -s nullglob
scripts=(./*/update.sh)

if [[ ${#scripts[@]} -eq 0 ]]; then
  echo "No package update scripts found." >&2
  exit 1
fi

failures=()

for script in "${scripts[@]}"; do
  package=${script#./}
  package=${package%/update.sh}

  echo "==> Updating $package..."
  if bash "$script" "$@"; then
    echo
  else
    echo ":: Failed to update $package" >&2
    echo >&2
    failures+=("$package")
  fi
done

if [[ ${#failures[@]} -gt 0 ]]; then
  echo "Update failed for: ${failures[*]}" >&2
  exit 1
fi

echo "All package metadata is up to date."
