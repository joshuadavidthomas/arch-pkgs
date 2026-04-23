#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

force=false
if [[ "${1:-}" == "--force" ]]; then
  force=true
fi

echo "Checking niri upstream for buffer size fix..."
if curl -sf https://raw.githubusercontent.com/niri-wm/niri/main/src/main.rs \
  | grep -q 'max_buffer_size'; then
  echo "Fix appears to be upstream. You can switch back to the official Arch package:"
  echo "  sudo pacman -S niri"
  exit 0
fi

echo "Fix is not upstream yet."
latest=$(pacman -Si niri 2>/dev/null | awk '/^Version/ {print $3}' | cut -d- -f1)
current_pkgver=$(sed -n 's/^pkgver=//p' PKGBUILD)

echo "Current:  $current_pkgver"
echo "Official: $latest"

if [[ -z "$latest" ]]; then
  echo "Could not determine latest niri version from repos." >&2
  exit 1
fi

if [[ "$latest" == "$current_pkgver" ]] && ! $force; then
  echo "PKGBUILD is already up to date."
  exit 0
fi

echo "Updating PKGBUILD to $latest..."
sed -i "s/^pkgver=.*/pkgver=$latest/" PKGBUILD
sed -i "s/^pkgrel=.*/pkgrel=1/" PKGBUILD
updpkgsums
makepkg --printsrcinfo > .SRCINFO

echo "Updated PKGBUILD and .SRCINFO to $latest."
