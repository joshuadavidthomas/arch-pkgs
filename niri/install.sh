#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

force=false
if [[ "${1:-}" == "--force" || "${1:-}" == "--reinstall" ]]; then
  force=true
fi

# Check if the patch is still needed
echo "Checking niri upstream for buffer size fix..."
if curl -sf "https://raw.githubusercontent.com/YaLTeR/niri/main/src/main.rs" \
    | grep -q 'max_buffer_size'; then
  echo "Fix appears to be upstream! You can switch back to the official Arch package:"
  echo "  sudo pacman -S niri"
  exit 0
fi
echo "Fix is NOT upstream yet. Continuing with patched build."
echo ""

latest=$(pacman -Si niri 2>/dev/null | awk '/^Version/ {print $3}' | cut -d- -f1)
current_pkgver=$(sed -n 's/^pkgver=//p' PKGBUILD)
installed_version=$(pacman -Q niri 2>/dev/null | awk '{print $2}' | sed 's/-.*//' || true)

if [[ -z "$latest" ]]; then
  echo "Could not determine latest niri version from repos."
  exit 1
fi

echo "Installed: ${installed_version:-not installed}"
echo "Repo: $latest"
echo "PKGBUILD: $current_pkgver"

if [[ "$latest" == "$installed_version" ]] && ! $force; then
  echo "Already installed and up to date."
  exit 0
fi

if [[ "$current_pkgver" != "$latest" ]]; then
  echo "Updating PKGBUILD: $current_pkgver → $latest"
  sed -i "s/^pkgver=.*/pkgver=$latest/" PKGBUILD
  sed -i "s/^pkgrel=.*/pkgrel=2/" PKGBUILD
  updpkgsums
fi

echo "Building niri $latest..."
makepkg -sf --nocheck
sudo pacman -U --noconfirm niri-[0-9]*.pkg.tar.zst
