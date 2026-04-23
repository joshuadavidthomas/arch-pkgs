#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

force=false
if [[ "${1:-}" == "--force" ]]; then
  force=true
fi

echo "Checking for latest Little Snitch for Linux version..."
download_page=$(curl -fsSL https://obdev.at/products/littlesnitch-linux/download.html)

artifact=$(echo "$download_page" \
  | grep -oE 'littlesnitch-[0-9]+\.[0-9]+\.[0-9]+-[0-9]+-x86_64\.pkg\.tar\.zst' \
  | head -n1)

if [[ -z "$artifact" ]]; then
  echo "Could not find x86_64 .pkg.tar.zst on the download page." >&2
  exit 1
fi

upstream_version=$(echo "$artifact" | sed -E 's/^littlesnitch-([0-9]+\.[0-9]+\.[0-9]+-[0-9]+)-x86_64.*/\1/')
pkgver=$(echo "$upstream_version" | sed 's/-/_/')
current_pkgver=$(sed -n 's/^pkgver=//p' PKGBUILD)

echo "Current:  $current_pkgver"
echo "Upstream: $pkgver"

if [[ "$pkgver" == "$current_pkgver" ]] && ! $force; then
  echo "PKGBUILD is already up to date."
  exit 0
fi

echo "Updating PKGBUILD to $pkgver..."
hashes=$(curl -fsSL "https://obdev.at/downloads/littlesnitch-linux/littlesnitch-${upstream_version%-*}.hashes.txt")
new_sha256=$(echo "$hashes" | awk -v fn="$artifact" '$2==fn {print $1}')
if [[ -z "$new_sha256" ]]; then
  echo "Could not find sha256 for $artifact in hashes.txt." >&2
  exit 1
fi

sed -i "s/^pkgver=.*/pkgver=$pkgver/" PKGBUILD
sed -i "s/^pkgrel=.*/pkgrel=1/" PKGBUILD
sed -i "s/^sha256sums=.*/sha256sums=('$new_sha256')/" PKGBUILD
makepkg --printsrcinfo > .SRCINFO

echo "Updated PKGBUILD and .SRCINFO to $pkgver."
