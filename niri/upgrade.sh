#!/usr/bin/env bash
set -euo pipefail

# Rebuild and install the patched niri package.
# Updates the PKGBUILD to match the latest version in the Arch repos,
# downloads the new source, applies the patch, builds, and installs.

cd "$(dirname "$0")"

# Check upstream first
./check-upstream.sh
echo ""

latest=$(pacman -Si niri 2>/dev/null | awk '/^Version/ {print $3}' | cut -d- -f1)
current_pkgver=$(grep '^pkgver=' PKGBUILD | cut -d= -f2)

if [[ -z "$latest" ]]; then
    echo "Could not determine latest niri version from repos."
    exit 1
fi

if [[ "$current_pkgver" != "$latest" ]]; then
    echo "Updating PKGBUILD: $current_pkgver → $latest"
    sed -i "s/^pkgver=.*/pkgver=$latest/" PKGBUILD
    # Reset pkgrel when version changes
    sed -i "s/^pkgrel=.*/pkgrel=2/" PKGBUILD
    updpkgsums
fi

echo "Building niri $latest..."
makepkg -sf --nocheck

echo ""
echo "Build complete. Install with:"
echo "  sudo pacman -U $(ls -1 niri-[0-9]*.pkg.tar.zst | tail -1)"
