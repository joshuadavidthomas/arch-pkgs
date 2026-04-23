#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

force=false
if [[ "${1:-}" == "--force" || "${1:-}" == "--reinstall" ]]; then
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

upstream_version=$(echo "$artifact" | sed -E 's/^littlesnitch-([0-9.]+)-([0-9]+)-x86_64.*/\1/')
upstream_pkgrel=$(echo "$artifact" | sed -E 's/^littlesnitch-([0-9.]+)-([0-9]+)-x86_64.*/\2/')

current_version=$(sed -n 's/^pkgver=//p' PKGBUILD)
current_pkgrel=$(sed -n 's/^_pkgrel_upstream=//p' PKGBUILD)

echo "Current:  $current_version-$current_pkgrel"
echo "Upstream: $upstream_version-$upstream_pkgrel"

installed_version=$(pacman -Q littlesnitch 2>/dev/null | awk '{print $2}' | sed 's/-.*//' || true)

if [[ "$upstream_version" == "$installed_version" \
   && "$upstream_version" == "$current_version" \
   && "$upstream_pkgrel" == "$current_pkgrel" ]] && ! $force; then
  echo "Already installed and up to date."
  exit 0
fi

if [[ "$upstream_version" != "$current_version" || "$upstream_pkgrel" != "$current_pkgrel" ]]; then
  echo "Updating PKGBUILD to $upstream_version-$upstream_pkgrel..."

  hashes=$(curl -fsSL "https://obdev.at/downloads/littlesnitch-linux/littlesnitch-${upstream_version}.hashes.txt")
  new_sha256=$(echo "$hashes" | awk -v fn="$artifact" '$2==fn {print $1}')
  if [[ -z "$new_sha256" ]]; then
    echo "Could not find sha256 for $artifact in hashes.txt." >&2
    exit 1
  fi

  sed -i "s/^pkgver=.*/pkgver=$upstream_version/" PKGBUILD
  sed -i "s/^_pkgrel_upstream=.*/_pkgrel_upstream=$upstream_pkgrel/" PKGBUILD
  sed -i "s/^pkgrel=.*/pkgrel=1/" PKGBUILD
  sed -i "s/^sha256sums=.*/sha256sums=('$new_sha256')/" PKGBUILD
  makepkg --printsrcinfo > .SRCINFO
fi

rm -f littlesnitch-[0-9]*.pkg.tar.zst
makepkg -sf
sudo pacman -U --noconfirm littlesnitch-[0-9]*.pkg.tar.zst
