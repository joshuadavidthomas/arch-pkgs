#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "Checking for latest Paper version..."
upstream_version=$(curl -sr 0-0 https://download.paper.design/linux/deb \
  -D - -o /dev/null 2>/dev/null \
  | sed -n 's/.*filename="paper-desktop-\(.*\)amd64\.deb".*/\1/p')
current_version=$(sed -n 's/^pkgver=//p' PKGBUILD)

echo "Current: $current_version"
echo "Upstream: $upstream_version"

if [[ "$upstream_version" != "$current_version" ]]; then
  echo "Updating PKGBUILD to $upstream_version..."

  tmpfile=$(mktemp --suffix=.deb)
  trap 'rm -f "$tmpfile"' EXIT
  curl -fSL -o "$tmpfile" https://download.paper.design/linux/deb

  new_sha256=$(sha256sum "$tmpfile" | awk '{print $1}')
  sed -i "s/^pkgver=.*/pkgver=$upstream_version/" PKGBUILD
  sed -i "s/^pkgrel=.*/pkgrel=1/" PKGBUILD
  sed -i "s/^sha256sums=.*/sha256sums=('$new_sha256')/" PKGBUILD
  makepkg --printsrcinfo > .SRCINFO
fi

makepkg -sf
sudo pacman -U --noconfirm paper-desktop-*.pkg.tar.zst
